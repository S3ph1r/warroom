"""Analyze all Revolut PDFs"""
import pypdf
from pathlib import Path

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\revolut")

pdfs = [
    "account-statement_2017-12-26_2025-12-26_it-it_3726b9.pdf",
    "account-statement_2022-07-26_2025-12-20_it-it_6b3811.pdf",
    "crypto-account-statement_2022-07-04_2025-12-20_it-it_1c330c.pdf",
    "trading-account-statement_2019-12-28_2025-12-26_it-it_e34cc5.pdf",
    "trading-account-statement_2022-07-04_2025-12-20_it-it_3fb91a.pdf",
    "trading-pnl-statement_2019-12-28_2025-12-20_it-it_d7438d.pdf",
]

for fname in pdfs:
    fpath = INBOX / fname
    print(f"\n{'='*70}")
    print(f"📄 {fname}")
    print('='*70)
    
    try:
        reader = pypdf.PdfReader(fpath)
        num_pages = len(reader.pages)
        print(f"Pages: {num_pages}")
        
        # Extract first page text
        first_page = reader.pages[0].extract_text()
        print(f"\n--- FIRST PAGE (first 800 chars) ---")
        print(first_page[:800])
        
        # Check for holdings/balance keywords
        all_text = " ".join([p.extract_text() for p in reader.pages[:3]])
        keywords = ["saldo", "bilancio", "posizione", "holdings", "portfolio", "valore totale", "quantità disponibile"]
        found = [kw for kw in keywords if kw.lower() in all_text.lower()]
        print(f"\n🔍 Keywords found: {found}")
        
        # Check last page for summary
        last_page = reader.pages[-1].extract_text()
        print(f"\n--- LAST PAGE (first 500 chars) ---")
        print(last_page[:500])
        
    except Exception as e:
        print(f"ERROR: {e}")
