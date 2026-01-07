import requests
import datetime
import os
import re

# ==========================================
# 1. SETUP SOURCES
# ==========================================
OUTPUT_FILE = "pocket_playlist.m3u"
YOUTUBE_FILE = "youtube.txt"

# Main Source
MAIN_SOURCE_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html"

# Live Event Sources
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SONY_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
ZEE_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# HEADER (Crucial for playback)
UA_HEADER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def fetch_content(url):
    print(f"   Downloading: {url}...")
    try:
        r = requests.get(url, headers={"User-Agent": UA_HEADER}, timeout=15)
        if r.status_code == 200:
            return r.text.splitlines()
    except Exception as e:
        print(f"   ❌ Error fetching {url}: {e}")
    return []

def extract_live_events(url):
    """Fetches a playlist and forces all channels into the 'Live Events' group."""
    raw_lines = fetch_content(url)
    cleaned_lines = []
    
    current_meta = ""
    for line in raw_lines:
        line = line.strip()
        if not line or line.startswith("#EXTM3U"): continue
        
        if line.startswith("#EXTINF"):
            # Force 'Live Events' group
            line = re.sub(r'group-title="[^"]*"', '', line)
            line = re.sub(r'(#EXTINF:[-0-9]+)', r'\1 group-title="Live Events"', line)
            current_meta = line
        elif not line.startswith("#") and current_meta:
            # Add URL
            cleaned_lines.append(current_meta)
            cleaned_lines.append(line)
            current_meta = ""
            
    return cleaned_lines

def parse_youtube_txt():
    """Reads youtube.txt and converts it to M3U format."""
    print("   Reading youtube.txt...")
    lines = []
    if not os.path.exists(YOUTUBE_FILE): return []
    try:
        with open(YOUTUBE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            content = f.readlines()
        
        title = "Unknown Channel"
        logo = "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Globe_icon.svg/1200px-Globe_icon.svg.png"
        
        for line in content:
            line = line.strip()
            if not line: continue
            
            if line.lower().startswith("title:"):
                title = line.split(":", 1)[1].strip()
            elif line.lower().startswith("link:"):
                url = line.split("link:", 1)[1].strip()
                lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{logo}",{title}')
                if "|" not in url and "http" in url: url += f"|User-Agent={UA_HEADER}"
                lines.append(url)
                title = "Unknown Channel"
    except Exception as e:
        print(f"   ❌ Error reading youtube.txt: {e}")
    return lines

# ==========================================
# 3. MAIN SCRIPT
# ==========================================
def main():
    print("🚀 Starting Playlist Generation (With Header Fix)...")
    
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines = ["#EXTM3U", f"# Updated on: {ist_now.strftime('%Y-%m-%d %H:%M:%S IST')}"]

    # 1. Process Main Source
    source_lines = fetch_content(MAIN_SOURCE_URL)
    
    # Tamil HD List (For Group Correction)
    TAMIL_HD_LIST = ["sun tv hd", "ktv hd", "sun music hd", "star vijay hd", "vijay super hd", "zee tamil hd", "zee thirai hd", "colors tamil hd", "jaya tv hd"]

    print("   Processing main channels...")
    
    # Robust Line-by-Line Parsing
    current_meta = ""
    
    for line in source_lines:
        line = line.strip()
        if not line or line.startswith("#EXTM3U"): continue
        
        if line.startswith("#EXTINF"):
            # 1. Modify Group if it's a Tamil HD channel
            name_check = line.lower()
            is_tamil_hd = False
            for thd in TAMIL_HD_LIST:
                if thd in name_check:
                    is_tamil_hd = True
                    break
            
            if is_tamil_hd:
                if 'group-title="' in line:
                    line = re.sub(r'group-title="([^"]*)"', 'group-title="Tamil HD"', line)
                else:
                    line = line.replace("#EXTINF:-1", '#EXTINF:-1 group-title="Tamil HD"')
            
            # Store metadata and wait for URL
            current_meta = line
            
        elif not line.startswith("#") and current_meta:
            # 2. This is the URL line.
            url = line
            
            # --- THE FIX: ADD HEADERS ---
            # Most of these links fail without a User-Agent.
            # We check if it already has headers (contains '|'). If not, we add ours.
            if "http" in url and "|" not in url:
                url += f"|User-Agent={UA_HEADER}"
            
            # Add to final list
            final_lines.append(current_meta)
            final_lines.append(url)
            current_meta = "" # Reset

    # 2. Append Extra Content
    print("   Appending Live Events...")
    final_lines.extend(extract_live_events(FANCODE_URL))
    final_lines.extend(extract_live_events(SONY_LIVE_URL))
    final_lines.extend(extract_live_events(ZEE_LIVE_URL))
    
    print("   Appending Temporary Channels...")
    final_lines.extend(parse_youtube_txt())

    # 3. Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print(f"✅ DONE! Playlist saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
