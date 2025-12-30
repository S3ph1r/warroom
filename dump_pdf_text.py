import pdfplumber

file_path = r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf"
output_txt = "pdf_full_dump.txt"

try:
    with pdfplumber.open(file_path) as pdf:
        with open(output_txt, "w", encoding="utf-8") as f:
            for i, page in enumerate(pdf.pages):
                f.write(f"\n--- PAGE {i+1} ---\n")
                text = page.extract_text()
                if text:
                    f.write(text)
    print(f"Dumped text to {output_txt}")
except Exception as e:
    print(f"Error: {e}")
