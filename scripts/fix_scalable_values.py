
import json

path = "scripts/scalable_holdings.json"

with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

holdings = data.get('holdings', [])
new_holdings = []

print("CORRECTING SCALABLE VALUES (Dividing by Quantity)...")

for h in holdings:
    qty = h.get('quantity', 1.0)
    current_val = h.get('market_value', 0.0)
    
    # Mistral treated text Position Value as Unit Price and multiplied.
    # We reverse this.
    real_val = current_val / qty
    
    # Store corrected
    h['market_value'] = real_val
    h['purchase_price'] = 0.0 # Clear confusion
    
    print(f"{h['name']}: {current_val} -> {real_val}")
    new_holdings.append(h)

data['holdings'] = new_holdings

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print("Done.")
