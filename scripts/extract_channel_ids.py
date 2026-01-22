"""
Extract Channel IDs from Video URLs
"""
import requests
import re

def get_channel_id(video_url):
    print(f"Fetching {video_url}...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        resp = requests.get(video_url, headers=headers, timeout=10)
        
        # Regex for channelId
        match = re.search(r'"channelId":"(UC[\w-]+)"', resp.text)
        if match:
            return match.group(1)
            
        # Fallback: itemprop="channelId"
        match = re.search(r'itemprop="channelId" content="(UC[\w-]+)"', resp.text)
        if match:
            return match.group(1)
            
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    videos = [
        ("Marco Casario", "https://youtu.be/aJPkdAECDyQ?si=WbSLJNWtRZ1970n-"),
        ("Blackbox Stocks", "https://youtu.be/9z3CXu_BFMg?si=KYwmQNgSQMQYEu22"),
        ("Altri Orienti", "https://youtu.be/XtdOGZMa69E?si=dCCu_ap4b0-ii7Gp")
    ]
    
    print("--- Extracting Channel IDs ---")
    for name, url in videos:
        cid = get_channel_id(url)
        if cid:
            print(f"✅ {name}: {cid}")
        else:
            print(f"❌ {name}: Failed to extract")

if __name__ == "__main__":
    main()
