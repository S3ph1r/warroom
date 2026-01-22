
import requests
import json
import time

# Wait for server to be fully ready
time.sleep(5)

URL = "http://localhost:8201/api/council/consult"

def test_council():
    print("🔮 Testing Council Endpoint (Full Pipeline)...")
    
    payload = {
        "query": "Should I sell Bitcoin if it drops below 90k?"
    }
    
    try:
        start = time.time()
        print(f"   Sending request to {URL}...")
        res = requests.post(URL, json=payload)
        elapsed = time.time() - start
        
        if res.status_code == 200:
            data = res.json()
            print(f"✅ Success! Response time: {elapsed:.2f}s")
            
            # Validation
            roles = ['historian', 'strategist', 'quant', 'insider']
            missing = [r for r in roles if r not in data]
            
            if missing:
                print(f"❌ Error: Missing advisors: {missing}")
            else:
                print("✅ All 4 Advisors responded.")
                
            for role, advice in data.items():
                print(f"   - {role.upper()}: {advice.get('verdict')} (Conf: {advice.get('confidence')}%)")
                if 'error' in advice:
                    print(f"     ⚠️ Error: {advice['error']}")
                    
        else:
            print(f"❌ Failed: HTTP {res.status_code}")
            print(res.text)
            
    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    test_council()
