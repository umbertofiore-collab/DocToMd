#!/usr/bin/env bash
# ==========================================================
# DocToMD - Launcher per macOS / Linux
# Avvia l'applicazione locale e apre il browser
# ==========================================================

cd "$(dirname "$0")"

echo "=================================================="
echo "    🚀 Avvio DocToMD (PDF to Markdown Converter)   "
echo "=================================================="

# Verifica ambiente virtuale
if [ ! -d ".venv" ]; then
    echo "📦 Creazione ambiente virtuale .venv..."
    python3 -m venv .venv
fi

# Verifica dipendenze
if [ ! -f ".venv/bin/uvicorn" ]; then
    echo "📥 Installazione dipendenze richieste..."
    ./.venv/bin/pip install -r requirements.txt
fi

echo "🌐 Apertura interfaccia Web nel browser..."
(sleep 1.2 && open "http://localhost:8000" 2>/dev/null || xdg-open "http://localhost:8000" 2>/dev/null || true) &

echo "⚡ Server in ascolto su http://localhost:8000"
echo "👉 Premi CTRL+C per fermare il server."
echo ""

./.venv/bin/uvicorn app.server:app --host 127.0.0.1 --port 8000 --reload
