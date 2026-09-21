"""
Test suite end-to-end per DocToMD:
- Generazione PDF sintetico con testo, immagini, formattazione e metadati
- Test modulo converter.py (PyMuPDF4LLM + post-processing)
- Test rilevamento scansione OCR
- Test CLI (cli.py)
- Test API FastAPI (app/server.py)
"""

import os
import io
import pytest
import pymupdf as fitz
from pathlib import Path
from starlette.testclient import TestClient

from app.converter import convert_pdf_to_markdown, is_scanned_pdf, clean_hyphenation
from app.server import app


def create_sample_pdf(output_path: Path) -> Path:
    """Crea un PDF di test con titoli, paragrafi, sillabazione, metadati e una immagine."""
    doc = fitz.open()

    # Pagina 1
    page1 = doc.new_page()
    page1.insert_text((50, 70), "Guida alla Trasformazione Digitale", fontsize=22)
    page1.insert_text((50, 110), "Sezione 1: Panoramica Generale", fontsize=16)
    
    # Testo con sillabazione da ripulire
    sample_text = (
        "Questa è una dimostrazione della straordi-\n"
        "naria velocità di elaborazione dei documenti.\n"
        "I vantaggi sono molteplici e quantifi-\n"
        "cabili in modo chiaro."
    )
    page1.insert_text((50, 150), sample_text, fontsize=11)

    # Inserisci una piccola immagine (quadrato verde)
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 100), 1)
    pix.clear_with(0x22C55E)  # Verde Tailwind
    img_rect = fitz.Rect(50, 240, 150, 340)
    page1.insert_image(img_rect, pixmap=pix)

    # Pagina 2
    page2 = doc.new_page()
    page2.insert_text((50, 70), "Sezione 2: Specifiche Tecniche", fontsize=16)
    page2.insert_text((50, 100), "Dettaglio delle performance e compatibilità con standard Markdown GFM.", fontsize=11)

    # Imposta metadati
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
    """Crea un PDF simulato come scansione: solo immagine raster senza caratteri di testo."""
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
    input_text = "straordi-\nnaria opera di clas-\nsificazione e auto- \nmazione."
    cleaned = clean_hyphenation(input_text)
    assert "straordinaria" in cleaned
    assert "classificazione" in cleaned
    assert "automazione" in cleaned


def test_converter_basic(sample_pdf_path, tmp_path):
    """Test motore convert_pdf_to_markdown con estrazione testi e metadati."""
    result = convert_pdf_to_markdown(
        pdf_source=str(sample_pdf_path),
        extract_images=False,
        include_frontmatter=True,
        add_page_separators=False
    )

    assert result["page_count"] == 2
    assert result["word_count"] > 10
    assert result["elapsed_ms"] > 0
    assert result["is_scanned"] is False
    assert result["metadata"]["title"] == "Documento Test DocToMD"

    md = result["markdown"]
    # Verifica frontmatter
    assert "---" in md
    assert 'title: "Documento Test DocToMD"' in md
    # Verifica rimozione sillabazione
    assert "straordinaria" in md
    assert "quantificabili" in md


def test_converter_images(sample_pdf_path, tmp_path):
    """Test estrazione e collegamento immagini."""
    img_dir = tmp_path / "extracted_images"
    result = convert_pdf_to_markdown(
        pdf_source=str(sample_pdf_path),
        extract_images=True,
        output_image_dir=str(img_dir),
        image_rel_path="./extracted_images"
    )

    assert result["image_count"] >= 1
    assert img_dir.exists()
    assert len(list(img_dir.glob("*.png"))) >= 1


def test_scanned_pdf_detection(scanned_pdf_path):
    """Test rilevamento automatico di PDF scansionato."""
    result = convert_pdf_to_markdown(
        pdf_source=str(scanned_pdf_path),
        extract_images=False
    )
    assert result["is_scanned"] is True
    assert "scansione" in result["scan_warning"].lower()


def test_fastapi_endpoints(sample_pdf_path):
    """Test endpoint API FastAPI."""
    client = TestClient(app)

    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # 2. Home page HTML
    res = client.get("/")
    assert res.status_code == 200
    assert "DocToMD" in res.text

    # 3. Conversione file singolo
    with open(sample_pdf_path, "rb") as f:
        res = client.post(
            "/api/convert",
            files={"file": ("test_doc.pdf", f, "application/pdf")},
            data={"extract_images": "true", "include_frontmatter": "true"}
        )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["page_count"] == 2
    assert "straordinaria" in data["markdown"]
    job_id = data["job_id"]

    # 4. Download file .md
    res_md = client.get(f"/api/download/{job_id}/md")
    assert res_md.status_code == 200
    assert res_md.headers["content-type"].startswith("text/markdown")

    # 5. Conversione batch
    with open(sample_pdf_path, "rb") as f1, open(sample_pdf_path, "rb") as f2:
        res_batch = client.post(
            "/api/convert-batch",
            files=[
                ("files", ("doc1.pdf", f1, "application/pdf")),
                ("files", ("doc2.pdf", f2, "application/pdf")),
            ],
            data={"include_frontmatter": "true"}
        )
    assert res_batch.status_code == 200
    batch_data = res_batch.json()
    assert batch_data["processed_count"] == 2
    batch_job_id = batch_data["job_id"]

    # Download ZIP batch
    res_zip = client.get(f"/api/download/{batch_job_id}/zip")
    assert res_zip.status_code == 200
    assert res_zip.headers["content-type"] == "application/zip"
