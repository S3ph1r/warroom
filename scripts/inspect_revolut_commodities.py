
import fitz
from pathlib import Path

pdf = Path(r"D:\Download\Revolut\account-statement_2017-12-26_2025-12-26_it-it_3726b9.pdf")

if pdf.exists():
    doc = fitz.open(pdf)
    content = ""
    # Try pages 1, 2, 3 again
    for i in [1, 2, 3]:
        page = doc[i]
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: (b[1], b[0]))
        text = "\n".join([b[4] for b in blocks])
        content += f"\n--- PAGE {i+1} ---\n{text[:2000]}\n"
        
    print(content)
