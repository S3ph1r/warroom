
import sys
import os
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
import logging
logging.basicConfig(level=logging.INFO)

from services.analytics_service import get_benchmark_history

def test_benchmark_fetching():
    print("Testing get_benchmark_history()...")
    try:
        data = get_benchmark_history(days=30)
        print(f"Data keys: {list(data.keys())}")
        for k, v in data.items():
            print(f"Benchmark: {k}, Points: {len(v)}")
            if len(v) > 0:
                print(f"  Sample: {v[0]}")
    except Exception as e:
        print(f"TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_benchmark_fetching()
