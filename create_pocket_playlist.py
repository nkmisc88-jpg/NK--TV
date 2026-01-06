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

# 1. LIVE EVENT LINKS (M3U)
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SONY_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
ZEE_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# 2. LIVE EVENT LINKS (JSON - DebugDyno)
HOTSTAR_JSON = "https://raw.githubusercontent.com/DebugDyno/yo_events/main/data/jiohotstar.json"
WATCHO_JSON  = "https://raw.githubusercontent.com/DebugDyno/yo_events/main/data/watcho.json"
SONY_JSON    = "https://raw.githubusercontent.com/DebugDyno/yo_events/main/data/sonyliv.json"

# 3. GROUP MAPPING LISTS
MOVE_TO_TAMIL_HD = [
    "Sun TV HD", "Star Vijay HD", "Colors Tamil HD", 
    "Zee Tamil HD", "KTV HD", "Sun Music HD", "Jaya TV HD",
    "Zee Thirai HD", "Vijay Super HD"
]

MOVE_TO_TAMIL_NEWS = [
    "Sun News", "News7 Tamil", "Thanthi TV", "Raj News 24x7", 
    "Tamil Janam", "Jaya Plus", "M Nadu", "News J", 
    "News18 Tamil Nadu", "News Tamil 24x7", "Win TV", 
    "Zee Tamil News", "Polimer News", "Puthiya Thalaimurai", 
    "Seithigal TV", "Sathiyam TV", "MalaiMurasu Seithigal"
]

MOVE_TO_INFOTAINMENT_SD = ["GOOD TiMES", "Food Food"]

SPORTS_HD_KEEP = [
    "Star Sports 1 HD", "Star Sports 2 HD", 
    "Star Sports 1 Tamil HD", "Star Sports 2 Tamil HD", 
    "Star Sports Select 1 HD", "Star Sports Select 2 HD", 
    "SONY TEN 1 HD", "SONY TEN 2 HD", "SONY TEN 5 HD"
]

INFOTAINMENT_KEYWORDS = ["discovery", "animal planet", "nat geo", "history tv", "tlc", "bbc earth", "sony bbc", "fox life", "travelxp"]
BAD_KEYWORDS = ["fashion", "overseas", "yupp", "usa", "pluto", "sun nxt", "sunnxt", "jio specials hd"]

DEFAULT_LOGO = "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Globe_icon.svg/1200px-Globe_icon.svg.png"
UA_HEADER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ==========================================
# FUNCTIONS
# ==========================================

def fetch_json_events(url):
    """Parses DebugDyno JSON files for Live Events"""
    print(f"   📥 Fetching JSON: {url}...")
    lines = []
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            items = []
            if isinstance(data, list): items = data
            elif isinstance(data, dict):
                for key in ["channels", "events", "data", "matches"]:
                    if key in data and isinstance(data[key], list): items = data[key]; break
            
            for item in items:
                name = item.get("name") or item.get("title") or "Unknown Event"
                stream_url = item.get("url") or item.get("stream_url") or item.get("link")
                logo = item.get("logo") or DEFAULT_LOGO
                
                if stream_url:
                    lines.append(f'#EXTINF:-1 group-title="Live Events" tvg-logo="{logo}",{name}')
                    # Add User-Agent if missing
                    if "|" not in stream_url and "http" in stream_url: 
                        stream_url += "|User-Agent=Mozilla/5.0"
                    lines.append(stream_url)
    except: pass
    return lines

def fetch_live_events(url):
    """Parses Standard M3U files for Live Events"""
    print(f"   📥 Fetching M3U: {url}...")
    lines = []
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code == 200:
            content = r.text.splitlines()
            for line in content:
                line = line.strip()
                if not line: continue
                if line.startswith("#EXTM3U"): continue
                
                if line.startswith("#EXTINF"):
                    # Force group to "Live Events"
                    line = re.sub(r'group-title="([^"]*)"', '', line)
                    line = re.sub(r'(#EXTINF:[-0-9]+)', r'\1 group-title="Live Events"', line)
                    lines.append(line)
                elif not line.startswith("#"):
                    lines.append(line)
    except: pass
    return lines

def parse_youtube_txt():
    """Reads youtube.txt and adds links to 'Temporary Channels'"""
    print("   ...Reading youtube.txt")
    lines = []
    if not os.path.exists(YOUTUBE_FILE): return []
    
    try:
        with open(YOUTUBE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            file_lines = f.readlines()
        
        current_title = "Unknown Channel"
        current_logo = DEFAULT_LOGO
        
        for line in file_lines:
            line = line.strip()
            if not line: continue
            
            # Skip massive junk lines (Garbage protection)
            if len(line) > 300: continue

            lower_line = line.lower()

            if lower_line.startswith("title"):
                parts = line.split(":", 1)
                if len(parts) > 1: current_title = parts[1].strip()
            
            elif lower_line.startswith("logo"):
                parts = line.split(":", 1)
                if len(parts) > 1: current_logo = parts[1].strip()
            
            elif "http" in lower_line:
                # Find the URL part
                url_start = lower_line.find("http")
                url = line[url_start:].strip()
                
                # Simple Logic: Just add what is there
                lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{current_logo}",{current_title}')
                
                # Add Header if missing
                if "|" not in url: url += f"|User-Agent={UA_HEADER}"
                lines.append(url)
                
                # Reset
                current_title = "Unknown Channel"
                current_logo = DEFAULT_LOGO

    except Exception as e:
        print(f"   ❌ Error reading youtube.txt: {e}")
    return lines

# ==========================================
# MAIN SCRIPT
# ==========================================
def main():
    print("📥 Downloading Source Playlist...")
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines = ["#EXTM3U"]
    final_lines.append(f"# Last Updated: {ist_now.strftime('%Y-%m-%d %H:%M:%S IST')}")
    final_lines.append("http://0.0.0.0")

    # Helper function needed inside main for mapping
    def get_group_and_name(line):
        grp_match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
        group = grp_match.group(1).strip() if grp_match else ""
        name = line.split(",")[-1].strip()
        return group, name

    def get_clean_id(name):
        name = name.lower().replace("hd", "").replace(" ", "").strip()
        return re.sub(r'[^a-z0-9]', '', name)

    def should_keep_channel(group, name):
        check_str = (group + " " + name).lower()
        for bad in BAD_KEYWORDS:
            if bad in check_str: return False 
        return True

    try:
        r = requests.get(POCKET_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        source_lines = r.text.splitlines()
    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)

    # 1. Scan for HD Channels first
    hd_channels_exist = set()
    for line in source_lines:
        if line.startswith("#EXTINF"):
            _, name = get_group_and_name(line)
            if "hd" in name.lower():
                hd_channels_exist.add(get_clean_id(name))

    # 2. Process Channels
    seen_channels = set()
    current_buffer = []
    zee_tamil_count = 0

    for line in source_lines:
        line = line.strip()
        if not line: continue
        if line.startswith("#EXTM3U"): continue

        if line.startswith("#EXTINF"):
            if current_buffer:
                final_lines.extend(current_buffer)
            current_buffer = []

            group, name = get_group_and_name(line)
            clean_name = name.lower().strip()
            
            if not should_keep_channel(group, name):
                current_buffer = []; continue

            if "hd" not in clean_name:
                base_id = get_clean_id(name)
                if base_id in hd_channels_exist:
                    current_buffer = []; continue

            exact_clean_id = re.sub(r'[^a-z0-9]', '', clean_name)
            is_duplicate = False
            if exact_clean_id in seen_channels:
                is_duplicate = True
            else:
                seen_channels.add(exact_clean_id)

            new_group = group 
            
            if "zee tamil hd" in clean_name:
                zee_tamil_count += 1
                if zee_tamil_count == 1: new_group = "Backup"; is_duplicate = True
                elif zee_tamil_count == 2: new_group = "Tamil HD"; is_duplicate = False
                else: new_group = "Backup"
            elif is_duplicate:
                new_group = "Backup"
            else:
                group_lower = group.lower()
                if group_lower == "tamil": new_group = "Tamil Extra"
                if group_lower == "local channels": new_group = "Tamil Extra"
                if "premium 24/7" in group_lower: new_group = "Tamil Extra"
                if "astro go" in group_lower: new_group = "Tamil Extra"
                if group_lower == "sports": new_group = "Sports Extra"
                if "extras" in group_lower: new_group = "Others" 
                if "entertainment" in group_lower: new_group = "Others"
                if "movies" in group_lower: new_group = "Others"
                if "music" in group_lower: new_group = "Others"
                if "infotainment" in group_lower: new_group = "Infotainment HD"

                if "news" in group_lower and "tamil" not in group_lower and "malayalam" not in group_lower:
                    new_group = "English and Hindi News"

                if new_group == "Tamil Extra" and "sports" in clean_name: new_group = "Sports Extra"
                if "j movies" in clean_name or "raj digital plus" in clean_name: new_group = "Tamil Extra"
                if "rasi movies" in clean_name or "rasi hollywood" in clean_name: new_group = "Tamil Extra"
                if "dd sports" in clean_name: new_group = "Sports Extra"
                
                if any(target.lower() in clean_name for target in MOVE_TO_INFOTAINMENT_SD): new_group = "Infotainment SD"
                if any(k in clean_name for k in INFOTAINMENT_KEYWORDS):
                    if "hd" not in clean_name: new_group = "Infotainment SD"

                for target in SPORTS_HD_KEEP:
                    if target.lower() in clean_name: new_group = "Sports HD"; break
                
                if any(target.lower() == clean_name for target in [x.lower() for x in MOVE_TO_TAMIL_NEWS]): new_group = "Tamil News"
                if any(target.lower() == clean_name for target in [x.lower() for x in MOVE_TO_TAMIL_HD]): new_group = "Tamil HD"

            if new_group != group:
                if 'group-title="' in line:
                    line = re.sub(r'group-title="([^"]*)"', f'group-title="{new_group}"', line)
                else:
                    line = line.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{new_group}"')

        current_buffer.append(line)

        if not line.startswith("#"):
            current_buffer[-1] = line
            final_lines.extend(current_buffer)
            current_buffer = []

    if current_buffer: final_lines.extend(current_buffer)

    print("📥 Adding Live Events (M3U)...")
    final_lines.extend(fetch_live_events(FANCODE_URL))
    final_lines.extend(fetch_live_events(SONY_LIVE_URL))
    final_lines.extend(fetch_live_events(ZEE_LIVE_URL))
    
    print("📥 Adding Live Events (JSON)...")
    final_lines.extend(fetch_json_events(HOTSTAR_JSON))
    final_lines.extend(fetch_json_events(WATCHO_JSON))
    final_lines.extend(fetch_json_events(SONY_JSON))

    print("📥 Adding Temporary Channels (youtube.txt)...")
    final_lines.extend(parse_youtube_txt())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    print(f"\n✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()