import fitz  # PyMuPDF
from typing import Dict, List, Tuple, Any

def parse_page_interval(interval_str: str, total_pages: int) -> List[int]:
    """
    Converte uma string de intervalo de páginas (ex: "Todos", "1-5", "2, 4, 6-10")
    em uma lista de índices de páginas (0-indexed) ativos.
    """
    val = interval_str.strip().lower()
    if not val or val == "todos" or val == "todas" or val == "all":
        return list(range(total_pages))
    
    active_pages = set()
    parts = val.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                start_str, end_str = part.split("-", 1)
                start = int(start_str.strip())
                end = int(end_str.strip())
                if start > end:
                    start, end = end, start
                for p in range(start, end + 1):
                    if 1 <= p <= total_pages:
                        active_pages.add(p - 1)
            except ValueError:
                pass
        else:
            try:
                p = int(part)
                if 1 <= p <= total_pages:
                    active_pages.add(p - 1)
            except ValueError:
                pass
                
    return sorted(list(active_pages))

def calculate_leaf_sequence(
    total_pages: int,
    start_leaf: int,
    volume_limit: int,
    reserve_terms: bool,
    active_pages: List[int] = None
) -> List[Dict[str, Any]]:
    """
    Calcula a sequência de numeração das folhas para cada página do PDF.
    Se reserve_terms for True, pula a numeração e desenho do carimbo em múltiplos
    de volume_limit (ex: 200 - Encerramento) e volume_limit + 1 (ex: 201 - Abertura).
    Se active_pages for fornecido, apenas as páginas contidas nesta lista (0-indexed)
    recebem numeração de folha e carimbo/termo.
    """
    if active_pages is None:
        active_pages = list(range(total_pages))
        
    active_set = set(active_pages)
    current_leaf = start_leaf
    pages_info = []
    
    for idx in range(total_pages):
        if idx not in active_set:
            pages_info.append({
                "page_idx": idx,
                "should_stamp": False,
                "leaf_number": None,
                "is_term": False,
                "is_active": False
            })
        else:
            is_term = False
            if reserve_terms:
                if current_leaf > 1 and (current_leaf % volume_limit == 0 or current_leaf % volume_limit == 1):
                    is_term = True
                    
            if is_term:
                pages_info.append({
                    "page_idx": idx,
                    "should_stamp": False,
                    "leaf_number": current_leaf,
                    "is_term": True,
                    "is_active": True
                })
                current_leaf += 1
            else:
                pages_info.append({
                    "page_idx": idx,
                    "should_stamp": True,
                    "leaf_number": current_leaf,
                    "is_term": False,
                    "is_active": True
                })
                current_leaf += 1
                
    return pages_info

def check_volume_break(pages_info: List[Dict[str, Any]], volume_limit: int) -> Tuple[bool, str]:
    """
    Verifica se a numeração cruza ou atinge limites de volume e retorna aviso visual se necessário.
    """
    if not pages_info:
        return False, ""
        
    numbered_pages = [p for p in pages_info if p.get("leaf_number") is not None]
    if not numbered_pages:
        return False, ""
        
    max_leaf = max(p["leaf_number"] for p in numbered_pages)
    min_leaf = min(p["leaf_number"] for p in numbered_pages)
    
    if max_leaf >= volume_limit:
        vol_min = (min_leaf - 1) // volume_limit + 1
        vol_max = (max_leaf - 1) // volume_limit + 1
        if vol_min != vol_max or max_leaf % volume_limit == 0:
            return True, f"Atenção: O documento ultrapassou o limite do volume (múltiplo de {volume_limit} folhas). Haverá quebra de volume."
            
    return False, ""

def draw_vector_stamp(
    page: fitz.Page,
    x0: float,
    y0: float,
    scale: float,
    process_number: str,
    start_date: str,
    leaf_number: int
):
    """
    Desenha o carimbo vetorial nas coordenadas especificadas utilizando PyMuPDF.
    Garante resolução infinita na impressão.
    """
    import os
    # Proporções base (150 x 60 pt)
    W = 150.0 * scale
    H = 60.0 * scale
    x1 = x0 + W
    y1 = y0 + H
    
    # Coordenadas internas
    y_line1 = y0 + 16.0 * scale
    y_line2 = y0 + 38.0 * scale
    x_split = x0 + 102.0 * scale
    
    # Matriz de derotação para converter coordenadas visuais para o espaço físico da página
    derot = page.derotation_matrix
    
    shape = page.new_shape()
    
    # Retângulo externo
    shape.draw_rect(fitz.Rect(x0, y0, x1, y1) * derot)
    
    # Divisórias horizontais
    shape.draw_line(fitz.Point(x0, y_line1) * derot, fitz.Point(x1, y_line1) * derot)
    shape.draw_line(fitz.Point(x0, y_line2) * derot, fitz.Point(x1, y_line2) * derot)
    
    # Divisória vertical do meio (split 68/32)
    shape.draw_line(fitz.Point(x_split, y_line1) * derot, fitz.Point(x_split, y_line2) * derot)
    
    # Contorno preto com espessura uniforme 1.2 pt escalada
    stroke_width = 1.2 * scale
    shape.finish(color=(0, 0, 0), width=stroke_width)
    
    # Obter caminhos das fontes no projeto
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    font_bold_path = os.path.join(base_dir, "fonts", "GOTHICB.TTF")
    
    if os.path.exists(font_bold_path):
        font_name = "CenturyGothic-Bold"
        font_file = font_bold_path
    else:
        font_name = "hebo" # fallback para Helvetica Bold
        font_file = None
        
    # Todos os textos usam o mesmo tamanho de fonte: Century Gothic 8
    font_size = 8.0 * scale
    
    # Linha 1: Processo n.º
    process_text = f"Processo n.º {process_number}"
    left_padding = 6.0 * scale
    px = x0 + left_padding
    py = y0 + 11.5 * scale
    shape.insert_text(fitz.Point(px, py) * derot, process_text, fontname=font_name, fontfile=font_file, fontsize=font_size, color=(0, 0, 0), rotate=page.rotation)
    
    # Linha 2 (Esquerda): Data do início
    left_padding = 6.0 * scale
    shape.insert_text(
        (fitz.Point(x0 + left_padding, y0 + 24.5 * scale)) * derot,
        "Data do início:",
        fontname=font_name,
        fontfile=font_file,
        fontsize=font_size,
        color=(0, 0, 0),
        rotate=page.rotation
    )
    shape.insert_text(
        (fitz.Point(x0 + left_padding, y0 + 34.5 * scale)) * derot,
        start_date,
        fontname=font_name,
        fontfile=font_file,
        fontsize=font_size,
        color=(0, 0, 0),
        rotate=page.rotation
    )
    
    # Linha 2 (Direita): Fl. (Sem espaço antes do número: Fl.18)
    fl_text = f"Fl.{leaf_number}"
    if font_file:
        font_obj = fitz.Font(fontfile=font_file)
        fl_w = font_obj.text_length(fl_text, fontsize=font_size)
    else:
        fl_w = fitz.get_text_length(fl_text, fontname=font_name, fontsize=font_size)
    fl_cell_w = x1 - x_split
    fl_x = x_split + (fl_cell_w - fl_w) / 2
    fl_y = y0 + 29.5 * scale
    shape.insert_text(fitz.Point(fl_x, fl_y) * derot, fl_text, fontname=font_name, fontfile=font_file, fontsize=font_size, color=(0, 0, 0), rotate=page.rotation)
    
    # Linha 3: Rubrica
    shape.insert_text(
        (fitz.Point(x0 + left_padding, y0 + 47.0 * scale)) * derot,
        "Rubrica",
        fontname=font_name,
        fontfile=font_file,
        fontsize=font_size,
        color=(0, 0, 0),
        rotate=page.rotation
    )
    
    shape.commit()

def process_pdf_stamping(
    input_pdf_path: str,
    output_pdf_path: str,
    process_number: str,
    start_date: str,
    start_leaf: int,
    volume_limit: int,
    reserve_terms: bool,
    global_coords: Dict[str, Any] = None,
    custom_coords: Dict[str, Dict[str, Any]] = None,
    active_pages: List[int] = None
) -> Tuple[List[Dict[str, Any]], bool, str]:
    """
    Abre o PDF, calcula a sequência e estampa cada página de acordo com os parâmetros e coordenadas.
    Retorna a lista de informações de página, se houve quebra de volume e o aviso correspondente.
    """
    doc = fitz.open(input_pdf_path)
    try:
        total_pages = len(doc)
        
        pages_info = calculate_leaf_sequence(
            total_pages=total_pages,
            start_leaf=start_leaf,
            volume_limit=volume_limit,
            reserve_terms=reserve_terms,
            active_pages=active_pages
        )
        has_break, break_msg = check_volume_break(pages_info, volume_limit)
        
        for idx, page in enumerate(doc):
            info = pages_info[idx]
            if not info["should_stamp"]:
                continue
                
            page_width = page.rect.width
            page_height = page.rect.height
            
            # Determinar coordenadas e escala
            scale = 1.0
            if custom_coords and str(idx) in custom_coords:
                c = custom_coords[str(idx)]
                x0 = c.get("x0")
                y0 = c.get("y0")
                scale = c.get("scale", 1.0)
            elif global_coords:
                x0 = global_coords.get("x0")
                y0 = global_coords.get("y0")
                scale = global_coords.get("scale", 1.0)
                ref_width = global_coords.get("ref_width")
                if ref_width is not None and ref_width > 0:
                    right_offset = ref_width - x0
                    x0 = page_width - right_offset
            else:
                # Posicionamento padrão: Canto superior direito
                w = 150.0 * scale
                h = 60.0 * scale
                x0 = page_width - 20.0 - w
                y0 = 20.0
                
            draw_vector_stamp(
                page=page,
                x0=x0,
                y0=y0,
                scale=scale,
                process_number=process_number,
                start_date=start_date,
                leaf_number=info["leaf_number"]
            )
            
        doc.save(output_pdf_path)
        return pages_info, has_break, break_msg
    finally:
        doc.close()

def render_page_to_png(pdf_path: str, page_idx: int, dpi: int = 150) -> bytes:
    """
    Renderiza uma única página do PDF para formato PNG.
    """
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_idx)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes
