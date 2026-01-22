"""
Debug YouTube ID Extraction
"""
import requests
import re

def main():
    handle = "@MarcoCasario"
    url = f"https://www.youtube.com/{handle}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    print(f"Fetching {url}...")
    try:
        cookies = {'CONSENT': 'YES+cb.20210328-17-p0.en+FX+419'}
        resp = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        print(f"Status: {resp.status_code}")
        
        # Search for UC pattern
        # Common patterns: "channelId":"UC...", "browseId":"UC..."
        
        print("\n--- Regex Matches ---")
        
        # 1. channelId
        matches = re.findall(r'"channelId":"(UC[\w-]+)"', resp.text)
        print(f"channelId matches: {matches[:3]}")
        
        # 2. browseId
        matches2 = re.findall(r'"browseId":"(UC[\w-]+)"', resp.text)
        print(f"browseId matches: {matches2[:3]}")
        
        # 3. specific dumb search
        matches3 = re.findall(r'UC[\w-]{22}', resp.text)
        print(f"Generic UC matches: {matches3[:5]}")
        
        # 4. og:url
        matches4 = re.findall(r'<meta property="og:url" content="https://www.youtube.com/channel/(UC[\w-]+)">', resp.text)
        print(f"og:url matches: {matches4}")
        
        # 5. Legacy Feed Test
        legacy_url = "https://www.youtube.com/feeds/videos.xml?user=MarcoCasario"
        print(f"\nTesting Legacy Feed: {legacy_url}")
        resp2 = requests.get(legacy_url, headers=headers, timeout=5)
        print(f"Legacy Feed Status: {resp2.status_code}")
        
    except Exception as e:
        print(f"Error: {e}")

    with open("debug_output.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("Saved HTML to debug_output.html")

if __name__ == "__main__":
    main()
