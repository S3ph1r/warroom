
import pdfplumber
import sys

def inspect_pdf(pdf_path):
    print(f"--- Inspecting: {pdf_path} ---")
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Total Pages: {total_pages}")
        
        pages_to_inspect = list(range(0, min(10, total_pages))) # First 10
        if total_pages > 10:
            pages_to_inspect.extend(list(range(max(10, total_pages - 5), total_pages))) # Last 5
            
        seen_lines = set()
        
        for p_idx in pages_to_inspect:
            print(f"\n--- PAGE {p_idx + 1} ---")
            page = pdf.pages[p_idx]
            text = page.extract_text()
            if text:
                lines = text.split('\n')
                # Print just the lines that look like transaction headers (heuristics)
                # or just print everything for now but condensed
                for line in lines:
                    # heuristic: lines starting with Uppercase words that are likely types
                    stripped = line.strip()
                    if len(stripped) < 3: continue
                    
                    # Just print first word to identify types
                    first_word = stripped.split()[0]
                    # Filter common noise
                    if first_word in ["Pagina", "Generata", "Conto", "Periodo", "Valuta", "Totale", "Riporto"]:
                        continue
                        
                    print(line)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_pdf_pages.py <pdf_path>")
        sys.exit(1)
    inspect_pdf(sys.argv[1])
