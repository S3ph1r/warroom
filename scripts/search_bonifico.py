
import pdfplumber

pdf_path = r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf"

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    
    # Search for Bonifico
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if "bonifico" in text.lower() or "deposito" in text.lower() or "trasferimento" in text.lower():
            print(f"\n--- PAGE {i+1} contains DEPOSIT keyword ---")
            # Print context around the keyword
            lines = text.split('\n')
            for j, line in enumerate(lines):
                if any(kw in line.lower() for kw in ['bonifico', 'deposito', 'trasferimento']):
                    # Print 5 lines around it
                    start = max(0, j-2)
                    end = min(len(lines), j+5)
                    print(f"\n[Context around line {j}]:")
                    for k in range(start, end):
                        print(f"  L{k}: {lines[k]}")
