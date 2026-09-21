"""
DocToMD - Motore di Conversione PDF to Markdown ad Alte Prestazioni.
Utilizza PyMuPDF e PyMuPDF4LLM con post-processing intelligente per:
- Conservare la gerarchia dei titoli (#, ##, ###)
- Convertire tabelle in Markdown GFM valido
- Estrarre e collegare le immagini
- Rimuovere sillabazioni a fine riga (de-hyphenation)
- Aggiungere metadati YAML (Frontmatter)
- Rilevare PDF scansionati privi di testo nativo (OCR alert)
"""

import os
import re
import time
import pymupdf as fitz
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path


def clean_hyphenation(text: str) -> str:
    """
    Rimuove le sillabazioni a fine riga.
    Es: 'istru- \\n zione' o 'innova-\\ntivo' -> 'istruzione', 'innovativo'.
    Preserva i trattini composti legittimi (es. 'e-mail', 'Nord-Est').
    """
    # Pattern per parola che termina con trattino seguito da a capo e minuscola
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
    creation_date = meta.get("creationDate", "").strip()
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
    """
    Rileva se il documento è probabilmente una scansione / immagine
    con scarso o assente testo vettoriale.
    """
    page_count = len(doc)
    if page_count == 0:
        return True, "Il documento non contiene pagine."

    # Conta caratteri totali
    clean_chars = len(re.sub(r'\s+', '', text_content))
    avg_chars_per_page = clean_chars / max(page_count, 1)

    # Conta immagini presenti
    total_images = sum(len(page.get_images()) for page in doc)

    if avg_chars_per_page < 30 and total_images > 0:
        return True, (
            f"Attenzione: rilevati pochissimi caratteri vettoriali ({int(avg_chars_per_page)}/pagina) "
            f"e {total_images} immagini. Il PDF sembra essere una scansione cartacea o fotografica."
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
    """
    Converte un file PDF o flusso di byte in Markdown strutturato.

    Args:
        pdf_source: Percorso del file PDF oppure bytes del PDF.
        extract_images: Se True, estrae le immagini e le salva sul disco.
        output_image_dir: Cartella su disco dove salvare le immagini estratte.
        image_rel_path: Percorso relativo da usare nei link Markdown `![](...)`.
        include_frontmatter: Se True, include il frontmatter YAML con i metadati.
        add_page_separators: Se True, aggiunge separatori orizzontali e numero di pagina.
        page_range: Lista opzionale di indici pagina (0-indexed) da convertire.

    Returns:
        Dizionario con:
        - markdown: Testo Markdown finale
        - page_count: Numero di pagine totali
        - word_count: Numero parole approssimativo
        - elapsed_ms: Tempo impiegato in millisecondi
        - is_scanned: Booleano che indica se il PDF sembra scansionato
        - scan_warning: Messaggio descrittivo di avviso se scansionato
        - image_count: Numero di immagini estratte
        - metadata: Metadati estratti dal PDF
    """
    start_time = time.perf_counter()

    # Importa pymupdf4llm all'interno della funzione
    try:
        import pymupdf4llm
    except ImportError:
        raise ImportError(
            "pymupdf4llm non è installato. Esegui: pip install pymupdf4llm"
        )

    # Apertura documento con PyMuPDF
    if isinstance(pdf_source, bytes):
        doc = fitz.open(stream=pdf_source, filetype="pdf")
    else:
        doc = fitz.open(pdf_source)

    total_pages = len(doc)
    doc_metadata = doc.metadata or {}

    # Configurazione estrazione immagini
    extracted_images_count = 0
    if extract_images and output_image_dir:
        os.makedirs(output_image_dir, exist_ok=True)

    # Conversione con pymupdf4llm
    if add_page_separators:
        # Elaborazione pagina per pagina per aggiungere i separatori
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

    # Conteggio immagini estratte (se la directory esiste)
    if extract_images and output_image_dir and os.path.exists(output_image_dir):
        image_files = [f for f in os.listdir(output_image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        extracted_images_count = len(image_files)

        # Se image_path assoluto è finito nei link markdown, normalizziamo con image_rel_path
        if output_image_dir:
            raw_markdown = raw_markdown.replace(str(Path(output_image_dir).resolve()), image_rel_path)
            raw_markdown = raw_markdown.replace(output_image_dir, image_rel_path)

    # Post-processing: pulizia sillabazioni e ritorni a capo
    cleaned_md = clean_hyphenation(raw_markdown)
    cleaned_md = clean_blank_lines(cleaned_md)

    # Rilevamento documento scansionato
    is_scanned, scan_warning = is_scanned_pdf(doc, cleaned_md)

    # Aggiunta frontmatter opzionale
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
