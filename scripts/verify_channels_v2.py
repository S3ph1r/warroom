"""
Verify Channels V2 - Strict Mode
"""
import requests
import re

def check_id_identity(cid):
    url = f"https://www.youtube.com/channel/{cid}"
    print(f"🕵️ Identity Check: {url}")
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        # Title of the page
        title_match = re.search(r'<title>(.*?)</title>', resp.text)
        if title_match:
            print(f"   🆔 Title: {title_match.group(1)}")
        else:
            print("   ❓ No title found")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def extract_strict(video_url):
    print(f"\n🎥 Analyzing Video: {video_url}")
    try:
        resp = requests.get(video_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        
        # 1. itemprop="channelId" (The most reliable for the AUTHOR)
        m1 = re.search(r'itemprop="channelId" content="(UC[\w-]+)"', resp.text)
        if m1:
            cid = m1.group(1)
            print(f"   ✅ Found Author ID (itemprop): {cid}")
            check_id_identity(cid) # Check who this is immediately
        else:
            print("   ⚠️ No itemprop channelId found.")
            
            # Debug: what IDs are there?
            all_ids = re.findall(r'"channelId":"(UC[\w-]+)"', resp.text)
            print(f"   Others found (json): {all_ids[:3]}")

    except Exception as e:
        print(f"Error: {e}")

def main():
    videos = [
        ("Blackbox Stocks", "https://www.youtube.com/watch?v=9z3CXu_BFMg"),
        ("Altri Orienti", "https://www.youtube.com/watch?v=XtdOGZMa69E")
    ]
    
    for name, url in videos:
        print(f"\n--- {name} ---")
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            
            # Search for browseId (Author ID)
            # Pattern: "browseId":"UC..." usually appears near "author" or "owner"
            # We catch all and print the most frequent or first unique ones
            ids = re.findall(r'"browseId":"(UC[\w-]+)"', resp.text)
            unique_ids = list(set(ids))
            print(f"   🆔 BrowseIDs found: {unique_ids}")
            
            # Check identity of first candidate
            if unique_ids:
                check_id_identity(unique_ids[0])
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
