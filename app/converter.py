"""
DocToMD Suite - Motore di Elaborazione PDF ad Alte Prestazioni.
Fornisce strumenti avanzati per:
1. Conversione PDF in Markdown (PyMuPDF4LLM)
2. Compressione intelligente PDF (ottimizzazione immagini e stream)
3. Unione di più PDF (Merge)
4. Divisione ed estrazione pagine (Split)
5. Conversione pagine PDF in immagini PNG ad alta risoluzione
"""

import os
import io
import re
import time
import zipfile
import pymupdf as fitz
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path


# =====================================================================
# 1. STRUMENTO: CONVERSIONE PDF IN MARKDOWN
# =====================================================================

def clean_hyphenation(text: str) -> str:
    """Rimuove le sillabazioni a fine riga (es. 'straordi-\\n naria' -> 'straordinaria')."""
    pattern = r'([a-zA-Z\u00C0-\u017F]+)-\s*\n\s*([a-z\u00C0-\u017F]+)'
    return re.sub(pattern, r'\1\2', text)


def clean_blank_lines(text: str) -> str:
    """Normalizza righe vuote consecutive eccessive (max 2 consecutive)."""
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def extract_metadata_frontmatter(doc: fitz.Document, page_count: int) -> str:
    """Estrae i metadati nativi del PDF e genera un blocco YAML frontmatter."""
    meta = doc.metadata or {}
    title = meta.get("title", "").strip() or "Senza Titolo"
    author = meta.get("author", "").strip()
    producer = meta.get("producer", "").strip()

    frontmatter = [
        "---",
        f'title: "{title}"',
        f'pages: {page_count}',
        f'converted_at: "{time.strftime("%Y-%m-%d %H:%M:%S")}"'
    ]
    if author:
        frontmatter.append(f'author: "{author}"')
    if producer:
        frontmatter.append(f'producer: "{producer}"')
    frontmatter.append("---\n\n")

    return "\n".join(frontmatter)


def is_scanned_pdf(doc: fitz.Document, text_content: str) -> Tuple[bool, str]:
    """Rileva se il documento è probabilmente una scansione / immagine priva di testo vettoriale."""
    page_count = len(doc)
    if page_count == 0:
        return True, "Il documento non contiene pagine."

    clean_chars = len(re.sub(r'\s+', '', text_content))
    avg_chars_per_page = clean_chars / max(page_count, 1)
    total_images = sum(len(page.get_images()) for page in doc)

    if avg_chars_per_page < 30 and total_images > 0:
        return True, (
            f"Attenzione: rilevati pochissimi caratteri vettoriali ({int(avg_chars_per_page)}/pagina) "
            f"e {total_images} immagini. Il PDF sembra essere una scansione o una foto."
        )

    return False, ""


def convert_pdf_to_markdown(
    pdf_source: str | bytes,
    extract_images: bool = False,
    output_image_dir: Optional[str] = None,
    image_rel_path: str = "./images",
    include_frontmatter: bool = True,
    add_page_separators: bool = False,
    page_range: Optional[List[int]] = None
) -> Dict[str, Any]:
    """Converte un PDF in Markdown strutturato."""
    start_time = time.perf_counter()

    try:
        import pymupdf4llm
    except ImportError:
        raise ImportError("pymupdf4llm non è installato. Esegui: pip install pymupdf4llm")

    if isinstance(pdf_source, bytes):
        doc = fitz.open(stream=pdf_source, filetype="pdf")
    else:
        doc = fitz.open(pdf_source)

    total_pages = len(doc)
    doc_metadata = doc.metadata or {}

    extracted_images_count = 0
    if extract_images and output_image_dir:
        os.makedirs(output_image_dir, exist_ok=True)

    if add_page_separators:
        chunks = pymupdf4llm.to_markdown(
            doc,
            pages=page_range,
            page_chunks=True,
            write_images=extract_images,
            image_path=output_image_dir or "",
            image_format="png"
        )
        md_parts = []
        for chunk in chunks:
            page_idx = chunk.get("metadata", {}).get("page", 0)
            page_text = chunk.get("text", "").strip()
            if page_text:
                md_parts.append(f"<!-- Page {page_idx + 1} -->\n\n{page_text}")
        raw_markdown = "\n\n---\n\n".join(md_parts)
    else:
        raw_markdown = pymupdf4llm.to_markdown(
            doc,
            pages=page_range,
            page_chunks=False,
            write_images=extract_images,
            image_path=output_image_dir or "",
            image_format="png"
        )

    if extract_images and output_image_dir and os.path.exists(output_image_dir):
        image_files = [f for f in os.listdir(output_image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        extracted_images_count = len(image_files)
        raw_markdown = raw_markdown.replace(str(Path(output_image_dir).resolve()), image_rel_path)
        raw_markdown = raw_markdown.replace(output_image_dir, image_rel_path)

    cleaned_md = clean_hyphenation(raw_markdown)
    cleaned_md = clean_blank_lines(cleaned_md)

    is_scanned, scan_warning = is_scanned_pdf(doc, cleaned_md)

    final_markdown = cleaned_md
    if include_frontmatter:
        frontmatter = extract_metadata_frontmatter(doc, total_pages)
        final_markdown = f"{frontmatter}{cleaned_md}"

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    words = len(re.findall(r'\b\w+\b', final_markdown))

    doc.close()

    return {
        "markdown": final_markdown,
        "page_count": total_pages,
        "word_count": words,
        "elapsed_ms": elapsed_ms,
        "is_scanned": is_scanned,
        "scan_warning": scan_warning,
        "image_count": extracted_images_count,
        "metadata": {
            "title": doc_metadata.get("title", ""),
            "author": doc_metadata.get("author", ""),
            "subject": doc_metadata.get("subject", ""),
            "keywords": doc_metadata.get("keywords", ""),
            "creator": doc_metadata.get("creator", ""),
            "producer": doc_metadata.get("producer", "")
        }
    }


# =====================================================================
# 2. STRUMENTO: COMPRESSIONE INTELLIGENTE PDF
# =====================================================================

def compress_pdf(pdf_bytes: bytes, level: str = "medium") -> Tuple[bytes, int, int, float]:
    """
    Comprime un documento PDF rimuovendo oggetti duplicati, ripulendo gli stream
    e ottimizzando le immagini incorporate.

    Livelli:
    - 'light': pulizia stream e garbage collection non distruttiva (qualità 100%)
    - 'medium': deflating avanzato + ottimizzazione moderata (consigliata, ottima leggibilità)
    - 'strong': massima compressione per invio via email / upload portali

    Returns:
        Tuple[bytes, original_size, new_size, saving_percent]
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    original_size = len(pdf_bytes)

    if level == "strong":
        # Ricomprimi immagini interne con qualità JPEG più efficiente
        for page in doc:
            image_list = page.get_images()
            for img_info in image_list:
                xref = img_info[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                    if pix.colorspace and pix.colorspace.n >= 4:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    # Ricomprimi in JPEG a qualità 60%
                    img_data = pix.tobytes("jpeg", jpg_quality=60)
                    doc.update_stream(xref, img_data)
                except Exception:
                    pass
        garbage_level = 4
        deflate_setting = True
    elif level == "medium":
        garbage_level = 4
        deflate_setting = True
    else:  # light
        garbage_level = 3
        deflate_setting = True

    output_buffer = io.BytesIO()
    doc.save(
        output_buffer,
        garbage=garbage_level,
        deflate=deflate_setting,
        clean=True,
        deflate_images=True,
        deflate_fonts=True
    )
    compressed_bytes = output_buffer.getvalue()
    doc.close()

    new_size = len(compressed_bytes)
    # Se il PDF era già compresso e l'output è maggiore, restituisci l'originale
    if new_size >= original_size:
        compressed_bytes = pdf_bytes
        new_size = original_size
        saving_percent = 0.0
    else:
        saving_percent = round(((original_size - new_size) / original_size) * 100, 1)

    return compressed_bytes, original_size, new_size, saving_percent


# =====================================================================
# 3. STRUMENTO: UNISCI PIÙ PDF (MERGE)
# =====================================================================

def merge_pdfs(pdf_list: List[bytes]) -> Tuple[bytes, int]:
    """
    Fonde un elenco di documenti PDF in un unico file cumulativo.

    Returns:
        Tuple[merged_pdf_bytes, total_pages]
    """
    merged_doc = fitz.open()

    for pdf_bytes in pdf_list:
        sub_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        merged_doc.insert_pdf(sub_doc)
        sub_doc.close()

    total_pages = len(merged_doc)
    output_buffer = io.BytesIO()
    merged_doc.save(output_buffer, garbage=3, deflate=True)
    merged_bytes = output_buffer.getvalue()
    merged_doc.close()

    return merged_bytes, total_pages


# =====================================================================
# 4. STRUMENTO: DIVIDI ED ESTRAI PAGINE (SPLIT)
# =====================================================================

def parse_page_range(range_str: str, max_pages: int) -> List[int]:
    """
    Converte una stringa come '1-3, 5, 7-9' in una lista ordinata di indici 0-based.
    """
    pages = set()
    parts = range_str.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            sub = part.split("-")
            start = int(sub[0].strip())
            end = int(sub[1].strip())
            for p in range(start, end + 1):
                if 1 <= p <= max_pages:
                    pages.add(p - 1)
        else:
            p = int(part)
            if 1 <= p <= max_pages:
                pages.add(p - 1)
    return sorted(list(pages))


def split_pdf(pdf_bytes: bytes, page_selection: str) -> Tuple[bytes, int]:
    """
    Estrae solo le pagine indicate (es. '1-3, 5, 8') e genera un nuovo PDF.

    Returns:
        Tuple[split_pdf_bytes, extracted_pages_count]
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    max_pages = len(doc)
    page_indices = parse_page_range(page_selection, max_pages)

    if not page_indices:
        doc.close()
        raise ValueError("Nessuna pagina valida selezionata.")

    doc.select(page_indices)
    output_buffer = io.BytesIO()
    doc.save(output_buffer, garbage=3, deflate=True)
    split_bytes = output_buffer.getvalue()
    extracted_count = len(doc)
    doc.close()

    return split_bytes, extracted_count


# =====================================================================
# 5. STRUMENTO: PDF TO IMMAGINI AD ALTA RISOLUZIONE
# =====================================================================

def pdf_to_images_zip(pdf_bytes: bytes, dpi: int = 150) -> Tuple[bytes, int]:
    """
    Trasforma ogni singola pagina del PDF in un'immagine PNG nitida e le raccoglie in uno ZIP.

    Returns:
        Tuple[zip_bytes, image_count]
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as master_zip:
        for page_idx in range(total_pages):
            page = doc[page_idx]
            pix = page.get_pixmap(dpi=dpi)
            png_bytes = pix.tobytes("png")
            filename = f"pagina_{page_idx + 1:03d}.png"
            master_zip.writestr(filename, png_bytes)

    doc.close()
    return zip_buffer.getvalue(), total_pages
