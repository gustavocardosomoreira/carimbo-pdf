import os
import uuid
import shutil
import time
import asyncio
import gc
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.core.config import (
    DEFAULT_VOLUME_LIMIT,
    DEFAULT_PROCESS_NUMBER,
    DEFAULT_START_DATE,
    DEFAULT_START_LEAF,
    DEFAULT_RESERVE_TERMS
)
from app.core.pdf_processor import (
    process_pdf_stamping,
    render_page_to_png,
    calculate_leaf_sequence,
    check_volume_break
)
import fitz

# Constantes de limite e expiração
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
INACTIVITY_THRESHOLD_SECONDS = 30 * 60  # 30 minutos

# Registro de atividade das sessões (file_id -> timestamp da última atividade)
SESSION_ACTIVITY: Dict[str, float] = {}

def touch_session(file_id: str):
    """
    Atualiza o timestamp de atividade de uma sessão/arquivo.
    """
    if file_id:
        SESSION_ACTIVITY[file_id] = time.time()

def cleanup_inactive_uploads(max_age_seconds: int = INACTIVITY_THRESHOLD_SECONDS):
    """
    Remove arquivos temporários de upload cuja última atividade tenha sido há mais de max_age_seconds.
    """
    now = time.time()
    if not os.path.exists(UPLOAD_DIR):
        return

    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.isfile(file_path):
            file_id = filename.split(".")[0].replace("_stamped", "")
            last_active = SESSION_ACTIVITY.get(file_id)
            if last_active is None:
                try:
                    last_active = os.path.getmtime(file_path)
                except Exception:
                    last_active = now

            if now - last_active > max_age_seconds:
                try:
                    os.remove(file_path)
                    SESSION_ACTIVITY.pop(file_id, None)
                except Exception:
                    pass

async def periodic_cleanup_task():
    """
    Tarefa em segundo plano executada ciclicamente a cada 5 minutos para limpar sessões inativas.
    """
    while True:
        try:
            await asyncio.sleep(300)  # 5 minutos
            await run_in_threadpool(cleanup_inactive_uploads, INACTIVITY_THRESHOLD_SECONDS)
        except asyncio.CancelledError:
            break
        except Exception:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerenciador do ciclo de vida da aplicação para tarefas de startup e shutdown.
    """
    cleanup_task = asyncio.create_task(periodic_cleanup_task())
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="Carimbo.pdf - Carimbador Dinâmico de PDF",
    lifespan=lifespan
)

# Configurar diretório de templates e uploads
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class StampCoords(BaseModel):
    x0: float
    y0: float
    scale: float
    ref_width: Optional[float] = None
    ref_height: Optional[float] = None

class StampRequest(BaseModel):
    file_id: str
    process_number: str
    start_date: str
    start_leaf: int
    volume_limit: int
    reserve_terms: bool
    global_coords: Optional[StampCoords] = None
    custom_coords: Optional[Dict[str, StampCoords]] = None
    active_pages: Optional[List[int]] = None

@app.get("/health")
async def health_check():
    """
    Endpoint de verificação de integridade (Health Check) para o Railway/Plataformas de nuvem.
    """
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def serve_frontend(request: Request):
    """
    Serve a interface do usuário (SPA).
    """
    response = templates.TemplateResponse(request, "index.html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

def _read_and_parse_pdf(input_path: str):
    """
    Função síncrona auxiliar para abrir e ler dimensões do PDF sem bloquear o event loop.
    """
    with fitz.open(input_path) as doc:
        total_pages = len(doc)
        pages_metadata = []
        for idx in range(total_pages):
            page = doc.load_page(idx)
            pages_metadata.append({
                "page_idx": idx,
                "width": page.rect.width,
                "height": page.rect.height
            })
    return total_pages, pages_metadata

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Recebe um PDF, armazena temporariamente, lê suas dimensões e metadados.
    Valida o tamanho máximo de 50 MB por sessão.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Por favor, envie apenas arquivos PDF.")

    file_id = str(uuid.uuid4())
    input_filename = f"{file_id}.pdf"
    input_path = os.path.join(UPLOAD_DIR, input_filename)

    # Copiar o arquivo validando tamanho total acumulado
    total_bytes = 0
    with open(input_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):  # Chunks de 1 MB
            total_bytes += len(chunk)
            if total_bytes > MAX_FILE_SIZE_BYTES:
                buffer.close()
                if os.path.exists(input_path):
                    os.remove(input_path)
                raise HTTPException(
                    status_code=413,
                    detail="O tamanho total dos PDFs nesta sessão não pode ultrapassar 50 MB."
                )
            buffer.write(chunk)

    try:
        total_pages, pages_metadata = await run_in_threadpool(_read_and_parse_pdf, input_path)
    except Exception as e:
        if os.path.exists(input_path):
            os.remove(input_path)
        raise HTTPException(status_code=400, detail=f"Erro ao ler o PDF: {str(e)}")

    touch_session(file_id)

    # Calcular sequência inicial padrão
    pages_info = calculate_leaf_sequence(
        total_pages=total_pages,
        start_leaf=DEFAULT_START_LEAF,
        volume_limit=DEFAULT_VOLUME_LIMIT,
        reserve_terms=DEFAULT_RESERVE_TERMS
    )
    has_break, break_msg = check_volume_break(pages_info, DEFAULT_VOLUME_LIMIT)

    return {
        "file_id": file_id,
        "filename": file.filename,
        "total_pages": total_pages,
        "pages": pages_metadata,
        "pages_info": pages_info,
        "has_break": has_break,
        "break_msg": break_msg
    }

@app.get("/api/preview/{file_id}/{page_idx}")
async def get_page_preview(file_id: str, page_idx: int):
    """
    Gera e retorna o preview PNG sob demanda para uma determinada página do PDF.
    Usa run_in_threadpool para não bloquear o event loop e define cabeçalhos de cache.
    """
    input_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail="Arquivo PDF não encontrado.")

    touch_session(file_id)

    try:
        png_bytes = await run_in_threadpool(render_page_to_png, input_path, page_idx, 100)
        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={"Cache-Control": "private, max-age=3600"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao renderizar página: {str(e)}")

@app.post("/api/stamp")
async def stamp_pdf_route(request: StampRequest):
    """
    Aplica a carimbagem no PDF de acordo com os parâmetros enviados e retorna o arquivo final.
    """
    input_path = os.path.join(UPLOAD_DIR, f"{request.file_id}.pdf")
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail="Arquivo original não encontrado.")

    touch_session(request.file_id)

    output_filename = f"{request.file_id}_stamped.pdf"
    output_path = os.path.join(UPLOAD_DIR, output_filename)

    global_coords_dict = None
    if request.global_coords:
        global_coords_dict = request.global_coords.model_dump()

    custom_coords_dict = None
    if request.custom_coords:
        custom_coords_dict = {k: v.model_dump() for k, v in request.custom_coords.items()}

    try:
        pages_info, has_break, break_msg = await run_in_threadpool(
            process_pdf_stamping,
            input_pdf_path=input_path,
            output_pdf_path=output_path,
            process_number=request.process_number,
            start_date=request.start_date,
            start_leaf=request.start_leaf,
            volume_limit=request.volume_limit,
            reserve_terms=request.reserve_terms,
            global_coords=global_coords_dict,
            custom_coords=custom_coords_dict,
            active_pages=request.active_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no processamento do carimbo: {str(e)}")
    finally:
        gc.collect()

    return FileResponse(
        path=output_path,
        media_type="application/pdf",
        filename="carimbo_carimbado.pdf"
    )

