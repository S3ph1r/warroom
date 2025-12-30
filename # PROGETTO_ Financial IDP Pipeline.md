\# PROGETTO: Financial IDP Pipeline \- Documentazione Tecnica (Parte 1 di 3\)

\#\# 1\. Executive Summary & Constraints  
Il sistema è un'architettura \*\*Event-Driven\*\* progettata per processare flussi di documenti finanziari provenienti da diverse fonti (Brokers) su Google Drive.  
L'obiettivo è trasformare documenti non strutturati (PDF) o semi-strutturati (CSV, Excel) in dati strutturati SQL, minimizzando i costi di inferenza LLM tramite la generazione dinamica di codice (Code Generation Strategy).

\*\*Vincoli Operativi Rigidi:\*\*  
\*   \*\*Input ammessi:\*\* PDF (Text-based), CSV, Excel (limitato all'1% dei casi).  
\*   \*\*Input vietati:\*\* Immagini, Word, Zip, PDF scansionati (immagini pure), file di sistema. Vanno scartati immediatamente.  
\*   \*\*Identificazione Broker:\*\* Il nome del broker è determinato univocamente dalla sottocartella di provenienza (es. \`/Inbox/Saxo/\` \-\> Broker: \`Saxo\`).  
\*   \*\*LLM:\*\* Utilizzo di modelli locali (classe 14B per logica complessa, 3B/7B per routing veloce) via server API compatibile OpenAI (Ollama/vLLM).

\---

\#\# 2\. Stack Tecnologico di Riferimento

\*   \*\*Runtime:\*\* Python 3.11+  
\*   \*\*LLM Inference Server:\*\* Ollama (o vLLM) esposto su porta locale.  
    \*   \*Small Model:\* \`Qwen-2.5-7B-Instruct\` (o Llama-3.2-3B) per classificazione rapida.  
    \*   \*Big Model:\* \`Qwen-2.5-14B-Coder\` (o equivalente specializzato in coding) per la scrittura dei parser.  
\*   \*\*Document Parsing:\*\*  
    \*   \*\*PDF:\*\* \`Docling\` (IBM) o \`PyMuPDF\` (fitz). \*Nota: Docling è preferito per la capacità di convertire layout complessi in Markdown.\*  
    \*   \*\*CSV/Excel:\*\* \`Pandas\`.  
\*   \*\*Validation:\*\* \`Pydantic\` (fondamentale per garantire output strutturati).  
\*   \*\*Database:\*\* PostgreSQL (consigliato) o SQLite (per MVP).

\---

\#\# 3\. Modulo A: Ingestione e Filtro (The Gatekeeper)

Questo modulo agisce da "firewall" per i file. Non deve usare l'AI, ma logica deterministica veloce.

\#\#\# Workflow Logico  
1\.  \*\*Event Trigger:\*\* Polling sulla cartella GDrive o Webhook.  
2\.  \*\*Path Parsing:\*\* Dato il percorso \`/Inbox/{Broker\_Name}/{Filename}.{Ext}\`, estrarre \`Broker\_Name\`.  
3\.  \*\*Extension Whitelist Check:\*\*  
    \*   Se estensione in \`\[.csv, .pdf, .xls, .xlsx\]\`: \*\*PROCEDI\*\*.  
    \*   Altro: \*\*SCARTA\*\* (Sposta in \`/Discarded/Unsupported\_Format\`).

\#\#\# Specifica per Antigravity (Python Snippet Logic)  
Il sistema deve leggere l'header del file (Magic Numbers) per confermare il tipo, non fidarsi solo dell'estensione.

\`\`\`python  
import magic \# python-magic library

ALLOWED\_MIMETYPES \= \[  
    'application/pdf',  
    'text/csv',  
    'text/plain', \# Spesso i CSV sono visti come text/plain  
    'application/vnd.ms-excel',  
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'  
\]

def ingest\_file(file\_path):  
    mime \= magic.from\_file(file\_path, mime=True)  
    if mime not in ALLOWED\_MIMETYPES:  
        move\_to\_trash(file\_path, reason="Invalid Format")  
        return None  
    \# Procedi al Modulo B  
\`\`\`

\---

\#\# 4\. Modulo B: Router e Classificazione (The Router)

Una volta accettato il file, dobbiamo capire \*cosa\* contiene senza leggerlo tutto.

\#\#\# Strategia di Pre-processing (Low-Cost)  
Non passiamo l'intero file all'LLM.  
\*   \*\*Se CSV/Excel:\*\* Carica le prime \*\*30 righe\*\* come testo stringa (inclusi header).  
\*   \*\*Se PDF:\*\* Converti solo la \*\*Pagina 1 e 2\*\* in Markdown. Se il PDF ha una sola pagina, usa solo quella.

\#\#\# Prompt di Classificazione (Modello 7B)  
Il prompt deve restituire un JSON stretto.

\*\*System Prompt:\*\*  
\> "Sei un assistente automatico di back-office finanziario. Il tuo compito è classificare il documento in base al testo fornito.  
\> Le categorie possibili sono ESCLUSIVAMENTE:  
\> 1\. \`HOLDINGS\`: Il documento è un report statico di portafoglio (elenco titoli posseduti in una data). Parole chiave tipiche: 'Posizioni', 'Quantità', 'Valore Mercato', 'Asset Allocation'.  
\> 2\. \`TRANSACTIONS\`: Il documento è un registro cronologico di movimenti (acquisti, vendite, cedole). Parole chiave tipiche: 'Data', 'Time', 'Buy', 'Sell', 'Commissione', 'Tax'.  
\> 3\. \`TRASH\`: Il documento non contiene dati utili (es. informative legali, copertine vuote, o layout illeggibile).  
\>  
\> Rispondi SOLO con questo JSON: \`{\\"category\\": \\"...\\", \\"confidence\\": 0.0-1.0}\`"

\*\*Gestione Output:\*\*  
\*   Se \`category \== "TRASH"\` o \`confidence \< 0.8\`: Sposta in \`/Discarded/Low\_Confidence\`.  
\*   Altrimenti: Passa il file e la categoria rilevata al \*\*Modulo C\*\* (Estrazione).

\---

\# PROGETTO: Financial IDP Pipeline \- Documentazione Tecnica (Parte 2 di 3\)

\#\# 5\. Modulo C: The Extraction Engine (Logic Generator)

Questo modulo non estrae i dati "a mano". \*\*Scrive programmi su misura\*\* per estrarli.  
Il sistema mantiene un \*\*Registro dei Parser (Parser Registry)\*\*: un database o un file JSON che mappa \`Broker\` \+ \`Category\` \+ \`LayoutFingerprint\` $\\to$ \`Script Python\`.

\#\#\# Flusso Operativo (Flowchart Logico)

1\.  \*\*Check Registry:\*\* Il sistema calcola un \*fingerprint\* del layout (es. hash dell'header del CSV o delle prime 10 righe del Markdown PDF).  
    \*   Esiste già uno script associato a questo fingerprint per questo Broker?  
    \*   \*\*SI:\*\* Carica lo script ed eseguilo (Tempo: ms).  
    \*   \*\*NO:\*\* Attiva la pipeline \*\*Generator\*\* (Tempo: \~30-60s una tantum).

\---

\#\# 6\. Pipeline Generator: Gestione CSV/Excel "Sporchi"  
\*\*Obiettivo:\*\* Creare uno script Pandas robusto che scarti righe di riepilogo, totali e intestazioni ripetute, estraendo solo i dati atomici.

\#\#\# Input per l'LLM (14B Coder)  
\*   \*\*Sample Data:\*\* Le prime 50 righe del file (raw string).  
\*   \*\*Target Schema:\*\* Elenco dei campi richiesti (\`isin\`, \`ticker\`, \`quantity\`, \`currency\`, etc.).

\#\#\# Prompt Template (Python Generation)  
\> "Agisci come Senior Data Engineer.  
\> Ho un dataset 'sporco' (vedi input sotto) proveniente da un broker. Contiene righe di intestazione, righe di riepilogo (es. 'Azioni (48)') e totali che devono essere scartati.  
\>  
\> \*\*Task:\*\* Scrivi una funzione Python \`def parse\_csv(file\_path):\` che usa \`pandas\` per:  
\> 1\. Caricare il file (gestisci encoding e separatori , o ;).  
\> 2\. \*\*Filtering Logic:\*\* Applica un filtro booleano per tenere SOLO le righe che rappresentano singoli asset/transazioni. (Suggerimento: Spesso le righe valide hanno un ISIN o una Quantità numerica, mentre i riepiloghi hanno questi campi vuoti o nulli).  
\> 3\. \*\*Mapping:\*\* Rinomina le colonne originali nei nomi del mio Target Schema.  
\> 4\. \*\*Cleaning:\*\* Pulisci i campi numerici (es. rimuovi 'EUR', trasforma '1.000,00' in float 1000.0).  
\>  
\> Restituisci SOLO il blocco di codice Python."

\#\#\# Esecuzione e Validazione  
Il codice generato viene eseguito in una sandbox controllata.  
\*   \*\*Successo:\*\* Se il DataFrame risultante non è vuoto e rispetta i tipi di dato, lo script viene salvato nel Registry.  
\*   \*\*Fallimento:\*\* L'errore (traceback) viene rimandato all'LLM per una correzione ("Self-Correction Loop").

\---

\#\# 7\. Pipeline Generator: Gestione PDF Complessi  
\*\*Obiettivo:\*\* Trasformare un PDF multipagina (es. 83 pagine) in dati strutturati senza usare l'LLM su ogni pagina.

\#\#\# Tooling: Docling (Key Component)  
Utilizzare la libreria \`Docling\` per convertire il PDF in \*\*Markdown\*\*.  
\*   \*Perché?\* Il Markdown preserva la gerarchia visiva (Intestazioni Date \> Tabelle Transazioni) che si perde col semplice testo.

\#\#\# Strategia "Stateful Parsing"  
Poiché nei PDF finanziari (come l'esempio Saxo) la data appare spesso una sola volta come intestazione di gruppo, lo script generato deve mantenere uno "stato".

\#\#\# Input per l'LLM (14B Coder)  
\*   \*\*Sample Markdown:\*\* Markdown generato dalle pagine 2 e 3 (dove la struttura è stabile).  
\*   \*\*Target Schema:\*\* JSON Schema delle transazioni.

\#\#\# Prompt Template (Regex/Logic Generation)  
\> "Sto analizzando un estratto conto convertito in Markdown.  
\> \*\*Struttura del documento:\*\* Le transazioni sono raggruppate per data. La data appare come intestazione (es. '\#\#\# 19-dic-2025'). Sotto la data seguono blocchi di testo per le singole operazioni.  
\>  
\> \*\*Task:\*\* Scrivi uno script Python che prenda in input l'intera stringa Markdown e:  
\> 1\. Iteri riga per riga (o usi Regex multiline).  
\> 2\. Mantenga una variabile \`current\_date\` quando incontra una data.  
\> 3\. Estragga i blocchi di transazione associandoli alla \`current\_date\`.  
\> 4\. Gestisca il fatto che una transazione può essere su più righe (es. Riga 1: Titolo/Prezzo, Riga 2: Commissioni). Se trovi 'Commissione', agganciala alla transazione precedente.  
\>  
\> L'output deve essere una lista di dizionari."

\---

\#\# 8\. Modulo D: Data Normalization & Loading

Una volta che lo script (CSV o PDF) ha prodotto una lista di dizionari "grezzi", entra in gioco la normalizzazione deterministica (Python puro).

1\.  \*\*Date Parsing:\*\* Tutto viene convertito in \`YYYY-MM-DD\`.  
2\.  \*\*Number Parsing:\*\* Gestione locale (1.000,00 vs 1,000.00) basata sulla valuta o impostazioni broker.  
3\.  \*\*ISIN Validation:\*\* Controllo regex (2 lettere \+ 10 alfanumerici).  
4\.  \*\*Upsert SQL:\*\*  
    \*   \*Holdings:\* \`DELETE FROM holdings WHERE broker\_id \= 'Saxo' AND snapshot\_date \= '2025-12-19'; INSERT ...\` (Le posizioni sono snapshot, si sovrascrivono per quella data).  
    \*   \*Transactions:\* \`INSERT INTO transactions ... ON CONFLICT (broker\_id, isin, transaction\_date, quantity, price) DO NOTHING\`. (Evitare duplicati se il file viene ricaricato).

\---

\#\# 9\. Fallback Strategy (Robustezza)

Cosa succede se il layout cambia drasticamente a pagina 40 di 83?

Il sistema implementa un \*\*Hybrid Loop\*\*:  
1\.  Il parser Python generato gira su tutte le pagine.  
2\.  Se incontra un errore o estrae 0 dati da una pagina specifica che contiene testo, il sistema isola quella pagina.  
3\.  \*\*Emergency Call:\*\* Quella singola pagina viene mandata all'LLM con un prompt di estrazione diretta (non generazione codice): \*"Estrai i dati da questo frammento di testo in JSON"\*.  
4\.  I dati estratti manualmente vengono uniti a quelli estratti dallo script.  
5\.  Il sistema notifica: "Attenzione: Parser instabile per Broker X".

\---

\# PROGETTO: Financial IDP Pipeline \- Documentazione Tecnica (Parte 3 di 3\)

\#\# 10\. Database Schema (SQL Implementation)

Si raccomanda l'uso di \*\*PostgreSQL\*\* per la robustezza dei tipi di dato (\`DECIMAL\` per la valuta è critico).

\`\`\`sql  
\-- Tabella: HOLDINGS (Istantanee di portafoglio)  
CREATE TABLE holdings (  
    id SERIAL PRIMARY KEY,  
    broker\_id VARCHAR(50) NOT NULL,       \-- Es. 'Saxo', 'Fineco'  
    snapshot\_date DATE NOT NULL,          \-- Data del report  
    isin VARCHAR(20),                     \-- Identificativo univoco  
    ticker VARCHAR(20),                   \-- Simbolo (se ISIN assente)  
    description VARCHAR(255),             \-- Nome strumento  
    quantity NUMERIC(18, 6\) NOT NULL,     \-- Supporto per frazionarie  
    currency VARCHAR(3) NOT NULL,         \-- EUR, USD, etc.  
    market\_value NUMERIC(18, 2),          \-- Valore nella valuta originale  
    market\_value\_eur NUMERIC(18, 2),      \-- Valore convertito (opzionale)  
    asset\_category VARCHAR(50),           \-- Azione, ETF, Bond (opzionale)  
      
    created\_at TIMESTAMP DEFAULT CURRENT\_TIMESTAMP,  
      
    \-- Vincolo: Per un dato broker e data, un ISIN può apparire una sola volta  
    CONSTRAINT uq\_holdings\_snapshot UNIQUE (broker\_id, snapshot\_date, isin)  
);

\-- Tabella: TRANSACTIONS (Storico movimenti)  
CREATE TABLE transactions (  
    id SERIAL PRIMARY KEY,  
    broker\_id VARCHAR(50) NOT NULL,  
    transaction\_date DATE NOT NULL,  
    operation\_type VARCHAR(20) NOT NULL,  \-- BUY, SELL, DIVIDEND, FEE...  
      
    isin VARCHAR(20),  
    ticker VARCHAR(20),  
    description VARCHAR(255),  
      
    quantity NUMERIC(18, 6),              \-- Positivo/Negativo  
    price\_unit NUMERIC(18, 6),            \-- Prezzo unitario  
    total\_amount NUMERIC(18, 2\) NOT NULL, \-- Totale transato  
    currency VARCHAR(3) NOT NULL,  
      
    fees NUMERIC(18, 2\) DEFAULT 0,        \-- Commissioni esplicite  
    exchange\_rate NUMERIC(18, 6),         \-- Tasso cambio se presente  
      
    source\_file VARCHAR(255),             \-- Nome file origine (per audit)  
    raw\_json JSONB,                       \-- Dati grezzi estratti (per debug)  
      
    created\_at TIMESTAMP DEFAULT CURRENT\_TIMESTAMP,

    \-- Vincolo: Evitare duplicati se si ricarica lo stesso file  
    CONSTRAINT uq\_transaction\_entry UNIQUE (broker\_id, transaction\_date, isin, operation\_type, total\_amount)  
);  
\`\`\`

\---

\#\# 11\. Monitoring & Observability

Poiché il sistema deve girare "da solo", il logging è fondamentale.

1\.  \*\*File Log Structure:\*\*  
    \*   \`/Processed/{Broker}/{Year}/{Month}/\` \-\> Dove finiscono i file completati con successo.  
    \*   \`/Discarded/{Reason}/\` \-\> Dove finiscono i file scartati (Reason: \`Trash\`, \`Error\`, \`LowConfidence\`).  
2\.  \*\*Audit Log (Tabella SQL \`system\_logs\`):\*\*  
    \*   Registra ogni evento: \`FileIn\`, \`Classification\`, \`ParserUsed\` (Cached o Generated), \`RowsInserted\`, \`ErrorTrace\`.  
3\.  \*\*Alerting:\*\*  
    \*   Se \`ErrorRate \> 10%\` nell'ultima ora \-\> Email all'admin.  
    \*   Se \`ParserGenerationFailed\` \-\> Alert critico (il layout del broker è cambiato e l'LLM non riesce a gestirlo).

\---

\#\# 12\. "The Router" \- Code Snippet per Sviluppatori

Questo è lo scheletro Python che Antigravity può usare come base. Implementa la logica di \*\*Ingestione\*\* e \*\*Classificazione\*\* discussa nella Parte 1\.

\`\`\`python  
import os  
import shutil  
import json  
from openai import OpenAI  
from pydantic import BaseModel, Field  
from typing import Literal

\# \--- CONFIGURAZIONE \---  
INPUT\_FOLDER \= "./Inbox"  
PROCESSED\_FOLDER \= "./Processed"  
DISCARDED\_FOLDER \= "./Discarded"

\# Client puntato su Server Locale (Ollama/vLLM)  
client \= OpenAI(base\_url="http://localhost:11434/v1", api\_key="ollama")

\# \--- SCHEMI DI OUTPUT (Structured Outputs) \---  
class DocumentClassification(BaseModel):  
    category: Literal\["HOLDINGS", "TRANSACTIONS", "TRASH"\] \= Field(  
        ..., description="La categoria del documento finanziario."  
    )  
    confidence: float \= Field(..., description="Livello di confidenza da 0.0 a 1.0")  
    reasoning: str \= Field(..., description="Breve motivo della classificazione")

\# \--- FUNZIONI CORE \---

def get\_broker\_from\_path(file\_path: str) \-\> str:  
    """Estrae il nome broker dalla struttura cartelle: ./Inbox/Saxo/Report.pdf \-\> Saxo"""  
    path\_parts \= os.path.normpath(file\_path).split(os.sep)  
    try:  
        \# Assumendo struttura ./Inbox/{Broker}/{File}  
        return path\_parts\[-2\]   
    except IndexError:  
        return "Unknown"

def extract\_preview\_text(file\_path: str) \-\> str:  
    """  
    Estrae testo grezzo dalle prime pagine/righe.  
    Qui andrebbe integrato 'Docling' per PDF e 'Pandas' per CSV.  
    """  
    ext \= os.path.splitext(file\_path)\[1\].lower()  
      
    if ext \== '.csv':  
        \# Logica placeholder per CSV  
        with open(file\_path, 'r', encoding='utf-8', errors='ignore') as f:  
            return "".join(\[next(f) for \_ in range(30)\])  
              
    elif ext \== '.pdf':  
        \# Logica placeholder per PDF (Docling/PyMuPDF)  
        return "\[DOCLING\_MARKDOWN\_PREVIEW\_OF\_PAGE\_1\_AND\_2\]"  
      
    return ""

def classify\_document(text\_preview: str) \-\> DocumentClassification:  
    """Chiama l'LLM Locale (es. Qwen-2.5-7B) per classificare"""  
      
    response \= client.beta.chat.completions.parse(  
        model="qwen2.5-7b-instruct",  
        messages=\[  
            {"role": "system", "content": "Sei un analista back-office. Classifica il documento."},  
            {"role": "user", "content": f"Testo documento:\\n{text\_preview}"}  
        \],  
        response\_format=DocumentClassification,  
    )  
    return response.choices\[0\].message.parsed

\# \--- ORCHESTRATOR LOOP \---

def process\_inbox():  
    for root, dirs, files in os.walk(INPUT\_FOLDER):  
        for file in files:  
            file\_path \= os.path.join(root, file)  
            broker \= get\_broker\_from\_path(file\_path)  
              
            \# 1\. Filtro Estensione (Hard Check)  
            if not file.lower().endswith(('.csv', '.pdf', '.xls', '.xlsx')):  
                shutil.move(file\_path, os.path.join(DISCARDED\_FOLDER, "InvalidFormat", file))  
                continue

            print(f"Processing {file} from Broker: {broker}...")  
              
            \# 2\. Estrazione Anteprima  
            preview\_text \= extract\_preview\_text(file\_path)  
              
            \# 3\. Classificazione AI  
            result \= classify\_document(preview\_text)  
            print(f"-\> Classificato come: {result.category} ({result.confidence})")  
              
            if result.category \== "TRASH" or result.confidence \< 0.8:  
                shutil.move(file\_path, os.path.join(DISCARDED\_FOLDER, "Trash", file))  
                continue  
                  
            \# 4\. Routing all'Estrazione (Parte 2 del progetto)  
            if result.category \== "HOLDINGS":  
                \# run\_holdings\_pipeline(file\_path, broker)  
                pass  
            elif result.category \== "TRANSACTIONS":  
                \# run\_transactions\_pipeline(file\_path, broker)  
                pass

            \# 5\. Spostamento a Processed  
            shutil.move(file\_path, os.path.join(PROCESSED\_FOLDER, broker, file))

if \_\_name\_\_ \== "\_\_main\_\_":  
    process\_inbox()  
\`\`\`

\---

\#\# 13\. Conclusione del Progetto

Questa architettura risolve le tre sfide principali:

1\.  \*\*Eterogeneità:\*\* Grazie al "Router" (LLM 7B), non importa se il file è CSV o PDF, viene indirizzato alla pipeline giusta.  
2\.  \*\*Scalabilità (Nuovi Broker):\*\* Grazie al "Logic Generator" (LLM 14B Coder), l'aggiunta di un nuovo broker non richiede sviluppo manuale, ma solo 1 minuto di generazione automatica dello script di parsing.  
3\.  \*\*Costi ed Efficienza:\*\* Non usiamo l'LLM per leggere \*ogni\* riga di \*ogni\* file. Lo usiamo solo per \*\*classificare\*\* (veloce) e \*\*scrivere il codice\*\* (una tantum). Il parsing massivo è fatto da Python/Pandas, rendendo il sistema estremamente performante anche con migliaia di documenti.

Il progetto è pronto per la fase di sviluppo.

