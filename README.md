# DocToMD Suite - Il Coltellino Svizzero per Documenti PDF

Suite multifunzione moderna, ultra-veloce e 100% privata per lavorare con file PDF e Markdown.

Sviluppata con **PyMuPDF (C-Engine)**, **FastAPI** e **Tailwind CSS**.

---

## 🛠️ Strumenti Inclusi nella Suite

1. 📑 **PDF ➔ Markdown (Ultra-Fast)**
   - Conversione istantanea con conservazione dei titoli (`#`, `##`, `###`), elenchi e grassetti.
   - Generazione tabelle compatibili con GitHub Flavored Markdown (`| col1 | col2 |`).
   - De-sillabazione automatica di fine riga (`inter-\n vento` $\rightarrow$ `intervento`).
   - Estrazione immagini incorporate e metadati YAML Frontmatter.
   - Anteprima live formattata e sorgente raw con pulsante *"Copia MD"*.

2. 🗜️ **Comprimi PDF (Intelligent Compressor)**
   - Riduzione del peso dei PDF pesanti fino al 70% preservando la leggibilità.
   - 3 livelli: Leggera (stampa), Bilanciata (web/schermo), Forte (invio email).
   - Calcolo e visualizzazione immediata dello spazio risparmiato.

3. 🧩 **Unisci PDF (Merge)**
   - Combina 2 o più file PDF in un unico documento ordinato con 1 clic.

4. ✂️ **Dividi ed Estrai Pagine (Split)**
   - Estrai intervalli specifici di pagine (es. `1-3, 5, 8-12`) in un nuovo PDF pulito.

5. 🖼️ **PDF ➔ Immagini (High Resolution)**
   - Esporta ogni pagina del PDF come immagine PNG ad alta risoluzione (150 o 300 DPI) racchiusa in uno ZIP.

---

## 🚀 Avvio Locale

### Su macOS (Doppio Click)
Fai doppio click sul file **`start.command`** per avviare il server e aprire l'interfaccia nel browser.

### Da Terminale
```bash
./run.sh
```

### Tramite CLI (Terminale)
```bash
./.venv/bin/python cli.py documento.pdf -o risultato.md --images
```

---

## 🌐 Deploy Cloud Gratuito (Render.com)
Il progetto è configurato per il deploy continuo su Render:
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.server:app --host 0.0.0.0 --port $PORT`
Ad ogni `git push`, Render aggiorna automaticamente la web app online.
