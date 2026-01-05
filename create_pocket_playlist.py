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

# 1. MOVE TO TAMIL HD
MOVE_TO_TAMIL_HD = [
    "Sun TV HD", "Star Vijay HD", "Colors Tamil HD", 
    "Zee Tamil HD", "KTV HD", "Sun Music HD", "Jaya TV HD",
    "Zee Thirai HD", "Vijay Super HD"
]

# 2. FILTERS (Global Deletions)
BAD_KEYWORDS = ["pluto", "usa", "yupp", "sunnxt", "overseas", "extras", "apac"]

# 3. ASTRO KEEP LIST
ASTRO_KEEP = [
    "vinmeen", "thangathirai", "vaanavil", 
    "vasantham", "vellithirai", "sports plus"
]

# 4. LIVE EVENTS
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SONY_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
ZEE_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# 5. AUTO LOGO MAP (Updated with reliable URLs)
LOGO_MAP = {
    "willow": "https://upload.wikimedia.org/wikipedia/commons/8/83/Willow_TV_logo.png",
    "fox": "https://i.imgur.com/39s1fL3.png", 
    "star sports": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/Star_Sports_network.svg/1200px-Star_Sports_network.svg.png",
    "sony": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Sony_LIV_logo.svg/1200px-Sony_LIV_logo.svg.png",
    "zee": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Zee5_logo.svg/1200px-Zee5_logo.svg.png",
    "sun": "https://upload.wikimedia.org/wikipedia/en/thumb/8/80/Sun_TV_Network_Logo.png/220px-Sun_TV_Network_Logo.png",
    "colors": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Colors_TV_Logo.png/1200px-Colors_TV_Logo.png",
    "astro": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Astro_logo.svg/1200px-Astro_logo.svg.png",
    "fancode": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/54/FanCode_Logo.png/1200px-FanCode_Logo.png"
}

# BROWSER HEADER (Fixes Playback Errors)
UA_HEADER = "|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def get_group_and_name(line):
    grp_match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
    group = grp_match.group(1).strip() if grp_match else ""
    name = line.split(",")[-1].strip()
    return group, name

def should_keep_channel(group, name):
    # Remove Placeholder Dashed Lines
    if "----" in name: return False
    
    if "apac" in name.lower(): return False
    
    clean_group = group.lower().replace(" ", "")
    for bad in BAD_KEYWORDS:
        if bad in clean_group: return False 
            
    if "astro go" in group.lower():
        is_allowed = False
        for allowed in ASTRO_KEEP:
            if allowed in name.lower():
                is_allowed = True; break
        if not is_allowed: return False 
    return True

def fetch_live_events(url):
    events = []
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code == 200:
            lines = r.text.splitlines()
            for line in lines:
                line = line.strip()
                if not line: continue
                if line.startswith("#EXTINF"):
                    line = re.sub(r'group-title="([^"]*)"', '', line)
                    line = re.sub(r'(#EXTINF:[-0-9]+)', r'\1 group-title="Live Events"', line)
                    events.append(line)
                elif not line.startswith("#"):
                    events.append(line)
    except: pass
    return events

def get_auto_logo(channel_name):
    name_lower = channel_name.lower()
    for key, url in LOGO_MAP.items():
        if key in name_lower:
            return url
    return ""

def parse_youtube_txt():
    temp_channels = []
    if not os.path.exists(YOUTUBE_FILE): 
        print("⚠️ youtube.txt not found")
        return []
    
    print("📥 Processing youtube.txt...")
    try:
        with open(YOUTUBE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        
        current_title = ""
        current_logo = ""
        
        for line in lines:
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
                    
                    # --- AUTO LOGO LOGIC (Aggressive) ---
                    # If logo is empty OR just spaces, guess it
                    if not current_logo.strip():
                        current_logo = get_auto_logo(current_title)

                    entry = f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{current_logo}",{current_title}'
                    temp_channels.append(entry)
                    
                    # FIX PLAYBACK: Add User-Agent to temp channels too
                    if "http" in url and "|" not in url:
                        url += UA_HEADER
                        
                    temp_channels.append(url)
                    
                    # Reset
                    current_title = ""
                    current_logo = ""

    except Exception as e:
        print(f"⚠️ Error parsing youtube.txt: {e}")
    return temp_channels

def main():
    print("📥 Downloading Source Playlist...")
    try:
        r = requests.get(POCKET_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        source_lines = r.text.splitlines()
    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)

    # HEADER
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines = ["#EXTM3U"]
    final_lines.append(f"# Last Updated: {ist_now.strftime('%Y-%m-%d %H:%M:%S IST')}")
    final_lines.append("http://0.0.0.0")

    # (REMOVED PLACEHOLDER - CLEANER WILL CATCH ANY RESIDUE)

    # TRACKING VARIABLES
    seen_channels = set()
    zee_tamil_count = 0 
    
    # PROCESS CHANNELS
    current_buffer = []
    skip_this_channel = False
    
    for line in source_lines:
        line = line.strip()
        if not line: continue
        if line.startswith("#EXTM3U"): continue

        if line.startswith("#EXTINF"):
            if current_buffer and not skip_this_channel:
                final_lines.extend(current_buffer)
            current_buffer = []
            skip_this_channel = False
            
            group, name = get_group_and_name(line)
            clean_name = name.lower().strip()
            group_lower = group.lower()
            
            # --- CLEANER: Remove Placeholder Lines ---
            if "----" in name:
                skip_this_channel = True
                continue

            # --- ZEE TAMIL HD FIX ---
            if "zee tamil hd" in clean_name:
                zee_tamil_count += 1
                if zee_tamil_count == 2: pass 
                else:
                    skip_this_channel = True
                    continue 
            
            # --- STANDARD DEDUPLICATION ---
            else:
                clean_id = re.sub(r'[^a-z0-9]', '', clean_name)
                if clean_id in seen_channels:
                    skip_this_channel = True
                    continue
                else:
                    seen_channels.add(clean_id)
            
            # --- FILTERS ---
            if not should_keep_channel(group, name):
                skip_this_channel = True
                continue

            # --- GROUP MOVING ---
            new_group = group 
            if group_lower == "tamil": new_group = "Tamil SD"
            if group_lower == "local channels": new_group = "Tamil Extra"
            if "premium 24/7" in group_lower: new_group = "Tamil Extra"
            if "astro go" in group_lower: new_group = "Tamil Extra"

            # SPECIFIC MOVES
            if "j movies" in clean_name or "raj digital plus" in clean_name:
                new_group = "Tamil SD"
            if "rasi movies" in clean_name or "rasi hollywood" in clean_name:
                new_group = "Tamil Extra"
            if "dd sports" in clean_name:
                new_group = "Sports SD"
            if any(target.lower() == clean_name for target in [x.lower() for x in MOVE_TO_TAMIL_HD]): 
                new_group = "Tamil HD"

            # Apply New Group
            if new_group != group:
                if 'group-title="' in line:
                    line = re.sub(r'group-title="([^"]*)"', f'group-title="{new_group}"', line)
                else:
                    line = line.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{new_group}"')

        current_buffer.append(line)

        if not line.startswith("#"):
            # --- GLOBAL PLAYBACK FIX ---
            # Automatically attach User-Agent to ALL http links if missing.
            # This fixes the "None of the available extractors" error.
            if "http" in line and "|" not in line:
                line += UA_HEADER
                current_buffer[-1] = line
            
            # Specific check for Astro (just in case)
            if "astro" in current_buffer[0].lower() and "http" in line and "User-Agent" not in line:
                 line += UA_HEADER
                 current_buffer[-1] = line
            
            if not skip_this_channel:
                final_lines.extend(current_buffer)
            current_buffer = []
            skip_this_channel = False

    # ADD LIVE EVENTS
    print("📥 Adding Live Events...")
    final_lines.extend(fetch_live_events(FANCODE_URL))
    final_lines.extend(fetch_live_events(SONY_LIVE_URL))
    final_lines.extend(fetch_live_events(ZEE_LIVE_URL))

    # ADD TEMPORARY CHANNELS
    final_lines.extend(parse_youtube_txt())

    # SAVE
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print(f"\n✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()