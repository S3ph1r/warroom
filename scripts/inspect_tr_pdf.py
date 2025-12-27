
import fitz
from pathlib import Path

pdf = Path(r"D:\Download\Trade Repubblic\Estratto conto.pdf")

if pdf.exists():
    try:
        doc = fitz.open(pdf)
        print(f"Pages: {len(doc)}")
        text = doc[0].get_text("text")
        print("--- HEADER ---")
        print(text[:500])
        
        if "Trade Republic" in text:
            print("VERDICT: Trade Republic Document")
        elif "Revolut" in text:
            print("VERDICT: Revolut Document (Misplaced?)")
        else:
            print("VERDICT: Unknown Vendor")
            
    except Exception as e:
        print(f"Error: {e}")
else:
    print("File not found")
