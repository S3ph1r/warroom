
from intelligence.scrapers.youtube_scraper import YoutubeScraper

scraper = YoutubeScraper()
handle = "@choramedia"
channel_id = scraper.get_channel_id(handle)
print(f"Channel ID: {channel_id}")
videos = scraper.get_latest_videos(channel_id, limit=15)
print(f"Found {len(videos)} videos:")
for v in videos:
    print(f"- {v['title']}")
