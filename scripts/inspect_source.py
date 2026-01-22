
import sys
import json
import yt_dlp
import logging

# Configure minimal logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Inspector")

def audit_channel_strategy(url):
    """
    Analyzes a YouTube URL (Video or Channel) and returns a configuration object
    with the recommended strategy.
    
    Returns:
        dict: {
            "handle": str,
            "channel_id": str,
            "strategy": str,
            "display_name": str,
            "filter_keyword": None
        } or None if failed.
    """
    logger.info(f"🔍 Inspecting: {url} ...")
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True, # Fast extraction for channels
        'skip_download': True,
        'ignoreerrors': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. Info Extraction
            info = ydl.extract_info(url, download=False)
            
            if not info:
                logger.error("❌ Could not extract info. Check URL.")
                return None

            # Detect Type
            is_playlist = 'entries' in info
            
            channel_name = info.get('uploader') or info.get('channel')
            channel_id = info.get('channel_id')
            
            if not channel_id and is_playlist and len(info['entries']) > 0:
                # Try to get channel info from first video
                first_vid = info['entries'][0]
                channel_name = first_vid.get('uploader')
                channel_id = first_vid.get('channel_id')

            logger.info(f"📺 CHANNEL Found: {channel_name} ({channel_id})")
            
            # 2. Audit Content (Analyze last 3 videos)
            logger.info(f"🕵️ Auditing recent content...")
            
            videos_to_check = []
            if is_playlist:
                # getting first 3 from playlist
                videos_to_check = list(info['entries'])[:3]
            else:
                # it's a single video, check just this one
                videos_to_check = [info]

            audit_results = {
                "manual_subs": 0,
                "auto_subs": 0,
                "desc_avg_len": 0,
                "chapters_found": 0,
                "count": 0
            }

            for vid in videos_to_check:
                vid_url = vid.get('url') or vid.get('webpage_url')
                if not vid_url:
                    vid_url = f"https://www.youtube.com/watch?v={vid['id']}"
                
                # We need full details for subtitles, flat extraction doesn't give subs
                # So we run a separate detailed extraction for these few videos
                with yt_dlp.YoutubeDL({'quiet':True, 'skip_download':True}) as vid_dl:
                    v_info = vid_dl.extract_info(vid_url, download=False)
                    
                    # logger.info(f"   - Analyzing: {v_info.get('title')[:40]}...")
                    
                    # Check Subtitles
                    subs = v_info.get('subtitles', {})
                    auto_subs = v_info.get('automatic_captions', {})
                    
                    has_manual = 'it' in subs or 'en' in subs
                    has_auto = 'it' in auto_subs or 'en' in auto_subs
                    
                    desc = v_info.get('description', '')
                    chapters = v_info.get('chapters')
                    
                    if has_manual: audit_results['manual_subs'] += 1
                    if has_auto: audit_results['auto_subs'] += 1
                    audit_results['desc_avg_len'] += len(desc)
                    if chapters: audit_results['chapters_found'] += 1
                    audit_results['count'] += 1

            if audit_results['count'] > 0:
                audit_results['desc_avg_len'] /= audit_results['count']

            # 3. Strategy Decision
            strategy = "STRATEGY_HYBRID" # Default
            confidence = "MEDIUM"

            if audit_results['manual_subs'] == audit_results['count']:
                strategy = "STRATEGY_FULL_TRANSCRIPT"
                confidence = "HIGH (Manual Subs available)"
            elif audit_results['auto_subs'] == audit_results['count']:
                strategy = "STRATEGY_FULL_TRANSCRIPT"
                confidence = "MEDIUM (Auto Subs available)"
            elif audit_results['desc_avg_len'] > 500:
                strategy = "STRATEGY_METADATA_ONLY"
                confidence = "HIGH (Rich Descriptions)"
            else:
                strategy = "STRATEGY_METADATA_ONLY"
                confidence = "LOW (No subs, short descriptions. Quality risk.)"

            logger.info(f"🎯 Recommended Strategy: {strategy} ({confidence})")

            # 4. JSON Object
            # Use Channel ID as handle if available, it's the most stable
            handle = channel_id if channel_id else f"@{channel_name}"
            # Ensure no spaces in fallback handle
            if handle: handle = handle.replace(" ", "")
            
            source_obj = {
                "handle": handle,
                "strategy": strategy,
                "name": channel_name or handle, # Normalize key to 'name' to match schema
                "filter_keyword": None,
                # "channel_id": channel_id # We don't strictly need to save ID if we scrape by handle, but good to have? Schema uses handled.
            }
            
            return source_obj

    except Exception as e:
        logger.error(f"Error inspecting source: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_source.py <youtube_url>")
    else:
        res = audit_channel_strategy(sys.argv[1])
        if res:
            print(json.dumps(res, indent=4))
