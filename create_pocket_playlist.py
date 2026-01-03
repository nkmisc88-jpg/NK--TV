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

# 1. MAIN SOURCE
POCKET_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html" 

# 2. LIVE EVENT SOURCES
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SONY_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
ZEE_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# 3. FILTERS (Global Deletions)
BAD_KEYWORDS = ["pluto", "usa", "yupp", "sunnxt", "overseas"]

# 4. ASTRO GO ALLOW LIST
ASTRO_KEEP = [
    "vinmeen", "thangathirai", "vaanavil", 
    "vasantham", "vellithirai", "sports plus"
]

# 5. GROUP RENAMES (Case Insensitive)
# Format: "Old Name": "New Name"
GROUP_RENAMES = {
    "tamil": "Tamil HD"
}

def get_group_and_name(line):
    """Extracts group-title and channel name from #EXTINF line."""
    grp_match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
    group = grp_match.group(1).strip() if grp_match else ""
    name = line.split(",")[-1].strip()
    return group, name

def should_keep_channel(group, name):
    """Decides whether to keep or skip a channel based on rules."""
    group_lower = group.lower()
    name_lower = name.lower()
    
    # RULE 1: Global Deletions
    # Remove spaces to match "Sun NXT" as "sunnxt"
    clean_group = group_lower.replace(" ", "")
    for bad in BAD_KEYWORDS:
        if bad in clean_group:
            return False 
            
    # RULE 2: Astro GO Filter
    if "astro go" in group_lower:
        is_allowed = False
        for allowed in ASTRO_KEEP:
            if allowed in name_lower:
                is_allowed = True
                break
        if not is_allowed:
            return False 

    return True

def fetch_live_events(url, source_name):
    """Fetches a playlist and forces the group to 'Live Events'."""
    events = []
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code == 200:
            lines = r.text.splitlines()
            for line in lines:
                line = line.strip()
                if not line: continue
                
                if line.startswith("#EXTINF"):
                    # Remove existing group
                    line = re.sub(r'group-title="([^"]*)"', '', line)
                    # Insert new group
                    line = re.sub(r'(#EXTINF:[-0-9]+)', r'\1 group-title="Live Events"', line)
                    events.append(line)
                elif not line.startswith("#"):
                    events.append(line)
    except: pass
    return events

def main():
    # 1. DOWNLOAD MAIN SOURCE
    print("📥 Downloading Main Source...")
    try:
        r = requests.get(POCKET_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if r.status_code != 200:
            print(f"❌ Error: Status {r.status_code}")
            sys.exit(1)
        source_lines = r.text.splitlines()
        print(f"✅ Downloaded {len(source_lines)} lines.")
    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)

    # 2. HEADER
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines = ["#EXTM3U"]
    final_lines.append(f"# Last Updated: {ist_now.strftime('%Y-%m-%d %H:%M:%S IST')}")
    final_lines.append("http://0.0.0.0")

    # 3. PROCESS MAIN CHANNELS
    current_buffer = []
    skip_this_channel = False
    
    for line in source_lines:
        line = line.strip()
        if not line: continue
        if line.startswith("#EXTM3U"): continue

        if line.startswith("#EXTINF"):
            # Flush previous buffer
            if current_buffer and not skip_this_channel:
                final_lines.extend(current_buffer)
            current_buffer = []
            skip_this_channel = False
            
            group, name = get_group_and_name(line)
            
            # CHECK FILTERS
            if not should_keep_channel(group, name):
                skip_this_channel = True
            
            # APPLY RENAME
            # If the group matches our rename list, change it
            if group.lower() in GROUP_RENAMES:
                new_group = GROUP_RENAMES[group.lower()]
                # Replace the old group in the string
                line = line.replace(f'group-title="{group}"', f'group-title="{new_group}"')

        current_buffer.append(line)

        # End of block (Link)
        if not line.startswith("#"):
            # FIX: Astro Playback (Add header if missing)
            if "astro" in current_buffer[0].lower() and "http" in line:
                 if "User-Agent" not in line:
                     if "|" in line: line = line.split("|")[0]
                     line += "|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                     current_buffer[-1] = line

            if not skip_this_channel:
                final_lines.extend(current_buffer)
            current_buffer = []
            skip_this_channel = False

    # 4. ADD LIVE EVENTS
    print("📥 Adding Live Events...")
    final_lines.extend(fetch_live_events(FANCODE_URL, "Fancode"))
    final_lines.extend(fetch_live_events(SONY_LIVE_URL, "Sony Live"))
    final_lines.extend(fetch_live_events(ZEE_LIVE_URL, "Zee Live"))

    # 5. ADD TEMPORARY CHANNELS
    if os.path.exists(YOUTUBE_FILE):
        print("📥 Appending youtube.txt...")
        with open(YOUTUBE_FILE, "r") as f:
            yt_lines = f.readlines()
        
        for i in range(len(yt_lines)):
            line = yt_lines[i].strip()
            if line.startswith("http") or line.startswith("rtmp"):
                name = "Temporary Channel"
                if i > 0:
                    prev = yt_lines[i-1].strip()
                    if prev and not prev.startswith("http") and not prev.startswith("#"):
                        name = prev
                final_lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="",{name}')
                final_lines.append(line)

    # SAVE
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print(f"\n✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
