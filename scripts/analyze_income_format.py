"""
Analyze Income Statement Format
Dump text from Income statement to understand structure.
"""
from pathlib import Path
from pypdf import PdfReader

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
TARGET = "20250506 Income statement Baader Bank pV94w5.pdf"

def analyze_income():
    pdf_path = INBOX / TARGET
    
    print(f"Analyzing: {pdf_path.name}")
    print("=" * 60)
    
    reader = PdfReader(pdf_path)
    
    for i, page in enumerate(reader.pages[:5]):  # First 5 pages
        text = page.extract_text()
        print(f"\n{'='*60}")
        print(f"PAGE {i+1}")
        print('='*60)
        print(text)
        
    # Also search for transaction keywords
    print("\n" + "="*60)
    print("SEARCHING FOR TRANSACTION PATTERNS")
    print("="*60)
    
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"
        
    lines = full_text.split('\n')
    
    # Look for Nvidia
    for i, line in enumerate(lines):
        if "nvidia" in line.lower() or "US67066G1040" in line:
            start = max(0, i-5)
            end = min(len(lines), i+10)
            print(f"\nFound Nvidia at line {i+1}:")
            for k in range(start, end):
                marker = ">>" if k == i else "  "
                print(f"{marker} L{k+1}: {lines[k].strip()}")
            print("-" * 40)
            break  # Just first occurrence

if __name__ == "__main__":
    analyze_income()
