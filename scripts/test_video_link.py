import requests
import re
import sys

def get_latest_video_link(handle):
    url = f"https://www.youtube.com/{handle}/videos"
    cookies = {
        'CONSENT': 'YES+cb.20230531-07-p0.en+FX+0',
        'SOCS': 'CAESEwgDEgk0ODEyMjk3MjQaAmVuIAEaBgiA_LyaBg'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    print(f"Scraping {url}...")
    try:
        resp = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        if resp.status_code != 200:
            print(f"Error: {resp.status_code}")
            return None
            
        # Regex to find the first 'watch?v=' that isn't part of some other metadata
        # Youtube strictly orders /videos by date usually.
        # We look for "url":"/watch?v=VIDEO_ID"
        match = re.search(r'"url":"/watch\?v=([\w-]+)"', resp.text)
        if match:
            video_id = match.group(1)
            return f"https://www.youtube.com/watch?v={video_id}", video_id
        
        print("No video link found in HTML.")
        # Debug: Save output
        with open("debug_videos_output.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
            
    except Exception as e:
        print(f"Error: {e}")
    return None

handles = ["@MarcoCasario", "@BlackBoxStocks", "@choramedia"]

print("--- Testing Video Link Extraction ---")
for h in handles:
    res = get_latest_video_link(h)
    if res:
        print(f"✅ {h}: {res[0]} (ID: {res[1]})")
    else:
        print(f"❌ {h} failed")
