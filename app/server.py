"""
DocToMD Suite - FastAPI Web Server
Fornisce API REST e Interfaccia Web moderna per la Suite di elaborazione PDF:
1. Conversione PDF in Markdown
2. Compressione intelligente PDF
3. Unione di più PDF (Merge)
4. Divisione ed estrazione pagine (Split)
5. Esportazione pagine PDF in immagini PNG (PDF to Images)
"""

import os
import io
import uuid
import shutil
import zipfile
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.converter import (
    convert_pdf_to_markdown,
    compress_pdf,
    merge_pdfs,
    split_pdf,
    pdf_to_images_zip,
    perform_ocr_on_image,
    perform_ocr_on_pdf
)

app = FastAPI(
    title="DocToMD Suite - Swiss Army Knife for Documents",
    description="Applicazione moderna e ultra-veloce per convertire, comprimere, unire e dividere documenti PDF",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR = BASE_DIR / "templates"
STORAGE_DIR = BASE_DIR.parent / ".temp_storage"
STORAGE_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def cleanup_temp_file(filepath: Path):
    """Pulisce file o cartelle temporanee."""
    try:
        if filepath.is_file():
            filepath.unlink(missing_ok=True)
        elif filepath.is_dir():
            shutil.rmtree(filepath, ignore_errors=True)
    except Exception:
        pass


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve la pagina principale dell'interfaccia utente (Suite DocToMD)."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "DocToMD Suite", "version": "2.0.0"}


# =====================================================================
# 1. API: CONVERSIONE PDF IN MARKDOWN
# =====================================================================

@app.post("/api/convert")
async def convert_single_pdf(
    file: UploadFile = File(...),
    extract_images: bool = Form(False),
    include_frontmatter: bool = Form(True),
    add_page_separators: bool = Form(False),
):
    """Converte un singolo PDF in Markdown strutturato."""
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

        md_filename = f"{base_name}.md"
        md_path = job_dir / md_filename
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(result["markdown"])

        zip_available = False
        zip_filename = None

        if extract_images and image_dir and image_dir.exists() and result["image_count"] > 0:
            zip_filename = f"{base_name}_markdown.zip"
            zip_path = job_dir / zip_filename
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.write(md_path, arcname=md_filename)
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
        raise HTTPException(status_code=500, detail=f"Errore nella conversione: {str(e)}")


@app.post("/api/convert-batch")
async def convert_batch_pdfs(
    files: List[UploadFile] = File(...),
    extract_images: bool = Form(False),
    include_frontmatter: bool = Form(True),
    add_page_separators: bool = Form(False),
):
    """Converte più file PDF e li raggruppa in un unico archivio ZIP scaricabile."""
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

                md_bytes = res["markdown"].encode("utf-8")
                master_zip.writestr(f"{base_name}.md", md_bytes)

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


# =====================================================================
# 2. API: COMPRESSIONE PDF
# =====================================================================

@app.post("/api/compress")
async def api_compress_pdf(
    file: UploadFile = File(...),
    level: str = Form("medium")
):
    """Comprime un file PDF e restituisce il file ottimizzato con le statistiche."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Il file fornito deve essere un PDF.")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Il file caricato è vuoto.")

    try:
        compressed_bytes, orig_size, new_size, saved_pct = compress_pdf(contents, level=level)
        clean_name = Path(file.filename).stem
        download_name = f"{clean_name}_compresso.pdf"

        # Headers con statistiche per il client
        headers = {
            "Content-Disposition": f'attachment; filename="{download_name}"',
            "X-Original-Size": str(orig_size),
            "X-New-Size": str(new_size),
            "X-Saved-Percent": str(saved_pct)
        }

        return Response(
            content=compressed_bytes,
            media_type="application/pdf",
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante la compressione: {str(e)}")


# =====================================================================
# 3. API: UNISCI PDF (MERGE)
# =====================================================================

@app.post("/api/merge")
async def api_merge_pdfs(files: List[UploadFile] = File(...)):
    """Unisce più file PDF in un unico documento."""
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Seleziona almeno 2 file PDF da unire.")

    pdf_buffers = []
    for f in files:
        if f.filename.lower().endswith(".pdf"):
            data = await f.read()
            if len(data) > 0:
                pdf_buffers.append(data)

    if len(pdf_buffers) < 2:
        raise HTTPException(status_code=400, detail="Almeno 2 file PDF validi devono essere forniti.")

    try:
        merged_bytes, total_pages = merge_pdfs(pdf_buffers)
        headers = {
            "Content-Disposition": 'attachment; filename="documento_unito.pdf"',
            "X-Total-Pages": str(total_pages)
        }
        return Response(
            content=merged_bytes,
            media_type="application/pdf",
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante l'unione dei PDF: {str(e)}")


# =====================================================================
# 4. API: DIVIDI PDF (SPLIT)
# =====================================================================

@app.post("/api/split")
async def api_split_pdf(
    file: UploadFile = File(...),
    page_selection: str = Form(...)
):
    """Estrae un intervallo di pagine (es. '1-3, 5') da un PDF."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Il file fornito deve essere un PDF.")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Il file caricato è vuoto.")

    try:
        split_bytes, count = split_pdf(contents, page_selection)
        clean_name = Path(file.filename).stem
        headers = {
            "Content-Disposition": f'attachment; filename="{clean_name}_estratto.pdf"',
            "X-Extracted-Pages": str(count)
        }
        return Response(
            content=split_bytes,
            media_type="application/pdf",
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Errore durante la divisione: {str(e)}")


# =====================================================================
# 5. API: PDF TO IMMAGINI
# =====================================================================

@app.post("/api/pdf-to-images")
async def api_pdf_to_images(
    file: UploadFile = File(...),
    dpi: int = Form(150)
):
    """Converte ogni pagina del PDF in un'immagine PNG racchiusa in uno ZIP."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Il file fornito deve essere un PDF.")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Il file caricato è vuoto.")

    try:
        zip_bytes, page_count = pdf_to_images_zip(contents, dpi=dpi)
        clean_name = Path(file.filename).stem
        headers = {
            "Content-Disposition": f'attachment; filename="{clean_name}_immagini.zip"',
            "X-Image-Count": str(page_count)
        }
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante l'esportazione in immagini: {str(e)}")


# =====================================================================
# 6. API: RICONOSCIMENTO OTTICO CARATTERI (OCR)
# =====================================================================

@app.post("/api/ocr")
async def api_ocr(file: UploadFile = File(...)):
    """
    Esegue OCR su PDF scansionati o file immagine (PNG, JPG, JPEG, WEBP).
    Restituisce Markdown strutturato, confidenza media e tempo.
    """
    filename_lower = file.filename.lower()
    valid_extensions = (".pdf", ".png", ".jpg", ".jpeg", ".webp")
    if not any(filename_lower.endswith(ext) for ext in valid_extensions):
        raise HTTPException(
            status_code=400,
            detail="Formato non supportato. Carica un PDF o un'immagine (.png, .jpg, .jpeg, .webp)."
        )

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Il file caricato è vuoto.")

    job_id = str(uuid.uuid4())
    job_dir = STORAGE_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    base_name = Path(file.filename).stem

    try:
        if filename_lower.endswith(".pdf"):
            result = perform_ocr_on_pdf(contents)
        else:
            result = perform_ocr_on_image(contents)

        md_filename = f"{base_name}_ocr.md"
        md_path = job_dir / md_filename
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(result["markdown"])

        return {
            "success": True,
            "filename": file.filename,
            "job_id": job_id,
            "md_filename": md_filename,
            "page_count": result.get("page_count", 1),
            "word_count": result["word_count"],
            "confidence": result["confidence"],
            "elapsed_ms": result["elapsed_ms"],
            "lines_count": result["lines_count"],
            "markdown": result["markdown"]
        }
    except Exception as e:
        cleanup_temp_file(job_dir)
        raise HTTPException(status_code=500, detail=f"Errore durante l'elaborazione OCR: {str(e)}")


# =====================================================================
# 7. DOWNLOAD HANDLER PER LE SESSIONI MARKDOWN & OCR
# =====================================================================

@app.get("/api/download/{job_id}/{file_type}")
async def download_file(job_id: str, file_type: str, background_tasks: BackgroundTasks):
    """Scarica il file generato dalla sessione Markdown (.md o .zip)."""
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
