import requests
import re
import datetime
import os
import sys

# ==========================================
# CONFIGURATION
# ==========================================
OUTPUT_FILE = "pocket_playlist.m3u"
YOUTUBE_FILE = "youtube.txt"
POCKET_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html" 

# 1. GROUP MAPPING (For the 1st copy of the channel)
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

MOVE_TO_INFOTAINMENT_SD = [
    "GOOD TiMES", "Food Food"
]

SPORTS_HD_KEEP = [
    "Star Sports 1 HD", "Star Sports 2 HD", 
    "Star Sports 1 Tamil HD", "Star Sports 2 Tamil HD", 
    "Star Sports Select 1 HD", "Star Sports Select 2 HD", 
    "SONY TEN 1 HD", "SONY TEN 2 HD", "SONY TEN 5 HD"
]

INFOTAINMENT_KEYWORDS = [
    "discovery", "animal planet", "nat geo", "history tv", 
    "tlc", "bbc earth", "sony bbc", "fox life", "travelxp"
]

# 2. DELETE LIST
BAD_KEYWORDS = ["fashion"]

# 3. LIVE EVENTS
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SONY_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
ZEE_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# 4. AUTO LOGO
LOGO_MAP = {
    "willow": "https://i.imgur.com/39s1fL3.png",
    "fox": "https://i.imgur.com/39s1fL3.png"
}

# Standard User Agent (Only used for YouTube/Live events, NOT applied to main channels)
UA_HEADER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def get_group_and_name(line):
    grp_match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
    group = grp_match.group(1).strip() if grp_match else ""
    name = line.split(",")[-1].strip()
    return group, name

def should_keep_channel(name):
    # Only checks for "fashion"
    clean_name = name.lower()
    for bad in BAD_KEYWORDS:
        if bad in clean_name: return False 
    return True

def fetch_playlist_lines(url):
    lines = []
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if r.status_code == 200:
            content = r.text.splitlines()
            for line in content:
                line = line.strip()
                if not line: continue
                if line.startswith("#EXTM3U"): continue
                lines.append(line)
    except: pass
    return lines

def parse_youtube_txt():
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
                    lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{current_logo}",{current_title}')
                    if "http" in url and "|" not in url: url += f"|User-Agent={UA_HEADER}"
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

    # 2. Fetch Source
    try:
        r = requests.get(POCKET_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        source_lines = r.text.splitlines()
    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)

    seen_channels = set()
    current_buffer = []

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
            
            # A. DELETE FILTER (Fashion TV)
            if not should_keep_channel(name):
                current_buffer = []
                continue

            # B. IDENTIFY DUPLICATES
            clean_id = re.sub(r'[^a-z0-9]', '', clean_name)
            is_duplicate = False
            if clean_id in seen_channels:
                is_duplicate = True
            else:
                seen_channels.add(clean_id)

            # C. GROUP RENAMING LOGIC
            new_group = group 
            
            if is_duplicate:
                # If it's a duplicate, move it to Backup immediately
                new_group = "Backup"
            else:
                # Only rename if it's the MAIN (first) copy
                group_lower = group.lower()

                # Base Renames
                if group_lower == "tamil": new_group = "Tamil SD"
                if group_lower == "local channels": new_group = "Tamil Extra"
                if "premium 24/7" in group_lower: new_group = "Tamil Extra"
                if "astro go" in group_lower: new_group = "Tamil Extra"
                if group_lower == "sports": new_group = "Sports Extra"
                
                # Others (Entertainment, Movies, Music)
                if "entertainment" in group_lower: new_group = "Others"
                if "movies" in group_lower: new_group = "Others"
                if "music" in group_lower: new_group = "Others"

                # Infotainment
                if "infotainment" in group_lower: new_group = "Infotainment HD"

                # News
                if "news" in group_lower and "tamil" not in group_lower and "malayalam" not in group_lower:
                    new_group = "English and Hindi News"

                # Specific Moves
                if "j movies" in clean_name or "raj digital plus" in clean_name: new_group = "Tamil SD"
                if "rasi movies" in clean_name or "rasi hollywood" in clean_name: new_group = "Tamil Extra"
                if "dd sports" in clean_name: new_group = "Sports Extra"
                    
                # Infotainment SD Moves
                if any(target.lower() in clean_name for target in MOVE_TO_INFOTAINMENT_SD):
                     new_group = "Infotainment SD"

                if any(k in clean_name for k in INFOTAINMENT_KEYWORDS):
                    if "hd" not in clean_name: new_group = "Infotainment SD"

                # Sports HD
                for target in SPORTS_HD_KEEP:
                    if target.lower() in clean_name: new_group = "Sports HD"; break
                
                # Tamil News
                if any(target.lower() == clean_name for target in [x.lower() for x in MOVE_TO_TAMIL_NEWS]):
                    new_group = "Tamil News"

                # Tamil HD
                if any(target.lower() == clean_name for target in [x.lower() for x in MOVE_TO_TAMIL_HD]): 
                    new_group = "Tamil HD"

            # Apply New Group Name
            if new_group != group:
                if 'group-title="' in line:
                    line = re.sub(r'group-title="([^"]*)"', f'group-title="{new_group}"', line)
                else:
                    line = line.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{new_group}"')

        current_buffer.append(line)

        if not line.startswith("#"):
            # NO MODIFICATION TO LINK. RAW COPY.
            current_buffer[-1] = line
            
            final_lines.extend(current_buffer)
            current_buffer = []

    if current_buffer:
        final_lines.extend(current_buffer)

    # ADD LIVE EVENTS
    print("📥 Adding Live Events...")
    final_lines.extend(fetch_playlist_lines(FANCODE_URL))
    final_lines.extend(fetch_playlist_lines(SONY_LIVE_URL))
    final_lines.extend(fetch_playlist_lines(ZEE_LIVE_URL))
    final_lines.extend(parse_youtube_txt())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print(f"\n✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()