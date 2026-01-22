
import fitz
from pathlib import Path

files = list(Path(r"D:\Download\Revolut").glob("trading-pnl*.pdf"))
path = files[0]

doc = fitz.open(path)
page = doc[1] # Page 2

print(f"--- MARKDOWN TABLE PAGE 2 ({path.name}) ---")
tabs = page.find_tables()
if tabs.tables:
    print(tabs[0].to_markdown())
else:
    print("No tables found.")
