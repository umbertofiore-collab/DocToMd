#!/usr/bin/env python3
"""
DocToMD - Interfaccia a Riga di Comando (CLI)
Consente di convertire rapidamente file PDF singoli o intere cartelle in Markdown.

Esempi di utilizzo:
    python cli.py documento.pdf
    python cli.py documento.pdf -o risultato.md --images
    python cli.py ./miei_pdf/ -o ./output_md/
"""

import sys
import argparse
from pathlib import Path
from app.converter import convert_pdf_to_markdown

# Colori ANSI per il terminale
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def process_single_file(
    input_path: Path,
    output_path: Path,
    extract_images: bool,
    include_frontmatter: bool,
    add_page_separators: bool,
    quiet: bool = False
) -> bool:
    """Converte un singolo file PDF e lo salva su output_path."""
    try:
        image_dir = output_path.parent / f"{output_path.stem}_images" if extract_images else None
        image_rel = f"./{output_path.stem}_images" if extract_images else ""

        result = convert_pdf_to_markdown(
            pdf_source=str(input_path),
            extract_images=extract_images,
            output_image_dir=str(image_dir) if image_dir else None,
            image_rel_path=image_rel,
            include_frontmatter=include_frontmatter,
            add_page_separators=add_page_separators
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result["markdown"])

        if not quiet:
            print(f"  {GREEN}✓{RESET} {BOLD}{input_path.name}{RESET} ➔ {CYAN}{output_path.name}{RESET} "
                  f"({result['page_count']} pag, {result['word_count']} parole, {result['elapsed_ms']}ms)")

            if result["is_scanned"]:
                print(f"    {YELLOW}⚠ Avviso: {result['scan_warning']}{RESET}")

            if extract_images and result["image_count"] > 0:
                print(f"    {CYAN}↳ Estratte {result['image_count']} immagini in: {image_dir}{RESET}")

        return True
    except Exception as e:
        if not quiet:
            print(f"  {RED}✗ Errore su {input_path.name}: {e}{RESET}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="DocToMD CLI - Convertitore rapido da PDF a Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Esempi:
  python cli.py doc.pdf                      # Genera doc.md
  python cli.py doc.pdf -o out.md --images   # Estrae anche immagini
  python cli.py ./cartella/ -o ./dist/       # Converte tutti i PDF nella cartella
"""
    )

    parser.add_argument("input", type=str, help="File PDF o cartella contenente file PDF")
    parser.add_argument("-o", "--output", type=str, default=None, help="Percorso del file o della cartella di output")
    parser.add_argument("--images", action="store_true", help="Estrai e collega le immagini del PDF")
    parser.add_argument("--no-frontmatter", action="store_true", help="Non includere il blocco frontmatter YAML con i metadati")
    parser.add_argument("--separators", action="store_true", help="Aggiungi divisori orizzontali per ogni pagina")
    parser.add_argument("-q", "--quiet", action="store_true", help="Modalità silenziosa (riduce l'output a terminale)")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"{RED}Errore: il percorso specificato '{args.input}' non esiste.{RESET}", file=sys.stderr)
        sys.exit(1)

    include_frontmatter = not args.no_frontmatter

    print(f"\n{BOLD}{CYAN}=== DocToMD - PDF to Markdown Converter ==={RESET}")

    if input_path.is_file():
        if not input_path.name.lower().endswith(".pdf"):
            print(f"{RED}Errore: il file selezionato non ha estensione .pdf{RESET}", file=sys.stderr)
            sys.exit(1)

        if args.output:
            out_file = Path(args.output)
            if out_file.is_dir() or args.output.endswith("/"):
                out_file = out_file / f"{input_path.stem}.md"
        else:
            out_file = input_path.with_suffix(".md")

        success = process_single_file(
            input_path=input_path,
            output_path=out_file,
            extract_images=args.images,
            include_frontmatter=include_frontmatter,
            add_page_separators=args.separators,
            quiet=args.quiet
        )
        sys.exit(0 if success else 1)

    elif input_path.is_dir():
        pdf_files = sorted(list(input_path.glob("*.pdf")) + list(input_path.glob("*.PDF")))
        if not pdf_files:
            print(f"{YELLOW}Nessun file PDF trovato nella cartella '{input_path}'.{RESET}")
            sys.exit(0)

        out_dir = Path(args.output) if args.output else input_path / "markdown_output"
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"Trovati {len(pdf_files)} file PDF da convertire in: {CYAN}{out_dir}{RESET}\n")

        success_count = 0
        for pdf_file in pdf_files:
            out_file = out_dir / f"{pdf_file.stem}.md"
            if process_single_file(
                input_path=pdf_file,
                output_path=out_file,
                extract_images=args.images,
                include_frontmatter=include_frontmatter,
                add_page_separators=args.separators,
                quiet=args.quiet
            ):
                success_count += 1

        print(f"\n{BOLD}{GREEN}Operazione completata: {success_count}/{len(pdf_files)} file convertiti con successo!{RESET}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
