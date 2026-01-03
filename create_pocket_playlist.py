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

# 1. CHANNELS TO COPY (Exact Name Match)
# These will appear in their ORIGINAL group AND "Tamil HD"
COPY_TO_TAMIL_HD = [
    "Sun TV HD",
    "Star Vijay HD",
    "Colors Tamil HD",
    "Zee Tamil HD",
    "KTV HD",
    "Sun Music HD",
    "Jaya TV HD"
]

# 2. FILTERS (Global Deletions)
BAD_KEYWORDS = ["pluto", "usa", "yupp", "sunnxt", "overseas"]

# 3. ASTRO GO ALLOW LIST
ASTRO_KEEP = [
    "vinmeen", "thangathirai", "vaanavil", 
    "vasantham", "vellithirai", "sports plus"
]

# 4. LIVE EVENT SOURCES
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SONY_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
ZEE_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

def get_group_and_name(line):
    grp_match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
    group = grp_match.group(1).lower() if grp_match else ""
    name = line.split(",")[-1].strip()
    return group, name

def should_keep_channel(group, name):
    clean_group = group.replace(" ", "")
    for bad in BAD_KEYWORDS:
        if bad in clean_group: return False 
            
    if "astro go" in group:
        is_allowed = False
        for allowed in ASTRO_KEEP:
            if allowed in name.lower():
                is_allowed = True
                break
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

    # PROCESS CHANNELS
    current_buffer = []
    skip_this_channel = False
    
    for line in source_lines:
        line = line.strip()
        if not line: continue
        if line.startswith("#EXTM3U"): continue

        if line.startswith("#EXTINF"):
            # --- PROCESS PREVIOUS BUFFER ---
            if current_buffer and not skip_this_channel:
                # 1. Add the Original Channel
                final_lines.extend(current_buffer)

                # 2. Check if we need to COPY this to Tamil HD
                # We look at the first line of the buffer (the EXTINF)
                extinf = current_buffer[0]
                _, ch_name = get_group_and_name(extinf)
                
                # Check if this channel is in our copy list
                if any(target.lower() == ch_name.lower() for target in COPY_TO_TAMIL_HD):
                    # Create the COPY
                    for buf_line in current_buffer:
                        if buf_line.startswith("#EXTINF"):
                            # Force the group to Tamil HD
                            if 'group-title="' in buf_line:
                                new_line = re.sub(r'group-title="([^"]*)"', 'group-title="Tamil HD"', buf_line)
                            else:
                                new_line = buf_line.replace("#EXTINF:-1", '#EXTINF:-1 group-title="Tamil HD"')
                            final_lines.append(new_line)
                        else:
                            # Add the link/props exactly as is
                            final_lines.append(buf_line)

            # --- START NEW CHANNEL ---
            current_buffer = []
            skip_this_channel = False
            
            group, name = get_group_and_name(line)
            if not should_keep_channel(group, name):
                skip_this_channel = True

        current_buffer.append(line)

        if not line.startswith("#"):
            # Astro Fix Logic (Add header if missing)
            if "astro" in current_buffer[0].lower() and "http" in line:
                 if "User-Agent" not in line:
                     if "|" in line: line = line.split("|")[0]
                     line += "|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                     current_buffer[-1] = line

    # FLUSH LAST CHANNEL
    if current_buffer and not skip_this_channel:
        final_lines.extend(current_buffer)
        # Check copy for last channel
        extinf = current_buffer[0]
        _, ch_name = get_group_and_name(extinf)
        if any(target.lower() == ch_name.lower() for target in COPY_TO_TAMIL_HD):
            for buf_line in current_buffer:
                if buf_line.startswith("#EXTINF"):
                    if 'group-title="' in buf_line:
                        new_line = re.sub(r'group-title="([^"]*)"', 'group-title="Tamil HD"', buf_line)
                    else:
                        new_line = buf_line.replace("#EXTINF:-1", '#EXTINF:-1 group-title="Tamil HD"')
                    final_lines.append(new_line)
                else:
                    final_lines.append(buf_line)

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
                if l.strip(): final_lines.append(l.strip())

    # SAVE
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print(f"\n✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
