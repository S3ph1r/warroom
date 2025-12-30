
import sys
filename = sys.argv[1] if len(sys.argv) > 1 else 'ingestion_log_2.txt'
try:
    with open(filename, 'r', encoding='utf-16') as f:
        print(f.read())
except:
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            print(f.read())
    except Exception as e:
        print(f"Error reading {filename}: {e}")
