"""
Debug script to inspect raw text extraction from documents.
Used to diagnose why LLM parsing failed.
"""
import sys
from pathlib import Path
import fitz  # PyMuPDF
import pandas as pd
from services.llm_ingestion_service import extract_content_smart

def extract_debug(file_path):
    path = Path(file_path)
    print(f"--- DEBUGGING: {path.name} ---")
    
    if path.suffix.lower() == '.pdf':
        try:
            doc = fitz.open(path)
            text = ""
            for i, page in enumerate(doc):
                page_text = page.get_text("text") # Try 'text' layout
                print(f"\n[PAGE {i+1} START]")
                print(page_text[:500] + "..." if len(page_text) > 500 else page_text)
                text += page_text
            print(f"\nTotal Text Length: {len(text)}")
        except Exception as e:
            print(f"PDF Error: {e}")

    elif path.suffix.lower() == '.csv':
        try:
            df = pd.read_csv(path, sep=None, engine='python') # Auto detect sep
            print(f"Columns: {list(df.columns)}")
            print("\nFirst 5 rows:")
            print(df.head().to_string())
            
            # Check what string format looks like
            csv_string = df.to_string(index=False)
            print(f"\nString Representation (First 500 chars):")
            print(csv_string[:500])
        except Exception as e:
            print(f"CSV Error: {e}")

def debug_smart(file_path):
    path = Path(file_path)
    print(f"--- SMART DEBUG: {path.name} ---")
    try:
        content = extract_content_smart(path)
        print(f"Content Length: {len(content)}")
        print("First 1000 chars:")
        print(content[:1000])
        print("\nLast 500 chars:")
        print(content[-500:])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    files = [
        r"D:\Download\BGSAXO\Posizioni_19-dic-2025_17_49_12.csv",
        r"D:\Download\BGSAXO\Transactions_19807401_2025-01-01_2025-12-19.pdf",
    ]
    
    for f in files:
        debug_smart(f)
