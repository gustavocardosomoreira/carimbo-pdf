import os
import tempfile
import fitz
import pytest
from app.core.pdf_processor import (
    calculate_leaf_sequence,
    check_volume_break,
    process_pdf_stamping,
    render_page_to_png
)

@pytest.fixture
def sample_pdf():
    # Cria um PDF em branco temporário com 3 páginas
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "sample.pdf")
        doc = fitz.open()
        for i in range(3):
            doc.new_page(width=595, height=842)
        doc.save(pdf_path)
        doc.close()
        yield pdf_path

def test_calculate_leaf_sequence_no_reserve():
    # Teste sem reserva de termos
    total_pages = 5
    start_leaf = 198
    volume_limit = 200
    pages_info = calculate_leaf_sequence(total_pages, start_leaf, volume_limit, reserve_terms=False)
    
    assert len(pages_info) == 5
    assert pages_info[0] == {"page_idx": 0, "should_stamp": True, "leaf_number": 198, "is_term": False, "is_active": True}
    assert pages_info[1] == {"page_idx": 1, "should_stamp": True, "leaf_number": 199, "is_term": False, "is_active": True}
    assert pages_info[2] == {"page_idx": 2, "should_stamp": True, "leaf_number": 200, "is_term": False, "is_active": True}
    assert pages_info[3] == {"page_idx": 3, "should_stamp": True, "leaf_number": 201, "is_term": False, "is_active": True}
    assert pages_info[4] == {"page_idx": 4, "should_stamp": True, "leaf_number": 202, "is_term": False, "is_active": True}

def test_calculate_leaf_sequence_with_reserve():
    # Teste com reserva de termos. Folha 200 e 201 devem ser marcadas como termos e não receber carimbo.
    total_pages = 5
    start_leaf = 198
    volume_limit = 200
    pages_info = calculate_leaf_sequence(total_pages, start_leaf, volume_limit, reserve_terms=True)
    
    assert len(pages_info) == 5
    assert pages_info[0] == {"page_idx": 0, "should_stamp": True, "leaf_number": 198, "is_term": False, "is_active": True}
    assert pages_info[1] == {"page_idx": 1, "should_stamp": True, "leaf_number": 199, "is_term": False, "is_active": True}
    # Folha 200 e 201 são termos
    assert pages_info[2] == {"page_idx": 2, "should_stamp": False, "leaf_number": 200, "is_term": True, "is_active": True}
    assert pages_info[3] == {"page_idx": 3, "should_stamp": False, "leaf_number": 201, "is_term": True, "is_active": True}
    # Folha 202 volta a ser carimbada
    assert pages_info[4] == {"page_idx": 4, "should_stamp": True, "leaf_number": 202, "is_term": False, "is_active": True}

def test_check_volume_break():
    # Caso 1: Sem quebra de volume (tudo abaixo do limite)
    pages_info_1 = [
        {"leaf_number": 10},
        {"leaf_number": 11},
        {"leaf_number": 12}
    ]
    has_break, msg = check_volume_break(pages_info_1, volume_limit=200)
    assert not has_break
    assert msg == ""
    
    # Caso 2: Atinge exatamente o limite (200)
    pages_info_2 = [
        {"leaf_number": 199},
        {"leaf_number": 200}
    ]
    has_break, msg = check_volume_break(pages_info_2, volume_limit=200)
    assert has_break
    assert "quebra de volume" in msg
    
    # Caso 3: Ultrapassa o limite (inicia volume 2)
    pages_info_3 = [
        {"leaf_number": 199},
        {"leaf_number": 200},
        {"leaf_number": 201},
        {"leaf_number": 202}
    ]
    has_break, msg = check_volume_break(pages_info_3, volume_limit=200)
    assert has_break
    assert "quebra de volume" in msg

def test_pdf_stamping_and_rendering():
    # Cria um PDF em branco temporário para testes
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "test_input.pdf")
        output_path = os.path.join(tmpdir, "test_output.pdf")
        
        # Gerar PDF em branco com 3 páginas
        doc = fitz.open()
        for i in range(3):
            doc.new_page(width=595, height=842) # Tamanho A4 padrão
        doc.save(pdf_path)
        doc.close()
        
        # Aplicar carimbo
        pages_info, has_break, break_msg = process_pdf_stamping(
            input_pdf_path=pdf_path,
            output_pdf_path=output_path,
            process_number="1234/2026",
            start_date="15/07/2026",
            start_leaf=199,
            volume_limit=200,
            reserve_terms=True
        )
        
        # Validar as informações geradas
        assert len(pages_info) == 3
        # Páginas:
        # Pág 0 (199) -> Carimbada
        # Pág 1 (200) -> Não carimbada (Termo)
        # Pág 2 (201) -> Não carimbada (Termo)
        assert pages_info[0]["should_stamp"] is True
        assert pages_info[0]["leaf_number"] == 199
        assert pages_info[1]["should_stamp"] is False
        assert pages_info[1]["leaf_number"] == 200
        assert pages_info[2]["should_stamp"] is False
        assert pages_info[2]["leaf_number"] == 201
        
        # Verificar se o arquivo final existe e possui as páginas carimbadas
        assert os.path.exists(output_path)
        out_doc = fitz.open(output_path)
        assert len(out_doc) == 3
        out_doc.close()
        
        # Verificar a renderização em PNG de uma página
        png_bytes = render_page_to_png(output_path, page_idx=0)
        assert len(png_bytes) > 0
        assert png_bytes[:4] == b"\x89PNG" # Assinatura do PNG


def test_parse_page_interval():
    from app.core.pdf_processor import parse_page_interval
    
    # Test valid interval strings
    assert parse_page_interval("Todos", 5) == [0, 1, 2, 3, 4]
    assert parse_page_interval("todas", 5) == [0, 1, 2, 3, 4]
    assert parse_page_interval("all", 5) == [0, 1, 2, 3, 4]
    assert parse_page_interval("1-3", 5) == [0, 1, 2]
    assert parse_page_interval("2, 4", 5) == [1, 3]
    assert parse_page_interval("1-2, 4-5", 5) == [0, 1, 3, 4]
    
    # Test out of bounds (should ignore out of bounds silently)
    assert parse_page_interval("1-10", 5) == [0, 1, 2, 3, 4]
    assert parse_page_interval("6, 7", 5) == []
    
    # Test empty or invalid formats
    assert parse_page_interval("", 5) == [0, 1, 2, 3, 4]
    assert parse_page_interval("invalid", 5) == []
    assert parse_page_interval("1-", 5) == []


def test_calculate_leaf_sequence_with_inactive_pages():
    from app.core.pdf_processor import calculate_leaf_sequence
    
    # Test with inactive pages (non-active pages get leaf_number: None, should_stamp: False)
    # Total pages: 5, active pages: [0, 2, 4] (indexes)
    # Start leaf: 10, volume_limit: 200, reserve_terms: True
    pages_info = calculate_leaf_sequence(
        total_pages=5,
        start_leaf=10,
        volume_limit=200,
        reserve_terms=True,
        active_pages=[0, 2, 4]
    )
    
    # Active pages: 0, 2, 4 should get leaf numbers 10, 11, 12 respectively.
    # Inactive pages: 1, 3 should get leaf_number: None, should_stamp: False
    assert pages_info[0]["leaf_number"] == 10
    assert pages_info[0]["should_stamp"] is True
    
    assert pages_info[1]["leaf_number"] is None
    assert pages_info[1]["should_stamp"] is False
    
    assert pages_info[2]["leaf_number"] == 11
    assert pages_info[2]["should_stamp"] is True
    
    assert pages_info[3]["leaf_number"] is None
    assert pages_info[3]["should_stamp"] is False
    
    assert pages_info[4]["leaf_number"] == 12
    assert pages_info[4]["should_stamp"] is True


def test_process_pdf_stamping_with_inactive_pages(sample_pdf):
    from app.core.pdf_processor import process_pdf_stamping
    import tempfile
    
    # We will exclude page 1 (second page). Only pages 0 and 2 should be active.
    # Total pages: 3.
    # We expect pages 0 and 2 to receive stamps and leaf numbers 18, 19.
    # Page 1 should remain unstamped and its leaf number should be None.
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "output.pdf")
        
        pages_info, has_break, break_msg = process_pdf_stamping(
            input_pdf_path=sample_pdf,
            output_pdf_path=output_path,
            process_number="9557/2026",
            start_date="21/05/2026",
            start_leaf=18,
            volume_limit=200,
            reserve_terms=True,
            active_pages=[0, 2]
        )
        
        assert pages_info[0]["leaf_number"] == 18
        assert pages_info[0]["should_stamp"] is True
        
        assert pages_info[1]["leaf_number"] is None
        assert pages_info[1]["should_stamp"] is False
        
        assert pages_info[2]["leaf_number"] == 19
        assert pages_info[2]["should_stamp"] is True
        
        # Verify the output PDF has exactly 3 pages
        assert os.path.exists(output_path)
        out_doc = fitz.open(output_path)
        assert len(out_doc) == 3
        out_doc.close()


def test_process_pdf_stamping_mixed_coords(sample_pdf):
    from app.core.pdf_processor import process_pdf_stamping
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "output_mixed.pdf")

        # Test passing both global coords and custom override for only page 0
        pages_info, has_break, break_msg = process_pdf_stamping(
            input_pdf_path=sample_pdf,
            output_pdf_path=output_path,
            process_number="9557/2026",
            start_date="21/05/2026",
            start_leaf=18,
            volume_limit=200,
            reserve_terms=True,
            global_coords={"x0": 400.0, "y0": 30.0, "scale": 1.1},
            custom_coords={"0": {"x0": 100.0, "y0": 100.0, "scale": 0.8}}
        )

        assert os.path.exists(output_path)
        out_doc = fitz.open(output_path)
        assert len(out_doc) == 3
        out_doc.close()


def test_process_pdf_stamping_on_rotated_page():
    from app.core.pdf_processor import process_pdf_stamping
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "rotated_input.pdf")
        output_path = os.path.join(tmpdir, "rotated_output.pdf")
        
        # Create a PDF with a rotated page (90 degrees rotation)
        doc = fitz.open()
        page = doc.new_page(width=595, height=842) # A4 Portrait
        page.set_rotation(90) # Becomes Landscape visually (width 842, height 595)
        doc.save(pdf_path)
        doc.close()
        
        # We stamp the page at visual coordinate (600, 20) with scale 1.0
        pages_info, has_break, break_msg = process_pdf_stamping(
            input_pdf_path=pdf_path,
            output_pdf_path=output_path,
            process_number="9557/2026",
            start_date="21/05/2026",
            start_leaf=18,
            volume_limit=200,
            reserve_terms=True,
            global_coords={"x0": 600.0, "y0": 20.0, "scale": 1.0}
        )
        
        assert os.path.exists(output_path)
        
        # Verify the stamped coordinates in the output file
        out_doc = fitz.open(output_path)
        out_page = out_doc[0]
        
        # Extract drawings or text to confirm correct unrotated coordinates
        drawings = out_page.get_drawings()
        # The drawing coordinates should be in the unrotated system:
        # Visual Rect(600, 20, 750, 80) derotated by Matrix(0, -1, 1, 0, -0, 842)
        # becomes Rect(20, 92, 80, 242) in unrotated space
        assert len(drawings) > 0
        
        # Verify unrotated text location and orientation
        text_page = out_page.get_text("dict")
        found_text = False
        for block in text_page["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    # Since page rotation is 90, the text was inserted with rotate=90.
                    # Dir Vector in unrotated space should be (0.0, -1.0)
                    for span in line["spans"]:
                        if "Processo" in span["text"]:
                            found_text = True
                            assert line["dir"] == (0.0, -1.0)
        assert found_text
        out_doc.close()


def test_process_pdf_stamping_global_ref_width():
    from app.core.pdf_processor import process_pdf_stamping
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "mixed_input.pdf")
        output_path = os.path.join(tmpdir, "mixed_output.pdf")
        
        # Create a PDF with 2 pages: 1 portrait (595x842), 1 landscape (842x595)
        doc = fitz.open()
        p0 = doc.new_page(width=595, height=842) # Portrait
        p1 = doc.new_page(width=842, height=595) # Landscape
        doc.save(pdf_path)
        doc.close()
        
        # We stamp globally. The user dragged on portrait page (width 595) to x0=425 (which is 170 from right).
        # We expect that on page 0 (portrait), it stamps at x0=425.
        # On page 1 (landscape, width 842), it stamps at x0=842 - 170 = 672.
        pages_info, has_break, break_msg = process_pdf_stamping(
            input_pdf_path=pdf_path,
            output_pdf_path=output_path,
            process_number="9557/2026",
            start_date="21/05/2026",
            start_leaf=18,
            volume_limit=200,
            reserve_terms=True,
            global_coords={"x0": 425.0, "y0": 20.0, "scale": 1.0, "ref_width": 595.0, "ref_height": 842.0}
        )
        
        assert os.path.exists(output_path)
        out_doc = fitz.open(output_path)
        
        # Page 0 (Portrait): drawing x0 should be 425
        drawings_p0 = out_doc[0].get_drawings()
        assert len(drawings_p0) > 0
        rect_p0 = drawings_p0[0]["rect"]
        assert abs(rect_p0.x0 - 425.0) < 1e-2
        
        # Page 1 (Landscape): drawing x0 should be 672.0
        drawings_p1 = out_doc[1].get_drawings()
        assert len(drawings_p1) > 0
        rect_p1 = drawings_p1[0]["rect"]
        assert abs(rect_p1.x0 - 672.0) < 1e-2
        
        out_doc.close()
