
import json
import re

def main():
    try:
        with open('discovery_schemas.txt', 'r', encoding='utf-16le', errors='ignore') as f:
            content = f.read()
            
        # Extract JSON part (start with [, end with ])
        # The log has python warnings, then JSON.
        match = re.search(r'(\[.*\])', content, re.DOTALL)
        if match:
            json_str = match.group(1)
            data = json.loads(json_str)
            print(json.dumps(data, indent=2))
        else:
            print("No JSON found in file.")
            print("Raw content snippet:")
            print(content[-500:]) # Show tail
            
    except Exception as e:
        print(f"Error reading schemas: {e}")

if __name__ == "__main__":
    main()
