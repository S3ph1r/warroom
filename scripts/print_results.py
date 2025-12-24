
try:
    with open('results.txt', 'r', encoding='utf-8') as f:
        print(f.read())
except Exception as e:
    print(f"Read Error: {e}")
