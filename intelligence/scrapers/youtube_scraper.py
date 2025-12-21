"""
YouTube Scraper & Transcript Fetcher
"""
import requests
import re
import feedparser
import logging
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

logger = logging.getLogger(__name__)

class YoutubeScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def get_channel_id(self, handle):
        """
        Resolves a handle (e.g. @MarcoCasario) to a UC Channel ID by scraping the page.
        Also accepts direct UC IDs.
        """
        handle = handle.strip()
        
        # If it looks like a UC ID, return as is
        if handle.startswith("UC") and len(handle) >= 20:
            return handle

        # Known Channel IDs (Hardcoded to bypass consent scraping issues)
        KNOWN_ID_MAP = {
            "@MarcoCasario": "UCZp2KqGRkO1goEAaxX5Huyg",
            "MarcoCasario": "UCZp2KqGRkO1goEAaxX5Huyg",
            "@BlackBoxStocks": "UC6eiypGm-D04Y2gR2DHsojQ",
            "BlackBoxStocks": "UC6eiypGm-D04Y2gR2DHsojQ",
            "@choramedia": "UCsYN70T0gqR5U_xmWnZKcTQ",
            "ChoraMedia": "UCsYN70T0gqR5U_xmWnZKcTQ",
            "@AltriOrienti": "UCsYN70T0gqR5U_xmWnZKcTQ", # Hosted on Chora Media
            "AltriOrienti": "UCsYN70T0gqR5U_xmWnZKcTQ"
        }
        
        if handle in KNOWN_ID_MAP:
            logger.info(f"Using known ID for {handle}: {KNOWN_ID_MAP[handle]}")
            return KNOWN_ID_MAP[handle]

        if not handle.startswith("@"):
            handle = "@" + handle
            
        url = f"https://www.youtube.com/{handle}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                # Look for externalId":"UC...
                match = re.search(r'"externalId":"(UC[\w-]+)"', resp.text)
                if match:
                    return match.group(1)
                
                # Fallback: sometimes it's channelId" content="UC...
                match = re.search(r'itemprop="channelId" content="(UC[\w-]+)"', resp.text)
                if match:
                    return match.group(1)
            else:
                print(f"❌ Failed to resolve {handle}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"❌ Error resolving {handle}: {e}")
            
        return None

    def get_latest_video_from_handle(self, handle):
        """
        Fetch the latest video by scraping the channel's /videos page directly.
        This is more reliable than RSS feeds which often 404.
        Returns: (video_id, video_title) or (None, None)
        """
        if not handle.startswith("@"):
            handle = "@" + handle
            
        url = f"https://www.youtube.com/{handle}/videos"
        cookies = {
            'CONSENT': 'YES+cb.20230531-07-p0.en+FX+0',
            'SOCS': 'CAESEwgDEgk0ODEyMjk3MjQaAmVuIAEaBgiA_LyaBg'
        }
        
        try:
            resp = requests.get(url, headers=self.headers, cookies=cookies, timeout=10)
            if resp.status_code != 200:
                logger.error(f"Failed to scrape {url}: HTTP {resp.status_code}")
                return None, None
                
            # Find first video link
            match = re.search(r'"url":"/watch\?v=([\w-]+)"', resp.text)
            if match:
                video_id = match.group(1)
                
                # Try to get title too
                title_match = re.search(rf'"videoId":"{video_id}"[^}}]*"title":\{{"runs":\[\{{"text":"([^"]+)"', resp.text)
                title = title_match.group(1) if title_match else f"Video {video_id}"
                
                return video_id, title
                
        except Exception as e:
            logger.error(f"Error scraping videos page for {handle}: {e}")
            
        return None, None

    def get_latest_videos(self, channel_id, limit=3):
        """
        Fetches latest videos from the RSS feed.
        """
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        
        # Use requests to fetch with headers (avoid 403 Forbidden)
        try:
            resp = requests.get(rss_url, headers=self.headers, timeout=10)
            if resp.status_code != 200:
                logger.error(f"Failed to fetch RSS {rss_url}: {resp.status_code}")
                return []
            
            feed = feedparser.parse(resp.content)
        except Exception as e:
            logger.error(f"Error fetching RSS: {e}")
            return []
        
        videos = []
        for entry in feed.entries[:limit]:
            videos.append({
                "video_id": entry.yt_videoid,
                "title": entry.title,
                "link": entry.link,
                "published_at": entry.published,
                "author": entry.author
            })
        return videos

    def get_transcript(self, video_id):
        """
        Fetches transcript for a video using the VERIFIED instantiated API.
        """
        try:
            # Use instantiated API (tested to work with youtube-transcript-api==1.2.3+)
            api = YouTubeTranscriptApi()
            transcript_data = api.fetch(video_id, languages=['it', 'en'])
            
            formatter = TextFormatter()
            text = formatter.format_transcript(transcript_data)
            return text
        except Exception as e:
            logger.warning(f"No transcript for {video_id}: {e}")
            return None

    def fetch_channel_updates(self, handle, limit=1):
        """
        HIGH-LEVEL METHOD: Fetch latest video from a channel, get transcript, return as NewsItem.
        Uses the RELIABLE direct scraping method instead of broken RSS feeds.
        
        Args:
            handle: Channel handle (e.g., "@MarcoCasario") or UC ID.
            limit: Currently only fetches 1 video (most recent).
        Returns:
            List of news-item style dicts.
        """
        print(f"📺 Scanning Channel: {handle}...")
        
        # Use new direct scraping method
        video_id, title = self.get_latest_video_from_handle(handle)
        
        if not video_id:
            print(f"   ❌ Could not find any video for {handle}")
            return []
        
        print(f"   Found: {title[:50]}... (ID: {video_id})")
        
        # Get transcript
        transcript = self.get_transcript(video_id)
        if not transcript:
            print(f"   ⚠️ No transcript available for this video.")
            return []  # Skip if no subtitles
            
        # Truncate for summary (2000 chars preview, full stored separately)
        summary_preview = transcript[:2000] + ("..." if len(transcript) > 2000 else "")
        
        item = {
            "title": f"[VIDEO] {title}",
            "summary": summary_preview,  # For LLM analysis
            "link": f"https://www.youtube.com/watch?v={video_id}",
            "published_at": "",  # Not easily available without RSS, could add later
            "source": f"YouTube ({handle})",
            "is_video": True,
            "full_transcript": transcript
        }
        
        print(f"   ✅ Transcript fetched ({len(transcript)} chars)")
        return [item]

