
import os

try:
    with open('benchmark_results_v2.txt', 'r', encoding='utf-8', errors='ignore') as f:
        print(f.read())
except Exception as e:
    print(f"Error reading file: {e}")
