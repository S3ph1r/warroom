
import pdfplumber

pdf_path = r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf"

with open('search_results.txt', 'w', encoding='utf-8') as out:
    with pdfplumber.open(pdf_path) as pdf:
        out.write(f"Total pages: {len(pdf.pages)}\n")
        
        # Search for Deposito
        found = False
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if "deposito" in text.lower():
                found = True
                out.write(f"\n--- PAGE {i+1} contains 'Deposito' ---\n")
                lines = text.split('\n')
                for j, line in enumerate(lines):
                    if "deposito" in line.lower():
                        start = max(0, j-3)
                        end = min(len(lines), j+8)
                        out.write(f"\n[Context around line {j}]:\n")
                        for k in range(start, end):
                            out.write(f"  L{k}: {lines[k]}\n")
        
        if not found:
            out.write("\nNo 'Deposito' keyword found in PDF.\n")

print("Results written to search_results.txt")
