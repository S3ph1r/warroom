import requests
import re
import youtube_transcript_api
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

def get_latest_video_id(handle):
    url = f"https://www.youtube.com/{handle}/videos"
    cookies = {
        'CONSENT': 'YES+cb.20230531-07-p0.en+FX+0',
        'SOCS': 'CAESEwgDEgk0ODEyMjk3MjQaAmVuIAEaBgiA_LyaBg'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    print(f"🔍 Scraping {url}...")
    try:
        resp = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        match = re.search(r'"url":"/watch\?v=([\w-]+)"', resp.text)
        if match:
            return match.group(1)
        print("  ❌ No video link found in HTML.")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    return None

def get_transcript(video_id):
    print(f"  📄 Fetching transcript for {video_id}...")
    try:
        # Based on error, fetch is an instance method.
        if hasattr(YouTubeTranscriptApi, 'fetch'):
            print("  debug: calling YouTubeTranscriptApi().fetch()")
            try:
                api = YouTubeTranscriptApi()
                # Pass languages explicitly!
                transcript = api.fetch(video_id, languages=['it', 'en'])
                return TextFormatter().format_transcript(transcript)
            except Exception as inst_err:
                print(f"  debug: Instantiation fetch failed: {inst_err}")
                # Fallback: maybe it's static but I messed up? No, 1 missing arg meant it consumed 1 as self.
                return None
            
        elif hasattr(YouTubeTranscriptApi, 'list'):
             print("  debug: calling .list()")
             # list likely returns available transcripts
             transcript_list = YouTubeTranscriptApi.list(video_id)
             # Assume we can just pick one? For now let's just print type
             print(f"  debug: list returned type {type(transcript_list)}")
             return None
             
        else:
             print("  ❌ No known methods found.")
             return None
            
    except Exception as e:
        print(f"  ❌ Transcript failed: {e}")
        return None

handles = ["@MarcoCasario", "@BlackBoxStocks", "@choramedia"]

print("--- 🕵️ VERIFYING TRANSCRIPTS ---")

results = {}

for handle in handles:
    print(f"\nChecking {handle}...")
    vid = get_latest_video_id(handle)
    
    if vid:
        print(f"  ✅ Video Found: https://youtu.be/{vid}")
        text = get_transcript(vid)
        if text:
            preview = text[:150].replace('\n', ' ')
            print(f"  ✅ Transcript OK ({len(text)} chars)")
            print(f"  📝 Preview: \"{preview}...\"")
            
            # Save simple artifact
            with open(f"transcript_{handle.replace('@','')}.txt", "w", encoding="utf-8") as f:
                f.write(text)
                
            results[handle] = "OK"
        else:
            print("  ❌ NO Subtitles available.")
            results[handle] = "NO SUBTITLES"
    else:
        results[handle] = "NO VIDEO FOUND"

print("\n--- SUMMARY ---")
for h, status in results.items():
    icon = "✅" if status == "OK" else "❌"
    print(f"{icon} {h}: {status}")
