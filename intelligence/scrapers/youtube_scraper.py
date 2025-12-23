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
            "AltriOrienti": "UCsYN70T0gqR5U_xmWnZKcTQ",
            "@simopieranni": "UCB6Kw-s33Qj-gk0782v69XQ",
            "simopieranni": "UCB6Kw-s33Qj-gk0782v69XQ"
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
                "author": entry.author,
                "description": entry.media_group[0]['media_description'] if 'media_group' in entry and len(entry.media_group) > 0 else entry.get('summary', '')
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

    def fetch_channel_updates(self, handle, limit=5, filter_keyword=None, display_name=None, strategy="STRATEGY_HYBRID"):
        """
        HIGH-LEVEL METHOD: Fetch latest videos, filter by keyword, get transcript.
        
        Args:
            handle: Channel handle (e.g., "@MarcoCasario").
            limit: Number of videos to scan (default 5).
            filter_keyword: If set, only keep videos containing this string in title (case-insensitive).
            display_name: Optional override for source name.
            strategy: Extraction strategy ("STRATEGY_FULL_TRANSCRIPT", "STRATEGY_METADATA_ONLY", "STRATEGY_HYBRID")
        Returns:
            List of news-item style dicts.
        """
        logger.info(f"📺 Scanning Channel: {handle} (Limit: {limit}, Filter: {filter_keyword}, Strategy: {strategy})")
        
        # 1. Resolve ID
        channel_id = self.get_channel_id(handle)
        if not channel_id:
            logger.error(f"   ❌ Could not resolve ID for {handle}")
            return []
            
        # 2. Get Videos (RSS is better for lists than scraping /videos HTML which is complex)
        # Note: HTML scraping /videos usually only gives the absolute latest easily.
        # RSS gives last 15.
        videos = self.get_latest_videos(channel_id, limit=15) # Fetch more to allow for filtering
        
        if not videos:
            logger.warning(f"   ❌ No videos found for {handle}")
            return []
            
        results = []
        count = 0
        
        for video in videos:
            if count >= limit:
                break
                
            # Filter Logic
            if filter_keyword:
                if filter_keyword.lower() not in video['title'].lower():
                    # logger.debug(f"   [Skip] '{video['title']}' does not match '{filter_keyword}'")
                    continue
            
            logger.info(f"   Found: {video['title'][:50]}... (ID: {video['video_id']})")
            
            transcript = None
            
            # --- STRATEGY EXECUTION ---
            if strategy == "STRATEGY_METADATA_ONLY":
                logger.info("   ℹ️ Strategy METADATA_ONLY: Skipping transcript fetch.")
                description = video.get('description', '')
                if description and len(description) > 50:
                    transcript = f"[DESCRIPTION ONLY] {description}"
                else:
                    logger.warning("   ❌ Description too short. Skipping.")
                    continue
                    
            elif strategy == "STRATEGY_FULL_TRANSCRIPT":
                transcript = self.get_transcript(video['video_id'])
                if not transcript:
                    logger.warning("   ❌ No transcript found (FULL_TRANSCRIPT enforced). Skipping.")
                    continue
                    
            else: # STRATEGY_HYBRID (Default)
                transcript = self.get_transcript(video['video_id'])
                if not transcript:
                    logger.warning(f"   ⚠️ No transcript available for {video['title']}. Trying fallback description.")
                    description = video.get('description', '')
                    if description and len(description) > 50:
                         transcript = f"[DESCRIPTION ONLY] {description}"
                         logger.info("   ✅ Fallback to Description successful.")
                    else:
                         logger.warning("   ❌ No meaningful description found. Skipping video.")
                         continue
            
            if not transcript:
                continue

            # Truncate for summary
            summary_preview = transcript[:2000] + ("..." if len(transcript) > 2000 else "")
            
            item = {
                "title": f"[VIDEO] {video['title']}",
                "original_title": video['title'],
                "summary": summary_preview,
                "link": video['link'],
                "published_at": video['published_at'],
                "source": display_name if display_name else f"YouTube ({handle})",
                "is_video": True,
                "video_id": video['video_id'],
                "full_transcript": transcript
            }
            results.append(item)
            count += 1
            logger.info(f"   ✅ Processed ({len(transcript)} chars)")
            
        logger.info(f"   🏁 Completed {handle}: {len(results)} videos.")
        return results

