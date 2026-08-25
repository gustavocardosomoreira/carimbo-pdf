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
    start_leaf: int | None,
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
            if reserve_terms and current_leaf is not None:
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
                if current_leaf is not None:
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

def format_process_number(val: str) -> str:
    """
    Formata o número do processo para exibição no carimbo.
    Se estiver vazio ou no modelo '/YYYY', preserva o espaçamento físico preenchendo com 15 espaços.
    """
    if not val:
        return f"{' '*15}/2026"
    val = val.strip()
    if val == "/2026" or val.startswith("/"):
        year = val[1:] if len(val) > 1 else "2026"
        return f"{' '*15}/{year}"
    if "/" in val:
        parts = val.split("/", 1)
        num_part = parts[0].strip()
        year_part = parts[1].strip()
        if not num_part:
            return f"{' '*15}/{year_part}"
        return f"{num_part}/{year_part}"
    return val

def format_start_date(val: str) -> str:
    """
    Formata a data de início para exibição no carimbo.
    Se estiver vazia ou no modelo '//YYYY', preserva o espaçamento físico (8 espaços dia, 9 espaços mês).
    """
    if not val:
        return f"{' '*8}/{' '*9}/2026"
    val = val.strip()
    if val == "//2026" or val == "//" or val.startswith("//"):
        year = val[2:] if len(val) > 2 else "2026"
        return f"{' '*8}/{' '*9}/{year if year else '2026'}"
    if "/" in val:
        parts = val.split("/")
        if len(parts) == 3:
            day, month, year = parts[0].strip(), parts[1].strip(), parts[2].strip()
            d_str = day if day else " "*8
            m_str = month if month else " "*9
            y_str = year if year else "2026"
            return f"{d_str}/{m_str}/{y_str}"
    return val



def draw_vector_stamp(
    page: fitz.Page,
    x0: float,
    y0: float,
    scale: float,
    process_number: str,
    start_date: str,
    leaf_number: int | None,
    stamp_model: str = "padrao"
):
    """
    Desenha o carimbo vetorial nas coordenadas especificadas utilizando PyMuPDF.
    Garante resolução infinita na impressão.
    """
    import os
    # Proporções base
    W = 120.4 * scale
    
    if stamp_model == "compacto":
        H = 44.0 * scale
        W = 105.0 * scale
    elif stamp_model == "mini":
        H = 33.0 * scale
        W = 105.0 * scale
    else:
        H = 60.0 * scale
        
    x1 = x0 + W
    y1 = y0 + H
    
    # Matriz de derotação
    derot = page.derotation_matrix
    
    shape = page.new_shape()
    
    # Retângulo externo
    shape.draw_rect(fitz.Rect(x0, y0, x1, y1) * derot)
    
    if stamp_model in ["compacto", "mini"]:
        num_rows = 4 if stamp_model == "compacto" else 3
        row_height = H / num_rows
        
        # Divisórias horizontais
        for i in range(1, num_rows):
            yh = y0 + i * row_height
            shape.draw_line(fitz.Point(x0, yh) * derot, fitz.Point(x1, yh) * derot)
            
        # Divisória vertical
        x_split = x0 + W * 0.42
        y_start_vert = y0 + row_height if stamp_model == "compacto" else y0
        shape.draw_line(fitz.Point(x_split, y_start_vert) * derot, fitz.Point(x_split, y1) * derot)
    else:
        y_line1 = y0 + 16.0 * scale
        y_line2 = y0 + 38.0 * scale
        x_split = x0 + 83.9 * scale
        shape.draw_line(fitz.Point(x0, y_line1) * derot, fitz.Point(x1, y_line1) * derot)
        shape.draw_line(fitz.Point(x0, y_line2) * derot, fitz.Point(x1, y_line2) * derot)
        shape.draw_line(fitz.Point(x_split, y_line1) * derot, fitz.Point(x_split, y_line2) * derot)
    
    # Contorno
    stroke_width = 1.2 * scale
    shape.finish(color=(0, 0, 0), width=stroke_width)
    
    # Fontes
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    font_bold_path = os.path.join(base_dir, "fonts", "GOTHICB.TTF")
    
    if os.path.exists(font_bold_path):
        font_name = "CenturyGothic-Bold"
        font_file = font_bold_path
    else:
        font_name = "hebo"
        font_file = None
        
    font_size = 8.0 * scale
    
    formatted_proc = format_process_number(process_number)
    formatted_date = format_start_date(start_date)
    
    if stamp_model in ["compacto", "mini"]:
        left_padding = 4.0 * scale
        row_idx = 0
        num_rows = 4 if stamp_model == "compacto" else 3
        row_height = H / num_rows
        
        if stamp_model == "compacto":
            title = "Prefeitura Municipal de Maricá"
            try:
                title_width = fitz.getTextlength(title, fontname=font_name, fontsize=7.5 * scale)
            except:
                title_width = fitz.get_text_length(title, fontname=font_name, fontfile=font_file, fontsize=7.5 * scale)
            title_x = x0 + (W - title_width) / 2.0
            shape.insert_text(fitz.Point(title_x, y0 + 7.5 * scale) * derot, title, fontname=font_name, fontfile=font_file, fontsize=7.5 * scale, color=(0, 0, 0), rotate=page.rotation)
            row_idx = 1
            
        leaf_text = f"{leaf_number}" if leaf_number is not None else ""
        if formatted_proc.strip() == "/2026":
            formatted_proc = " /2026"  # just a single space for visual clearance
            
        rows_data = [
            ("Processo", formatted_proc),
            ("Folha", leaf_text),
            ("Rubrica", "")
        ]
        
        for i, (label, val) in enumerate(rows_data):
            y_base = y0 + (row_idx + i) * row_height + 8.0 * scale
            shape.insert_text(fitz.Point(x0 + left_padding, y_base) * derot, label, fontname=font_name, fontfile=font_file, fontsize=font_size, color=(0, 0, 0), rotate=page.rotation)
            if val:
                shape.insert_text(fitz.Point(x_split + left_padding, y_base) * derot, val, fontname=font_name, fontfile=font_file, fontsize=font_size, color=(0, 0, 0), rotate=page.rotation)
    else:
        # Padrao
        process_text = f"Processo n.º {formatted_proc}"
        left_padding = 6.0 * scale
        shape.insert_text(fitz.Point(x0 + left_padding, y0 + 11.5 * scale) * derot, process_text, fontname=font_name, fontfile=font_file, fontsize=font_size, color=(0, 0, 0), rotate=page.rotation)
        
        shape.insert_text((fitz.Point(x0 + left_padding, y0 + 24.5 * scale)) * derot, "Data do início:", fontname=font_name, fontfile=font_file, fontsize=font_size, color=(0, 0, 0), rotate=page.rotation)
        shape.insert_text((fitz.Point(x0 + left_padding, y0 + 34.5 * scale)) * derot, formatted_date, fontname=font_name, fontfile=font_file, fontsize=font_size, color=(0, 0, 0), rotate=page.rotation)
        
        fl_text = f"Fl.{leaf_number}" if leaf_number is not None else "Fl."
        x_split = x0 + 83.9 * scale
        shape.insert_text(fitz.Point(x_split + left_padding, y0 + 29.5 * scale) * derot, fl_text, fontname=font_name, fontfile=font_file, fontsize=font_size, color=(0, 0, 0), rotate=page.rotation)
        
        shape.insert_text((fitz.Point(x0 + left_padding, y0 + 47.0 * scale)) * derot, "Rubrica", fontname=font_name, fontfile=font_file, fontsize=font_size, color=(0, 0, 0), rotate=page.rotation)
        
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
    active_pages: List[int] = None,
    bg_zoom: float = 1.0,
    bg_align: str = "center",
    stamp_model: str = "padrao"
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
            
            # Aplica zoom e alinhamento na folha original (independente de ter carimbo ou não)
            if bg_zoom < 1.0:
                page_width = page.rect.width
                page_height = page.rect.height
                
                scaled_w = page_width * bg_zoom
                scaled_h = page_height * bg_zoom
                
                dx = 0
                if "left" in bg_align: dx = 0
                elif "right" in bg_align: dx = page_width - scaled_w
                else: dx = (page_width - scaled_w) / 2
                
                dy = 0
                if "top" in bg_align: dy = page_height - scaled_h
                elif "bottom" in bg_align: dy = 0
                else: dy = (page_height - scaled_h) / 2
                
                page.clean_contents()
                try:
                    xref = page.get_contents()[0]
                    stream = doc.xref_stream(xref)
                    # Envolve num bloco de estado q...Q e aplica a matriz de transformação (cm)
                    transform = f"q {bg_zoom:.5f} 0 0 {bg_zoom:.5f} {dx:.5f} {dy:.5f} cm\n".encode("utf-8")
                    doc.update_stream(xref, transform + stream + b"\nQ")
                except IndexError:
                    pass

            if not info["should_stamp"]:
                continue
                
            page_width = page.rect.width
            page_height = page.rect.height
            
            # Determinar coordenadas e escala
            scale = 1.0
            x0 = None
            y0 = None
            
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
                if x0 is not None and y0 is not None:
                    if ref_width is not None and ref_width > 0:
                        right_offset = ref_width - x0
                        x0 = page_width - right_offset
                    
            if x0 is None or y0 is None:
                # Posicionamento padrão: Canto superior direito usando a escala
                stamp_width = 120.4 * scale
                x0 = page_width - 20.0 - stamp_width
                y0 = 20.0
                
            draw_vector_stamp(
                page=page,
                x0=x0,
                y0=y0,
                scale=scale,
                process_number=process_number,
                start_date=start_date,
                leaf_number=info["leaf_number"],
                stamp_model=stamp_model
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
