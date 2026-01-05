import requests
import datetime
import os
import sys

# ==========================================
# CONFIGURATION
# ==========================================
OUTPUT_FILE = "pocket_playlist.m3u"
YOUTUBE_FILE = "youtube.txt"
POCKET_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html" 

# LIVE EVENTS
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SONY_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
ZEE_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

def fetch_playlist_lines(url):
    """Downloads a playlist and returns its lines exactly as is."""
    lines = []
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if r.status_code == 200:
            content = r.text.splitlines()
            for line in content:
                line = line.strip()
                if not line: continue
                # Skip the #EXTM3U header from sources so we don't have duplicates
                if line.startswith("#EXTM3U"): continue
                lines.append(line)
    except:
        pass
    return lines

def parse_youtube_txt():
    """Reads youtube.txt and formats it for M3U."""
    lines = []
    if not os.path.exists(YOUTUBE_FILE): return []
    try:
        with open(YOUTUBE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            file_lines = f.readlines()
        
        current_title = ""
        current_logo = ""
        
        for line in file_lines:
            line = line.strip()
            if not line: continue
            
            if line.lower().startswith("title"):
                parts = line.split(":", 1)
                if len(parts) > 1: current_title = parts[1].strip()
            
            elif line.lower().startswith("logo"):
                parts = line.split(":", 1)
                if len(parts) > 1: current_logo = parts[1].strip()

            elif line.lower().startswith("link") or line.startswith("http"):
                url = line
                if line.lower().startswith("link"):
                    parts = line.split(":", 1)
                    if len(parts) > 1: url = parts[1].strip()
                
                if url.startswith("http") or url.startswith("rtmp"):
                    if not current_title: current_title = "Temporary Channel"
                    
                    # Create Entry
                    lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{current_logo}",{current_title}')
                    lines.append(url)
                    
                    current_title = ""
                    current_logo = ""
    except: pass
    return lines

def main():
    print("📥 Downloading Source Playlist...")
    
    # 1. Header
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines = ["#EXTM3U"]
    final_lines.append(f"# Last Updated: {ist_now.strftime('%Y-%m-%d %H:%M:%S IST')}")
    final_lines.append("http://0.0.0.0")

    # 2. Get Main Source (EXACT COPY)
    # We do NOT touch the lines. No checking for http, no adding headers.
    final_lines.extend(fetch_playlist_lines(POCKET_URL))

    # 3. Add Live Events
    print("📥 Adding Live Events...")
    final_lines.extend(fetch_playlist_lines(FANCODE_URL))
    final_lines.extend(fetch_playlist_lines(SONY_LIVE_URL))
    final_lines.extend(fetch_playlist_lines(ZEE_LIVE_URL))

    # 4. Add YouTube
    final_lines.extend(parse_youtube_txt())

    # 5. Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print(f"\n✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()