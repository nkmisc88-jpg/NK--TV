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

# GROUPS TO DELETE (Case Insensitive)
BAD_KEYWORDS = ["pluto", "usa", "yupp", "sunnxt", "overseas"]

# ASTRO GO ALLOW LIST (Only keep these 6)
ASTRO_KEEP = [
    "vinmeen", "thangathirai", "vaanavil", 
    "vasantham", "vellithirai", "sports plus"
]

# LIVE EVENT SOURCES
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SONY_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
ZEE_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

def get_group_and_name(line):
    """Extracts group-title and channel name from #EXTINF line."""
    grp_match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
    group = grp_match.group(1).lower() if grp_match else ""
    name = line.split(",")[-1].lower().strip()
    return group, name

def should_keep_channel(extinf_line):
    """Decides whether to keep or skip a channel based on rules."""
    group, name = get_group_and_name(extinf_line)
    
    # RULE 1: Global Deletions
    clean_group = group.replace(" ", "")
    for bad in BAD_KEYWORDS:
        if bad in clean_group:
            return False 
            
    # RULE 2: Astro GO Filter
    if "astro go" in group:
        is_allowed = False
        for allowed in ASTRO_KEEP:
            if allowed in name:
                is_allowed = True
                break
        if not is_allowed:
            return False 

    return True

def fetch_live_events(url):
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
                    # Force group to Live Events
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
        if r.status_code != 200:
            print(f"❌ Error: Status {r.status_code}")
            sys.exit(1)
        source_lines = r.text.splitlines()
        print(f"✅ Downloaded {len(source_lines)} lines.")
    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)

    # Header
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines = ["#EXTM3U"]
    final_lines.append(f"# Last Updated: {ist_now.strftime('%Y-%m-%d %H:%M:%S IST')}")
    final_lines.append("http://0.0.0.0")

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
            
            if not should_keep_channel(line):
                skip_this_channel = True

        current_buffer.append(line)

        if not line.startswith("#"):
            # FIX: Astro Playback Header
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
        print("📥 Appending youtube.txt...")
        with open(YOUTUBE_FILE, "r") as f:
            for l in f:
                l = l.strip()
                if l: final_lines.append(l)

    # SAVE
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print(f"\n✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
