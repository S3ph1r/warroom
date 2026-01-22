
import fitz
from pathlib import Path

# Find PnL
files = list(Path(r"D:\Download\Revolut").glob("trading-pnl*.pdf"))
path = files[0]

doc = fitz.open(path)
print(f"--- PAGE 2 TEXT ({path.name}) ---")
print(doc[1].get_text("text")) # text
print("\n--- PAGE 2 BLOCKS ---")
# print(doc[1].get_text("blocks")) # structured
