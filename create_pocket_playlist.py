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

# 1. CHANNELS TO MOVE TO "Tamil HD"
MOVE_TO_TAMIL_HD = [
    "Sun TV HD",
    "Star Vijay HD",
    "Colors Tamil HD",
    "Zee Tamil HD",
    "KTV HD",
    "Sun Music HD",
    "Jaya TV HD"
]

# 2. CHANNELS TO KEEP DUPLICATES FOR (Fix for broken links)
# If a channel is listed here, the script will NOT delete its duplicates.
# This lets you see all versions to find the working one.
ALLOW_DUPLICATES = [
    "Zee Tamil HD"
]

# 3. FILTERS (Global Deletions)
BAD_KEYWORDS = ["pluto", "usa", "yupp", "sunnxt", "overseas", "extras", "apac"]

# 4. ASTRO GO ALLOW LIST
ASTRO_KEEP = [
    "vinmeen", "thangathirai", "vaanavil", 
    "vasantham", "vellithirai", "sports plus"
]

# 5. LIVE EVENT SOURCES
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SONY_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
ZEE_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

def get_group_and_name(line):
    grp_match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
    group = grp_match.group(1).lower() if grp_match else ""
    name = line.split(",")[-1].strip()
    return group, name

def should_keep_channel(group, name):
    if "apac" in name.lower(): return False
    clean_group = group.replace(" ", "")
    for bad in BAD_KEYWORDS:
        if bad in clean_group: return False 
    if "astro go" in group:
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

    # TRACKING
    seen_channels = set()
    
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
            
            # --- DEDUPLICATION LOGIC ---
            clean_id = re.sub(r'[^a-z0-9]', '', name.lower())
            
            # Check if this channel is in our "Allow Duplicates" list
            is_exception = False
            for allowed in ALLOW_DUPLICATES:
                if allowed.lower() in name.lower():
                    is_exception = True
                    break
            
            if clean_id in seen_channels and not is_exception:
                # Duplicate found, AND it's not an exception -> DELETE
                skip_this_channel = True
                continue
            else:
                # First time seeing it OR it is an exception -> KEEP
                seen_channels.add(clean_id)
            
            # --- FILTERS ---
            if not should_keep_channel(group, name):
                skip_this_channel = True
                continue

            # --- GROUP MOVING ---
            new_group = group 
            if group == "tamil": new_group = "Tamil SD"
            if any(target.lower() == name.lower() for target in MOVE_TO_TAMIL_HD): new_group = "Tamil HD"
            if "astro go" in group: new_group = "Tamil HD"

            if new_group != group:
                if 'group-title="' in line:
                    line = re.sub(r'group-title="([^"]*)"', f'group-title="{new_group}"', line)
                else:
                    line = line.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{new_group}"')

        current_buffer.append(line)

        if not line.startswith("#"):
            if "astro" in current_buffer[0].lower() and "http" in line:
                 if "User-Agent" not in line:
                     if "|" in line: line = line.split("|")[0]
                     line += "|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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
    if os.path.exists(YOUTUBE_FILE):
        print("📥 Processing youtube.txt...")
        with open(YOUTUBE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            yt_lines = f.read().splitlines()
        pending_extinf = ""
        for line in yt_lines:
            line = line.strip()
            if not line: continue
            if line.startswith("#EXTINF"):
                if 'group-title="' in line:
                    line = re.sub(r'group-title="[^"]*"', 'group-title="Temporary Channels"', line)
                else:
                    if "," in line:
                         parts = line.split(",", 1)
                         line = f'{parts[0]} group-title="Temporary Channels",{parts[1]}'
                    else:
                         line += ' group-title="Temporary Channels"'
                pending_extinf = line
            elif line.startswith("http") or line.startswith("rtmp"):
                if pending_extinf: final_lines.append(pending_extinf)
                else: final_lines.append('#EXTINF:-1 group-title="Temporary Channels" tvg-logo="",Temporary Channel')
                final_lines.append(line)
                pending_extinf = "" 
            elif not line.startswith("#"):
                 pending_extinf = f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="",{line}'

    # SAVE
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print(f"\n✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
