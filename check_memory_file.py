import json
from pathlib import Path
import os

print(f"CWD: {os.getcwd()}")
file_path = Path("data/warroom_memory.json")
if not file_path.exists():
    print("Memory file not found.")
else:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"Memory items: {len(data)}")
