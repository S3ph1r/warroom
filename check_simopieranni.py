
from intelligence.scrapers.youtube_scraper import YoutubeScraper

scraper = YoutubeScraper()
channel_id = "UCB6Kw-s33Qj-gk0782v69XQ" # Resolved ID for @simopieranni

print(f"Fetching videos for {channel_id}...")
videos = scraper.get_latest_videos(channel_id, limit=10)

if videos:
    print(f"Found {len(videos)} videos:")
    for v in videos:
        print(f"- {v['title']}")
else:
    print("No videos found (or RSS fetch failed).")
