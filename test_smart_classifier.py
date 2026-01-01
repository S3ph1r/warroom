"""Test script for Smart Classifier on Revolut files."""
import sys
sys.path.insert(0, '.')
from pathlib import Path
from scripts.smart_classifier import classify_document
import json

files = [
    r'g:\Il mio Drive\WAR_ROOM_DATA\inbox\revolut\crypto-account-statement_2022-07-04_2025-12-31_it-it_87d838.xlsx',
    r'g:\Il mio Drive\WAR_ROOM_DATA\inbox\revolut\trading-account-statement_2019-12-28_2025-12-31_it-it_28f506.xlsx',
    r'g:\Il mio Drive\WAR_ROOM_DATA\inbox\revolut\account-statement_2022-07-26_2025-12-31_it-it_43269b.xlsx',
]

for f in files:
    print('\n' + '='*60)
    print(f'FILE: {Path(f).name}')
    print('='*60)
    result = classify_document(f)
    
    # Show key fields
    print(f"document_type: {result.get('document_type')}")
    print(f"should_process: {result.get('should_process')}")
    print(f"asset_type: {result.get('asset_type')}")
    print(f"contains_transactions: {result.get('contains_transactions')}")
    print(f"reason: {result.get('reason')}")
    print(f"column_mapping:")
    if result.get('column_mapping'):
        for k, v in result.get('column_mapping').items():
            if v:
                print(f"  {k}: {v}")
