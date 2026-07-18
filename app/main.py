import os
import uuid
import shutil
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.templating import Jinja2Templates
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

app = FastAPI(title="Carimbo.pdf - Carimbador Dinâmico de PDF")

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

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Recebe um PDF, armazena temporariamente, lê suas dimensões e metadados.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Por favor, envie apenas arquivos PDF.")
        
    file_id = str(uuid.uuid4())
    input_filename = f"{file_id}.pdf"
    input_path = os.path.join(UPLOAD_DIR, input_filename)
    
    # Salvar o arquivo
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        doc = fitz.open(input_path)
        total_pages = len(doc)
        pages_metadata = []
        for idx in range(total_pages):
            page = doc.load_page(idx)
            pages_metadata.append({
                "page_idx": idx,
                "width": page.rect.width,
                "height": page.rect.height
            })
        doc.close()
    except Exception as e:
        # Remover arquivo corrompido
        if os.path.exists(input_path):
            os.remove(input_path)
        raise HTTPException(status_code=400, detail=f"Erro ao ler o PDF: {str(e)}")
        
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
    """
    input_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail="Arquivo PDF não encontrado.")
        
    try:
        png_bytes = render_page_to_png(input_path, page_idx, dpi=100) # dpi menor para preview leve
        return Response(content=png_bytes, media_type="image/png")
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
        
    output_filename = f"{request.file_id}_stamped.pdf"
    output_path = os.path.join(UPLOAD_DIR, output_filename)
    
    global_coords_dict = None
    if request.global_coords:
        global_coords_dict = request.global_coords.model_dump()
        
    custom_coords_dict = None
    if request.custom_coords:
        custom_coords_dict = {k: v.model_dump() for k, v in request.custom_coords.items()}
        
    try:
        pages_info, has_break, break_msg = process_pdf_stamping(
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
        
    return FileResponse(
        path=output_path,
        media_type="application/pdf",
        filename="carimbo_carimbado.pdf"
    )
