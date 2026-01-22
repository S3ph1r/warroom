"""Analyze Trade Republic PDF"""
import pypdf
from pathlib import Path

fpath = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\traderepublic\Estratto conto.pdf")

print(f"=== {fpath.name} ===")
reader = pypdf.PdfReader(fpath)
print(f"Pages: {len(reader.pages)}")

# Extract all pages text
for i, page in enumerate(reader.pages):
    text = page.extract_text()
    print(f"\n{'='*60}")
    print(f"PAGE {i+1}")
    print('='*60)
    print(text[:3000] if len(text) > 3000 else text)
    if len(text) > 3000:
        print(f"\n[... {len(text)} chars total, truncated]")
