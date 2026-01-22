
from pathlib import Path

csv_path = Path(r"D:\Download\Binance\2025_05_17_19_26_07.csv")
old_csv = Path(r"D:\Download\Binance\2024_07_08_21_50_39.csv")

def peek(p):
    if p.exists():
        print(f"--- {p.name} ---")
        try:
            with open(p, 'r', encoding='utf-8') as f:
                for i in range(10):
                    print(f.readline().strip())
        except Exception as e:
            print(f"Error: {e}")

peek(csv_path)
peek(old_csv)
