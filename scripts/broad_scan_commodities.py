
import fitz
from pathlib import Path

pdf = Path(r"D:\Download\Revolut\account-statement_2017-12-26_2025-12-26_it-it_3726b9.pdf")

if pdf.exists():
    doc = fitz.open(pdf)
    for i, page in enumerate(doc):
        text = page.get_text("text")
        if "XAU" in text or "XAG" in text:
            print(f"--- HIT PAGE {i+1} ---")
            
            # Print blocks containing XAU/XAG
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: (b[1], b[0]))
            
            for b_idx, b in enumerate(blocks):
                b_text = b[4]
                if "XAU" in b_text or "XAG" in b_text:
                    print(f"BLOCK {b_idx}: {b_text.strip()}")
                    # Print next block (might contain balance)
                    if b_idx + 1 < len(blocks):
                        print(f"  NEXT: {blocks[b_idx+1][4].strip()}")
                        
            # Check for generic "Saldo" on the page
            print("  PAGE CONTENT SNIPPET:")
            clean = "\n".join([b[4] for b in blocks])
            print(clean[:500])
