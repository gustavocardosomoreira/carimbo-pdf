import os
import io
import pytest
import fitz
from fastapi.testclient import TestClient
from app.main import app, UPLOAD_DIR

client = TestClient(app)

@pytest.fixture
def dummy_pdf():
    # Cria um PDF em branco temporário com 2 páginas
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    doc.new_page(width=595, height=842)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def test_serve_frontend():
    # Testar se a rota principal serve a página do frontend
    response = client.get("/")
    assert response.status_code == 200
    assert "SIGFolha" in response.text
    assert "btn-view-all-grid" in response.text
    assert "volume-pill-indicator" in response.text
    assert "pdf-group-odd" in response.text

def test_api_upload_and_preview(dummy_pdf):
    # Enviar o PDF simulado para o endpoint de upload
    response = client.post(
        "/api/upload",
        files={"file": ("documento_teste.pdf", io.BytesIO(dummy_pdf), "application/pdf")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "file_id" in data
    assert data["filename"] == "documento_teste.pdf"
    assert data["total_pages"] == 2
    assert len(data["pages"]) == 2
    assert data["pages"][0]["width"] == 595.0
    
    file_id = data["file_id"]
    
    # Testar o preview da primeira página
    preview_response = client.get(f"/api/preview/{file_id}/0")
    assert preview_response.status_code == 200
    assert preview_response.headers["content-type"] == "image/png"
    assert preview_response.content[:4] == b"\x89PNG"
    
    # Limpar arquivo temporário após o teste
    input_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
    if os.path.exists(input_path):
        os.remove(input_path)

def test_api_stamp(dummy_pdf):
    # Primeiro fazemos o upload
    upload_response = client.post(
        "/api/upload",
        files={"file": ("documento_teste.pdf", io.BytesIO(dummy_pdf), "application/pdf")}
    )
    assert upload_response.status_code == 200
    file_id = upload_response.json()["file_id"]
    
    # Agora fazemos a solicitação de carimbagem
    stamp_payload = {
        "file_id": file_id,
        "process_number": "4321/2026",
        "start_date": "16/07/2026",
        "start_leaf": 10,
        "volume_limit": 200,
        "reserve_terms": True,
        "global_coords": {"x0": 400.0, "y0": 30.0, "scale": 1.1}
    }
    
    stamp_response = client.post("/api/stamp", json=stamp_payload)
    assert stamp_response.status_code == 200
    assert stamp_response.headers["content-type"] == "application/pdf"
    
    # Carregar o PDF retornado para validar que foi gerado corretamente
    stamped_bytes = stamp_response.content
    stamped_doc = fitz.open(stream=stamped_bytes, filetype="pdf")
    assert len(stamped_doc) == 2
    stamped_doc.close()
    
    # Limpar arquivos temporários
    for filename in [f"{file_id}.pdf", f"{file_id}_stamped.pdf"]:
        filepath = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)

def test_api_stamp_custom_coords(dummy_pdf):
    # Primeiro fazemos o upload
    upload_response = client.post(
        "/api/upload",
        files={"file": ("documento_teste.pdf", io.BytesIO(dummy_pdf), "application/pdf")}
    )
    assert upload_response.status_code == 200
    file_id = upload_response.json()["file_id"]
    
    # Solicitação com coordenadas customizadas por página
    stamp_payload = {
        "file_id": file_id,
        "process_number": "5555/2026",
        "start_date": "17/07/2026",
        "start_leaf": 1,
        "volume_limit": 200,
        "reserve_terms": False,
        "custom_coords": {
            "0": {"x0": 100.0, "y0": 100.0, "scale": 0.8},
            "1": {"x0": 200.0, "y0": 200.0, "scale": 1.2}
        }
    }
    
    stamp_response = client.post("/api/stamp", json=stamp_payload)
    assert stamp_response.status_code == 200
    assert stamp_response.headers["content-type"] == "application/pdf"
    
    # Carregar o PDF retornado para validar que foi gerado corretamente
    stamped_bytes = stamp_response.content
    stamped_doc = fitz.open(stream=stamped_bytes, filetype="pdf")
    assert len(stamped_doc) == 2
    stamped_doc.close()
    
    # Limpar arquivos temporários
    for filename in [f"{file_id}.pdf", f"{file_id}_stamped.pdf"]:
        filepath = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)


def test_api_stamp_with_inactive_pages(dummy_pdf):
    # Primeiro fazemos o upload
    upload_response = client.post(
        "/api/upload",
        files={"file": ("documento_teste.pdf", io.BytesIO(dummy_pdf), "application/pdf")}
    )
    assert upload_response.status_code == 200
    file_id = upload_response.json()["file_id"]
    
    # Solicitação excluindo a segunda página (índice 1) do carimbo
    stamp_payload = {
        "file_id": file_id,
        "process_number": "7777/2026",
        "start_date": "16/07/2026",
        "start_leaf": 10,
        "volume_limit": 200,
        "reserve_terms": True,
        "active_pages": [0]  # Apenas a página 0 será carimbada, página 1 ficará sem carimbo
    }
    
    stamp_response = client.post("/api/stamp", json=stamp_payload)
    assert stamp_response.status_code == 200
    assert stamp_response.headers["content-type"] == "application/pdf"
    
    # Validar que o PDF retornado tem 2 páginas (página 1 continua existindo, mesmo que desativada)
    stamped_bytes = stamp_response.content
    stamped_doc = fitz.open(stream=stamped_bytes, filetype="pdf")
    assert len(stamped_doc) == 2
    stamped_doc.close()
    
    # Limpar arquivos temporários
    for filename in [f"{file_id}.pdf", f"{file_id}_stamped.pdf"]:
        filepath = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)

