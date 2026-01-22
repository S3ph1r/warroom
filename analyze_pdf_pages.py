import pdfplumber
import sys

file_path = r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf"

try:
    with pdfplumber.open(file_path) as pdf:
        num_pages = len(pdf.pages)
        print(f"Total Pages: {num_pages}")
        
        # Page 2 (Index 1)
        if num_pages > 1:
            print("\n--- PAGE 2 CONTENT ---")
            print(pdf.pages[1].extract_text())
        else:
            print("PDF has only 1 page.")

        # Last Page
        if num_pages > 0:
            print("\n--- LAST PAGE CONTENT ---")
            print(pdf.pages[-1].extract_text())

except Exception as e:
    print(f"Error: {e}")
