import json
from pathlib import Path
from datetime import datetime

file_path = Path("data/intelligence_snapshot.json")
if not file_path.exists():
    print("Snapshot not found.")
    exit(0)

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total items in snapshot: {len(data)}")

counts = {}
for item in data:
    source = item.get('source', 'Unknown')
    counts[source] = counts.get(source, 0) + 1

print("\nCounts per source:")
max_exceeded = False
for source, count in counts.items():
    print(f"- {source}: {count}")
    if "Altri Orienti" in source or "simopieranni" in source:
         print(f"   -> Title: {item.get('title')}")
         print(f"   -> Summary Start: {item.get('summary')[:50]}...")
         
    if count > 10:
        max_exceeded = True

if max_exceeded:
    print("\n❌ FAILURE: Some sources have more than 10 items.")
else:
    print("\n✅ SUCCESS: All sources have <= 10 items.")
