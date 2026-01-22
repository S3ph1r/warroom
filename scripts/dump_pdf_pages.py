import sys
import pypdf

def main(pdf_path, output_txt, num_pages):
    reader = pypdf.PdfReader(pdf_path)
    with open(output_txt, 'w', encoding='utf-8') as f:
        # Extract first N pages
        limit = min(int(num_pages), len(reader.pages))
        for i in range(limit):
            text = reader.pages[i].extract_text()
            f.write(f"--- PAGE {i+1} START ---\n")
            f.write(text)
            f.write(f"\n--- PAGE {i+1} END ---\n\n")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: dump.py <pdf> <out> <pages>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
