# Svelte Setup (WSL Edition) 🐧

Hai un setup ibrido: Backend su Windows, Frontend su WSL. Ottimo!

## 1. Backend (PowerShell su Windows)
Lascia girare questo come stavi già facendo:
```powershell
.\venv\Scripts\python -m uvicorn backend.main:app --host 0.0.0.0 --port 8200 --reload
```

## 2. Frontend (Terminale Ubuntu/WSL)
Apri il tuo terminale WSL, naviga nella cartella del progetto (es. `/mnt/d/...`) ed esegui:

```bash
# Entra nella cartella frontend (il drive D: è montato su /mnt/d)
cd "/mnt/d/Download/Progetto WAR ROOM/warroom/frontend"

# Installa dipendenze
npm install

# Lancia il server di sviluppo (Porta 5200)
npm run dev -- --host
```

## 3. Apri il Browser
Vai su: **http://localhost:5200**

> **Nota Tecnica**: Ho aggiornato il codice per collegarsi direttamente a `localhost:8000` (Windows) dal Browser, bypassando problemi di rete tra WSL e Windows.
