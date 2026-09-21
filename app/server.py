"""
DocToMD - FastAPI Web Server
Fornisce API REST e Interfaccia Web per la conversione di PDF in Markdown.
"""

import os
import io
import uuid
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.converter import convert_pdf_to_markdown

app = FastAPI(
    title="DocToMD - PDF to Markdown Converter",
    description="Applicazione moderna e ultra-veloce per convertire documenti PDF in Markdown pulito",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STORAGE_DIR = BASE_DIR.parent / ".temp_storage"
STORAGE_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def cleanup_temp_file(filepath: Path):
    """Pulisce file o cartelle temporanee dopo il download."""
    try:
        if filepath.is_file():
            filepath.unlink(missing_ok=True)
        elif filepath.is_dir():
            shutil.rmtree(filepath, ignore_errors=True)
    except Exception:
        pass


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve la pagina principale dell'interfaccia utente."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "DocToMD"}


@app.post("/api/convert")
async def convert_single_pdf(
    file: UploadFile = File(...),
    extract_images: bool = Form(False),
    include_frontmatter: bool = Form(True),
    add_page_separators: bool = Form(False),
):
    """
    Converte un singolo file PDF in Markdown.
    Restituisce i dati del Markdown convertito e ID per il download.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Il file fornito deve essere in formato PDF.")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Il file caricato è vuoto.")

    job_id = str(uuid.uuid4())
    job_dir = STORAGE_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    image_dir = job_dir / "images" if extract_images else None
    image_dir_str = str(image_dir) if image_dir else None

    base_name = Path(file.filename).stem

    try:
        result = convert_pdf_to_markdown(
            pdf_source=contents,
            extract_images=extract_images,
            output_image_dir=image_dir_str,
            image_rel_path="./images",
            include_frontmatter=include_frontmatter,
            add_page_separators=add_page_separators
        )

        # Salva il file Markdown su disco per il download
        md_filename = f"{base_name}.md"
        md_path = job_dir / md_filename
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(result["markdown"])

        zip_available = False
        zip_filename = None

        # Se ci sono immagini estratte, crea anche uno zip con .md + cartella immagini
        if extract_images and image_dir and image_dir.exists() and result["image_count"] > 0:
            zip_filename = f"{base_name}_markdown.zip"
            zip_path = job_dir / zip_filename
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
                # Aggiungi file markdown
                zip_file.write(md_path, arcname=md_filename)
                # Aggiungi immagini
                for img_file in image_dir.glob("*.*"):
                    zip_file.write(img_file, arcname=f"images/{img_file.name}")
            zip_available = True

        return {
            "success": True,
            "filename": file.filename,
            "job_id": job_id,
            "md_filename": md_filename,
            "has_zip": zip_available,
            "zip_filename": zip_filename,
            "page_count": result["page_count"],
            "word_count": result["word_count"],
            "elapsed_ms": result["elapsed_ms"],
            "is_scanned": result["is_scanned"],
            "scan_warning": result["scan_warning"],
            "image_count": result["image_count"],
            "metadata": result["metadata"],
            "markdown": result["markdown"]
        }
    except Exception as e:
        cleanup_temp_file(job_dir)
        raise HTTPException(status_code=500, detail=f"Errore durante la conversione: {str(e)}")


@app.post("/api/convert-batch")
async def convert_batch_pdfs(
    files: List[UploadFile] = File(...),
    extract_images: bool = Form(False),
    include_frontmatter: bool = Form(True),
    add_page_separators: bool = Form(False),
):
    """
    Converte un elenco di file PDF e li raggruppa in un unico archivio ZIP scaricabile.
    """
    if not files:
        raise HTTPException(status_code=400, detail="Nessun file selezionato.")

    job_id = str(uuid.uuid4())
    job_dir = STORAGE_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    results_summary = []
    zip_path = job_dir / "tutti_i_documenti_markdown.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as master_zip:
        for file in files:
            if not file.filename.lower().endswith(".pdf"):
                continue

            contents = await file.read()
            if len(contents) == 0:
                continue

            base_name = Path(file.filename).stem
            file_img_dir = job_dir / f"{base_name}_images" if extract_images else None

            try:
                res = convert_pdf_to_markdown(
                    pdf_source=contents,
                    extract_images=extract_images,
                    output_image_dir=str(file_img_dir) if file_img_dir else None,
                    image_rel_path=f"./{base_name}_images",
                    include_frontmatter=include_frontmatter,
                    add_page_separators=add_page_separators
                )

                # Salva md nel master zip
                md_bytes = res["markdown"].encode("utf-8")
                master_zip.writestr(f"{base_name}.md", md_bytes)

                # Se ci sono immagini, salvale nel zip
                if extract_images and file_img_dir and file_img_dir.exists():
                    for img in file_img_dir.glob("*.*"):
                        master_zip.write(img, arcname=f"{base_name}_images/{img.name}")

                results_summary.append({
                    "filename": file.filename,
                    "pages": res["page_count"],
                    "words": res["word_count"],
                    "elapsed_ms": res["elapsed_ms"],
                    "image_count": res["image_count"],
                    "is_scanned": res["is_scanned"],
                    "status": "success"
                })
            except Exception as ex:
                results_summary.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": str(ex)
                })

    return {
        "success": True,
        "job_id": job_id,
        "zip_filename": "tutti_i_documenti_markdown.zip",
        "processed_count": len(results_summary),
        "results": results_summary
    }


@app.get("/api/download/{job_id}/{file_type}")
async def download_file(job_id: str, file_type: str, background_tasks: BackgroundTasks):
    """
    Scarica il file generato (.md o .zip).
    file_type: 'md' oppure 'zip'.
    """
    job_dir = STORAGE_DIR / job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Sessione di conversione scaduta o non trovata.")

    if file_type == "md":
        md_files = list(job_dir.glob("*.md"))
        if not md_files:
            raise HTTPException(status_code=404, detail="File Markdown non trovato.")
        target_file = md_files[0]
        return FileResponse(
            path=target_file,
            filename=target_file.name,
            media_type="text/markdown; charset=utf-8"
        )
    elif file_type == "zip":
        zip_files = list(job_dir.glob("*.zip"))
        if not zip_files:
            raise HTTPException(status_code=404, detail="Archivio ZIP non trovato.")
        target_file = zip_files[0]
        return FileResponse(
            path=target_file,
            filename=target_file.name,
            media_type="application/zip"
        )
    else:
        raise HTTPException(status_code=400, detail="Tipo di file non valido.")
