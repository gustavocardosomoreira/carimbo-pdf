import fitz
import pytest
from fastapi.testclient import TestClient

from app.core.pdf_processor import process_pdf_stamping
from app.main import app


def make_mixed_pdf(path):
    with fitz.open() as doc:
        for width, height, rotation in [(595, 842, 0), (842, 595, 0), (595, 842, 90), (842, 595, 90)]:
            page = doc.new_page(width=width, height=height)
            page.insert_text((50, 150), "ORIGINAL")
            page.set_rotation(rotation)
        doc.save(path)


def bounds(path):
    with fitz.open(path) as doc:
        return [tuple(page.get_drawings()[0]["rect"] * page.rotation_matrix) for page in doc]


@pytest.mark.parametrize("stamp_model", ["padrao", "compacto", "mini"])
@pytest.mark.parametrize("rotate_landscape", [False, True])
@pytest.mark.parametrize("orientation,selected,group", [
    ("portrait", 0, [0, 3]), ("landscape", 1, [1, 2]),
])
def test_moving_one_orientation_preserves_the_other(tmp_path, stamp_model, rotate_landscape, orientation, selected, group):
    source, baseline, moved = (tmp_path / name for name in ["source.pdf", "baseline.pdf", "moved.pdf"])
    make_mixed_pdf(source)
    args = (str(source), str(baseline), "123/2026", "16/11/2026", 1, 200, False)
    process_pdf_stamping(*args, stamp_model=stamp_model, rotate_landscape=rotate_landscape)
    before = bounds(baseline)
    width, height = (595, 842) if orientation == "portrait" else (842, 595)
    process_pdf_stamping(
        str(source), str(moved), "123/2026", "16/11/2026", 1, 200, False,
        stamp_model=stamp_model, rotate_landscape=rotate_landscape,
        orientation_coords={orientation: {
            "x0": before[selected][0] - 30, "y0": before[selected][1] - 10,
            "scale": 1, "ref_width": width, "ref_height": height,
        }},
    )
    after = bounds(moved)
    for idx in range(4):
        dx, dy = (-30, -10) if idx in group else (0, 0)
        expected = tuple(value + (dx if axis % 2 == 0 else dy) for axis, value in enumerate(before[idx]))
        assert after[idx] == pytest.approx(expected, abs=0.01)


@pytest.mark.parametrize("rotate_landscape", [False, True])
def test_api_preserves_both_orientation_positions_and_custom_overrides(tmp_path, monkeypatch, rotate_landscape):
    monkeypatch.setattr("app.main.UPLOAD_DIR", str(tmp_path))
    source = tmp_path / "mixed.pdf"
    make_mixed_pdf(source)
    with TestClient(app) as client:
        upload = client.post("/api/upload", files={"file": ("mixed.pdf", source.read_bytes(), "application/pdf")})
        assert upload.status_code == 200
        response = client.post("/api/stamp", json={
            "file_id": upload.json()["file_id"], "process_number": "123/2026",
            "start_date": "16/11/2026", "start_leaf": 1, "volume_limit": 200,
            "reserve_terms": False, "rotate_landscape": rotate_landscape,
            "global_coords": {"x0": 11, "y0": 12, "scale": 1},
            "orientation_coords": {
                "portrait": {"x0": 100, "y0": 110, "scale": 1},
                "landscape": {"x0": 200, "y0": 210, "scale": 1},
            },
            "custom_coords": {"2": {"x0": 300, "y0": 130, "scale": 0.8}},
            "active_pages": [0, 1, 2],
        })
    assert response.status_code == 200
    with fitz.open(stream=response.content, filetype="pdf") as doc:
        assert len(doc) == 4
        for idx, position in enumerate([(100, 110), (200, 210), (300, 130)]):
            page = doc[idx]
            rect = page.get_drawings()[0]["rect"] * page.rotation_matrix
            assert (rect.x0, rect.y0) == pytest.approx(position, abs=0.01)
            assert "ORIGINAL" in page.get_text()
        assert not doc[3].get_drawings()
