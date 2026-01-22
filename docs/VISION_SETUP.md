# Trade Republic Vision Analysis Setup

## Obiettivo
Usare un modello Vision (LLaVA) per analizzare visivamente il PDF di Trade Republic e generare regole di parsing accurate che gestiscano correttamente le colonne separate.

## Setup (Prima Esecuzione)

### Step 1: Scaricare il Modello Vision
```bash
.\setup_vision_model.bat
```

Questo scaricherà:
- **LLaVA 13B** (~7GB) - Modello Vision per Ollama
- **Dipendenze Python**: pdf2image, pillow

⏱️ Tempo stimato: 5-10 minuti (dipende dalla connessione)

### Step 2: Installare Poppler (se necessario)
`pdf2image` richiede Poppler per convertire PDF in immagini.

**Windows:**
1. Scarica Poppler: https://github.com/oschwartz10612/poppler-windows/releases
2. Estrai in `C:\Program Files\poppler`
3. Aggiungi `C:\Program Files\poppler\Library\bin` al PATH

**Oppure con Conda:**
```bash
conda install -c conda-forge poppler
```

## Esecuzione Analisi Vision

### Comando
```bash
.\run_tr_vision_analysis.bat
```

### Cosa Fa
1. **Converte PDF → Immagini**: Prime 3 e ultime 2 pagine
2. **Invia a LLaVA**: Chiede al modello Vision di analizzare la struttura tabellare
3. **Genera Regole**: Crea `Estratto conto.vision.rules.json` con regex intelligenti
4. **Testa Parser**: Esegue l'estrazione usando le nuove regole

### Output Atteso
```json
{
  "strategy": "line_stateful",
  "strategy_config": { ... },
  "field_extractors": {
    "type": {
      "regex": "Regex che gestisce 'CommercioBuy' correttamente"
    },
    ...
  },
  "visual_notes": "Descrizione di cosa ha visto il modello"
}
```

## Vantaggi Vision vs Text-Only

| Aspect | Text-Only (pdfplumber) | Vision (LLaVA) |
|--------|----------------------|----------------|
| **Separazione Colonne** | ❌ "CommercioBuy" | ✅ Vede colonne separate |
| **Layout Complessi** | ❌ Fallisce su tabelle annidate | ✅ Capisce struttura visiva |
| **PDF Scansionati** | ❌ Non funziona | ✅ Funziona (con OCR) |
| **Velocità** | ⚡ Istantaneo | 🐢 2-3 minuti |
| **Privacy** | ✅ Locale | ✅ Locale (Ollama WSL) |

## Troubleshooting

### Errore: "LLaVA model not found"
**Soluzione**: Esegui `.\setup_vision_model.bat`

### Errore: "poppler not found"
**Soluzione**: Installa Poppler (vedi Step 2 sopra)

### Errore: "Vision Model timeout"
**Soluzione**: Il modello sta ancora caricando. Riprova dopo 30 secondi.

### Output JSON non valido
**Possibile causa**: Il modello ha restituito testo invece di JSON puro.
**Soluzione**: Verifica i log in `analyze_tr_vision.py`, potrebbe servire refine del prompt.

## Prossimi Passi

Dopo aver eseguito l'analisi Vision:
1. **Controlla** `Estratto conto.vision.rules.json`
2. **Controlla** `Estratto conto.extracted.json`
3. **Verifica** se il campo `type` ora è corretto (non più "UNKNOWN")
4. **Decidi** se questa strategia è da adottare per tutti i broker
