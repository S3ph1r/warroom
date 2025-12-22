
import json
from pathlib import Path

path = Path("data/warroom_memory.json")
if not path.exists():
    print("No memory file.")
    exit()
    
with open(path, 'r') as f:
    data = json.load(f)
    
count = 0
for item in data:
    meta = item.get('metadata', {})
    source = meta.get('source', '')
    if "Altri Orienti" in source or "simopieranni" in source:
        print(f"Found: {meta.get('title')} | Date: {meta.get('published_at')} | Source: {source}")
        count += 1
        
print(f"Total found in memory: {count}")
