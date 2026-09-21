# DocToMD - Convertitore PDF in Markdown Ultra-Veloce

Applicazione moderna, veloce e completa per convertire documenti PDF in Markdown pulito e strutturato, ottimizzata per leggibilità umana, Obsidian/Notion e pipeline AI/RAG.

Sviluppata con **PyMuPDF4LLM**, **FastAPI** e **Tailwind CSS**.

---

## ⚡ Caratteristiche Principali

- 🚀 **Velocità Istantanea**: Oltre 100-200 pagine al secondo su CPU standard, senza necessità di GPU o librerie pesanti.
- 📊 **Tabelle Markdown Perfette**: Ricostruisce le griglie di celle e le converte in tabelle compatibili con GitHub Flavored Markdown (`| Colonna | Valore |`).
- 🏷️ **Gerarchia Titoli Intelligente**: Mappatura automatica dei font per rilevare `# H1`, `## H2`, `### H3`.
- 🖼️ **Estrazione Immagini**: Salva tutte le immagini incorporate e le collega automaticamente nel Markdown, fornendo un archivio ZIP pronto all'uso.
- 🧹 **Post-Processing Intelligente**:
  - Rimozione automatica delle sillabazioni di fine riga (De-hyphenation: `inter- \n vento` $\rightarrow$ `intervento`).
  - Normalizzazione delle righe vuote e pulizia degli spazi.
- 📑 **Metadati YAML (Frontmatter)**: Inclusione opzionale di titolo, autore, conteggio pagine e data.
- 🔍 **Rilevamento Scansioni (OCR Alert)**: Notifica automatica se il PDF è un'immagine/fotocopia con poco o nessun testo vettoriale.
- 💻 **Doppia Interfaccia**:
  - **Web UI Moderna**: Drag & Drop, batch upload, anteprima affiancata (HTML formattato vs Raw Markdown), copia con un clic.
  - **CLI per Terminale**: Conversione di singoli file o intere cartelle con un solo comando.

---

## 🚀 Avvio Rapido

### Metodo 1: Doppio click su macOS
Fai doppio click sul file **`start.command`** presente nella cartella per avviare il server e aprire automaticamente il browser su `http://localhost:8000`.

### Metodo 2: Da Terminale
```bash
./run.sh
```

---

## 🖥️ Utilizzo da Riga di Comando (CLI)

Puoi usare la CLI per convertire singoli file o elaborare intere directory:

```bash
# Attiva l'ambiente virtuale
source .venv/bin/activate

# 1. Converti un singolo file PDF
python cli.py documento.pdf

# 2. Converti ed estrai anche le immagini incorporate
python cli.py documento.pdf -o mio_output.md --images

# 3. Converti un'intera cartella di file PDF
python cli.py ./cartella_pdf/ -o ./output_md/

# 4. Aggiungi separatori visivi per ogni pagina
python cli.py documento.pdf --separators
```

---

## 💡 Dritte e Best Practice per Risultati Perfetti

Consulta la guida approfondita inclusa nel progetto:
👉 [GUIDA_E_DRITTE.md](./GUIDA_E_DRITTE.md)

Troverai le soluzioni e i consigli pratici su:
1. Come gestire PDF scansionati vs PDF nativi.
2. Perché la de-sillabazione è cruciale per i sistemi RAG ed embedding.
3. Come escludere header e numeri di pagina ripetuti.
4. Come trattare formule matematiche complesse (LaTeX) e layout multi-colonna.
5. Confronto prestazionale e di costi rispetto a Vision LLM e OCR tradizionali.

---

## 🛠️ Struttura del Progetto

```
pdf to mark down/
├── app/
│   ├── converter.py       # Motore di conversione ed elaborazione del testo
│   ├── server.py          # Server FastAPI con endpoint singoli, batch e download
│   └── templates/
│       └── index.html     # Interfaccia Web reattiva e moderna
├── cli.py                 # Strumento da riga di comando (CLI)
├── GUIDA_E_DRITTE.md      # Guida tecnica e consigli pratici
├── requirements.txt       # Dipendenze Python
├── run.sh                 # Script di avvio per macOS / Linux
├── start.command          # Launcher con doppio click per macOS
└── README.md              # Questo file
```

---

## 🔒 Privacy & Sicurezza
Tutta l'elaborazione avviene al **100% in locale** sul tuo computer. Nessun dato, documento o immagine viene trasmesso a server cloud di terze parti.
