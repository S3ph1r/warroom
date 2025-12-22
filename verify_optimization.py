
import sys
import os
from pathlib import Path

# Add project root
sys.path.insert(0, r"d:\Download\Progetto WAR ROOM\warroom")

from backend.main import build_intelligence_data, INTELLIGENCE_SNAPSHOT

print("Starting build...")
items = build_intelligence_data()
print(f"Build complete. Items: {len(items)}")

size = os.path.getsize(INTELLIGENCE_SNAPSHOT)
print(f"Snapshot size: {size / 1024 / 1024:.2f} MB")
