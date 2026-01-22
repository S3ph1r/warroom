
import json
from datetime import datetime, timedelta, timezone

DAYS_LOOKBACK = 180
cutoff = datetime.now() - timedelta(days=DAYS_LOOKBACK)
print(f"Cutoff: {cutoff} (Naive local)")

path = "data/warroom_memory.json"
with open(path, 'r') as f:
    all_items = json.load(f)
    
count_source = 0
count_accepted = 0

for item in all_items:
    meta = item.get('metadata', {})
    source = meta.get('source', 'Unknown')
    
    if "Altri Orienti" in source:
        count_source += 1
        pub_date_str = meta.get('published_at')
        if pub_date_str:
            if 'Z' in pub_date_str:
                 pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
            else:
                 pub_date = datetime.fromisoformat(pub_date_str)
                 
            # Logic from main.py
            is_recent = pub_date.replace(tzinfo=None) > cutoff.replace(tzinfo=None)
            
            print(f"Item: {meta.get('title')[:30]} | Date: {pub_date} | Accepted: {is_recent}")
            if is_recent:
                count_accepted += 1
        else:
            print(f"Item: {meta.get('title')} | No date")

print(f"Total Altri Orienti: {count_source}")
print(f"Total Accepted: {count_accepted}")
