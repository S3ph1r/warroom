from pypdf import PdfReader
from pathlib import Path
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def deep_scan():
    dir_path = Path(r"g:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
    pdf_files = list(dir_path.glob("*.pdf"))
    
    print(f"Deep Scanning {len(pdf_files)} files for Xiaomi ISIN...")
    
    for pdf in sorted(pdf_files):
        try:
            reader = PdfReader(pdf)
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() + "\n"
            
            if "KYG9830T1067" in full_text or "Xiaomi" in full_text:
                print(f"\n[!!!] HIT in {pdf.name}")
                lines = full_text.split('\n')
                for i, line in enumerate(lines):
                    if "KYG9830T1067" in line or "Xiaomi" in line:
                        # Print context
                        print(f"L{i}: {line.strip()}")
                        # Also look for quantities around it
                        for k in range(max(0, i-5), min(len(lines), i+10)):
                            if k == i: continue
                            l = lines[k].strip()
                            if any(x in l for x in ["STK", "pz.", "Amount", "Acquisto", "Kauf", "Purchase", "Quantity", "Units"]):
                                print(f"  L{k}: {l}")
        except Exception as e:
            pass

if __name__ == "__main__":
    deep_scan()
