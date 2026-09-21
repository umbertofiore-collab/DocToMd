"""
Test suite end-to-end per DocToMD Suite:
- Test modulo converter.py (PyMuPDF4LLM + post-processing)
- Test compressione PDF
- Test unione PDF (merge)
- Test divisione PDF (split)
- Test esportazione immagini PNG in ZIP
- Test rilevamento scansione OCR
- Test API FastAPI per tutti i tool
"""

import os
import io
import pytest
import pymupdf as fitz
from pathlib import Path
from starlette.testclient import TestClient

from app.converter import (
    convert_pdf_to_markdown,
    is_scanned_pdf,
    clean_hyphenation,
    compress_pdf,
    merge_pdfs,
    split_pdf,
    pdf_to_images_zip
)
from app.server import app


def create_sample_pdf(output_path: Path) -> Path:
    """Crea un PDF di test a 3 pagine con testi, immagini e metadati."""
    doc = fitz.open()

    # Pagina 1
    page1 = doc.new_page()
    page1.insert_text((50, 70), "Guida alla Trasformazione Digitale", fontsize=22)
    page1.insert_text((50, 110), "Sezione 1: Panoramica Generale", fontsize=16)
    sample_text = (
        "Questa è una dimostrazione della straordi-\n"
        "naria velocità di elaborazione dei documenti.\n"
        "I vantaggi sono molteplici e quantifi-\n"
        "cabili in modo chiaro."
    )
    page1.insert_text((50, 150), sample_text, fontsize=11)

    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 100), 1)
    pix.clear_with(0x22C55E)
    page1.insert_image(fitz.Rect(50, 240, 150, 340), pixmap=pix)

    # Pagina 2
    page2 = doc.new_page()
    page2.insert_text((50, 70), "Sezione 2: Specifiche Tecniche", fontsize=16)
    page2.insert_text((50, 100), "Dettaglio delle performance e compatibilità con standard Markdown GFM.", fontsize=11)

    # Pagina 3
    page3 = doc.new_page()
    page3.insert_text((50, 70), "Sezione 3: Appendice e Note Finali", fontsize=16)
    page3.insert_text((50, 100), "Conclusioni e riferimenti bibliografici per approfondimenti futuri.", fontsize=11)

    doc.set_metadata({
        "title": "Documento Test DocToMD",
        "author": "Antigravity Tester",
        "subject": "Collaudo e Validazione",
        "creator": "PyMuPDF Test Suite"
    })

    doc.save(str(output_path))
    doc.close()
    return output_path


def create_scanned_dummy_pdf(output_path: Path) -> Path:
    """Crea un PDF privo di caratteri di testo vettoriale."""
    doc = fitz.open()
    page = doc.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 400, 600), 1)
    pix.clear_with(0xCCCCCC)
    page.insert_image(fitz.Rect(0, 0, 400, 600), pixmap=pix)
    doc.save(str(output_path))
    doc.close()
    return output_path


@pytest.fixture(scope="session")
def sample_pdf_path(tmp_path_factory):
    fn = tmp_path_factory.mktemp("data") / "test_doc.pdf"
    return create_sample_pdf(fn)


@pytest.fixture(scope="session")
def scanned_pdf_path(tmp_path_factory):
    fn = tmp_path_factory.mktemp("data") / "scanned_doc.pdf"
    return create_scanned_dummy_pdf(fn)


def test_clean_hyphenation():
    """Test pulizia sillabazioni a fine riga."""
    input_text = "straordi-\nnaria opera di clas-\nsificazione."
    cleaned = clean_hyphenation(input_text)
    assert "straordinaria" in cleaned
    assert "classificazione" in cleaned


def test_converter_basic(sample_pdf_path):
    """Test motore conversione Markdown."""
    result = convert_pdf_to_markdown(str(sample_pdf_path), extract_images=False)
    assert result["page_count"] == 3
    assert result["word_count"] > 10
    assert result["is_scanned"] is False
    assert "straordinaria" in result["markdown"]


def test_compress_pdf(sample_pdf_path):
    """Test motore di compressione PDF."""
    with open(sample_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    comp_bytes, orig_size, new_size, saved_pct = compress_pdf(pdf_bytes, level="medium")
    assert len(comp_bytes) > 0
    assert orig_size == len(pdf_bytes)
    assert new_size <= orig_size


def test_merge_pdfs(sample_pdf_path):
    """Test unione di 2 PDF."""
    with open(sample_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    merged_bytes, total_pages = merge_pdfs([pdf_bytes, pdf_bytes])
    assert total_pages == 6
    assert len(merged_bytes) > 0


def test_split_pdf(sample_pdf_path):
    """Test estrazione pagine specifiche."""
    with open(sample_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    split_bytes, count = split_pdf(pdf_bytes, "1, 3")
    assert count == 2
    doc = fitz.open(stream=split_bytes, filetype="pdf")
    assert len(doc) == 2
    doc.close()


def test_pdf_to_images(sample_pdf_path):
    """Test esportazione pagine in archivio ZIP di immagini."""
    with open(sample_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    zip_bytes, count = pdf_to_images_zip(pdf_bytes, dpi=72)
    assert count == 3
    assert len(zip_bytes) > 0


def test_fastapi_endpoints_suite(sample_pdf_path):
    """Test suite completa endpoint API FastAPI."""
    client = TestClient(app)

    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["service"] == "DocToMD Suite"

    # 2. Home page HTML
    res = client.get("/")
    assert res.status_code == 200
    assert "DocToMD Suite" in res.text

    # 3. Conversione PDF in Markdown
    with open(sample_pdf_path, "rb") as f:
        res = client.post(
            "/api/convert",
            files={"file": ("test_doc.pdf", f, "application/pdf")},
            data={"extract_images": "false", "include_frontmatter": "true"}
        )
    assert res.status_code == 200
    assert res.json()["success"] is True

    # 4. Compressione PDF
    with open(sample_pdf_path, "rb") as f:
        res_comp = client.post(
            "/api/compress",
            files={"file": ("test_doc.pdf", f, "application/pdf")},
            data={"level": "medium"}
        )
    assert res_comp.status_code == 200
    assert res_comp.headers["content-type"] == "application/pdf"
    assert "X-Saved-Percent" in res_comp.headers

    # 5. Unione PDF (Merge)
    with open(sample_pdf_path, "rb") as f1, open(sample_pdf_path, "rb") as f2:
        res_merge = client.post(
            "/api/merge",
            files=[
                ("files", ("doc1.pdf", f1, "application/pdf")),
                ("files", ("doc2.pdf", f2, "application/pdf")),
            ]
        )
    assert res_merge.status_code == 200
    assert res_merge.headers["X-Total-Pages"] == "6"

    # 6. Divisione PDF (Split)
    with open(sample_pdf_path, "rb") as f:
        res_split = client.post(
            "/api/split",
            files={"file": ("test_doc.pdf", f, "application/pdf")},
            data={"page_selection": "1-2"}
        )
    assert res_split.status_code == 200
    assert res_split.headers["X-Extracted-Pages"] == "2"

    # 7. PDF to Images
    with open(sample_pdf_path, "rb") as f:
        res_img = client.post(
            "/api/pdf-to-images",
            files={"file": ("test_doc.pdf", f, "application/pdf")},
            data={"dpi": "72"}
        )
    assert res_img.status_code == 200
    assert res_img.headers["content-type"] == "application/zip"
