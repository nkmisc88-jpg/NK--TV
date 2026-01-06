import requests
import re
import datetime
import os
import sys
import json

# ==========================================
# CONFIGURATION
# ==========================================
OUTPUT_FILE = "pocket_playlist.m3u"
YOUTUBE_FILE = "youtube.txt"
POCKET_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html" 

# 1. LIVE EVENT LINKS
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SONY_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
ZEE_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# 2. GROUP MAPPINGS
MOVE_TO_TAMIL_HD = ["Sun TV HD", "Star Vijay HD", "Colors Tamil HD", "Zee Tamil HD", "KTV HD", "Sun Music HD", "Jaya TV HD", "Zee Thirai HD", "Vijay Super HD"]
MOVE_TO_TAMIL_NEWS = ["Sun News", "News7 Tamil", "Thanthi TV", "Raj News 24x7", "Tamil Janam", "Jaya Plus", "M Nadu", "News J", "News18 Tamil Nadu", "News Tamil 24x7", "Win TV", "Zee Tamil News", "Polimer News", "Puthiya Thalaimurai", "Seithigal TV", "Sathiyam TV", "MalaiMurasu Seithigal"]
MOVE_TO_INFOTAINMENT_SD = ["GOOD TiMES", "Food Food"]
SPORTS_HD_KEEP = ["Star Sports 1 HD", "Star Sports 2 HD", "Star Sports 1 Tamil HD", "Star Sports 2 Tamil HD", "Star Sports Select 1 HD", "Star Sports Select 2 HD", "SONY TEN 1 HD", "SONY TEN 2 HD", "SONY TEN 5 HD"]
INFOTAINMENT_KEYWORDS = ["discovery", "animal planet", "nat geo", "history tv", "tlc", "bbc earth", "sony bbc", "fox life", "travelxp"]
BAD_KEYWORDS = ["fashion", "overseas", "yupp", "usa", "pluto", "sun nxt", "sunnxt", "jio specials hd"]

DEFAULT_LOGO = "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Globe_icon.svg/1200px-Globe_icon.svg.png"
# Standard User Agent for regular requests
UA_HEADER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def get_group_and_name(line):
    grp_match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
    group = grp_match.group(1).strip() if grp_match else ""
    name = line.split(",")[-1].strip()
    return group, name

def get_clean_id(name):
    return re.sub(r'[^a-z0-9]', '', name.lower().replace("hd", "").replace(" ", "").strip())

def should_keep_channel(group, name):
    check_str = (group + " " + name).lower()
    for bad in BAD_KEYWORDS:
        if bad in check_str: return False 
    return True

def fetch_live_events(url):
    print(f"   📥 Fetching M3U: {url}...")
    lines = []
    try:
        r = requests.get(url, headers={"User-Agent": UA_HEADER}, timeout=15)
        if r.status_code == 200:
            content = r.text.splitlines()
            for line in content:
                line = line.strip()
                if not line: continue
                if line.startswith("#EXTM3U"): continue
                
                if line.startswith("#EXTINF"):
                    line = re.sub(r'group-title="[^"]*"', '', line)
                    line = re.sub(r'(#EXTINF:[-0-9]+)', r'\1 group-title="Live Events"', line)
                    lines.append(line)
                elif not line.startswith("#"):
                    lines.append(line)
    except: pass
    return lines

# --- DEEP THINKING: ANDROID API SCANNER ---
def get_youtube_live_url(youtube_url):
    print(f"      🔎 Scanning YouTube (API Mode): {youtube_url}")
    try:
        # 1. Extract Video ID intelligently
        video_id = None
        if "v=" in youtube_url:
            video_id = youtube_url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in youtube_url:
            video_id = youtube_url.split("youtu.be/")[1].split("?")[0]
        elif "/live/" in youtube_url:
            video_id = youtube_url.split("/live/")[1].split("?")[0]
            
        if not video_id:
            print("         ❌ Could not find Video ID.")
            return youtube_url

        # 2. Call YouTube Internal API (Imitating Android App)
        # This bypasses the HTML scraping issues
        api_url = "https://www.youtube.com/youtubei/v1/player"
        payload = {
            "videoId": video_id,
            "context": {
                "client": {
                    "clientName": "ANDROID",
                    "clientVersion": "17.31.35",
                    "androidSdkVersion": 30,
                    "hl": "en",
                    "gl": "US",
                    "utcOffsetMinutes": 0
                }
            }
        }
        
        # Headers specifically for the API
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "com.google.android.youtube/17.31.35 (Linux; U; Android 11) gzip"
        }
        
        r = requests.post(api_url, json=payload, headers=headers, timeout=10)
        data = r.json()
        
        # 3. Extract the HLS Manifest URL
        if "streamingData" in data and "hlsManifestUrl" in data["streamingData"]:
            m3u8_url = data["streamingData"]["hlsManifestUrl"]
            print("         ✅ Found Raw Live Stream (API)!")
            return m3u8_url
            
        print("         ❌ Live stream not found in API response (Is it offline?)")
    
    except Exception as e:
        print(f"         ❌ Error scanning YouTube: {e}")
    
    # Fallback: Return original URL if API fails, so at least something exists
    return youtube_url 

def parse_youtube_txt():
    print("   ...Reading youtube.txt")
    lines = []
    if not os.path.exists(YOUTUBE_FILE): return []
    
    try:
        with open(YOUTUBE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            file_lines = f.readlines()
        
        current_title = "Unknown Channel"
        current_logo = DEFAULT_LOGO
        current_props = [] 
        
        for line in file_lines:
            line = line.strip()
            if not line: continue
            if len(line) > 400: continue

            lower_line = line.lower()

            if lower_line.startswith("title"):
                parts = line.split(":", 1)
                if len(parts) > 1: current_title = parts[1].strip()
            
            elif lower_line.startswith("logo"):
                parts = line.split(":", 1)
                if len(parts) > 1: current_logo = parts[1].strip()

            elif line.startswith("#"):
                current_props.append(line)
            
            elif "http" in lower_line:
                url_start = lower_line.find("http")
                url = line[url_start:].strip()
                
                # --- AUTO-CONVERT YOUTUBE LINKS ---
                if "youtube.com" in url or "youtu.be" in url:
                    url = get_youtube_live_url(url)
                # ----------------------------------

                if current_props:
                    lines.extend(current_props)
                    current_props = [] 
                
                lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{current_logo}",{current_title}')
                
                # Only add User-Agent if it's NOT a raw YouTube HLS link (YouTube HLS hates headers)
                if "googlevideo.com" not in url:
                    if "|" not in url and "http" in url:
                        url += f"|User-Agent={UA_HEADER}"
                
                lines.append(url)
                
                current_title = "Unknown Channel"
                current_logo = DEFAULT_LOGO
                current_props = []

    except Exception as e:
        print(f"   ❌ Error reading youtube.txt: {e}")
    return lines

# ==========================================
# MAIN LOGIC
# ==========================================
def main():
    print("📥 Downloading Source Playlist...")
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines = ["#EXTM3U"]
    final_lines.append(f"# Last Updated: {ist_now.strftime('%Y-%m-%d %H:%M:%S IST')}")
    final_lines.append("http://0.0.0.0")

    try:
        r = requests.get(POCKET_URL, headers={"User-Agent": UA_HEADER}, timeout=30)
        source_lines = r.text.splitlines()
    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)

    hd_channels_exist = set()
    for line in source_lines:
        if line.startswith("#EXTINF"):
            _, name = get_group_and_name(line)
            if "hd" in name.lower(): hd_channels_exist.add(get_clean_id(name))

    seen_channels = set()
    current_buffer = []

    for line in source_lines:
        line = line.strip()
        if not line: continue
        if line.startswith("#EXTM3U"): continue

        if line.startswith("#EXTINF"):
            if current_buffer: final_lines.extend(current_buffer)
            current_buffer = []

            group, name = get_group_and_name(line)
            clean_name = name.lower().strip()
            
            if not should_keep_channel(group, name): current_buffer = []; continue
            if "hd" not in clean_name and get_clean_id(name) in hd_channels_exist: current_buffer = []; continue

            exact_id = get_clean_id(name)
            is_duplicate = exact_id in seen_channels
            if not is_duplicate: seen_channels.add(exact_id)

            new_group = group 
            
            # FORCE KEEP ZEE TAMIL/THIRAI HD
            if "zee tamil hd" in clean_name:
                new_group = "Tamil HD"; is_duplicate = False 
            elif "zee thirai hd" in clean_name:
                new_group = "Tamil HD"; is_duplicate = False
            
            elif is_duplicate:
                new_group = "Backup"
            else:
                group_lower = group.lower()
                if group_lower in ["tamil", "local channels"] or "astro" in group_lower: new_group = "Tamil Extra"
                if "news" in group_lower and "tamil" not in group_lower: new_group = "English and Hindi News"
                if any(t in clean_name for t in MOVE_TO_TAMIL_NEWS): new_group = "Tamil News"
                if any(t in clean_name for t in MOVE_TO_TAMIL_HD): new_group = "Tamil HD"
                if any(t in clean_name for t in SPORTS_HD_KEEP): new_group = "Sports HD"
                if any(t in clean_name for t in MOVE_TO_INFOTAINMENT_SD): new_group = "Infotainment SD"

            if new_group != group:
                if 'group-title="' in line:
                    line = re.sub(r'group-title="([^"]*)"', f'group-title="{new_group}"', line)
                else:
                    line = line.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{new_group}"')

        current_buffer.append(line)
        if not line.startswith("#"):
            current_buffer[-1] = line; final_lines.extend(current_buffer); current_buffer = []

    if current_buffer: final_lines.extend(current_buffer)

    print("📥 Adding Live Events...")
    final_lines.extend(fetch_live_events(FANCODE_URL))
    final_lines.extend(fetch_live_events(SONY_LIVE_URL))
    final_lines.extend(fetch_live_events(ZEE_LIVE_URL))
    
    print("📥 Adding Temporary Channels...")
    final_lines.extend(parse_youtube_txt())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    print(f"\n✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
