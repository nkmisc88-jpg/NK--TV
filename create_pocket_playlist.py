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

# KEYWORDS TO DELETE
# We use partial names (e.g., "yupp" covers "YuppTV" and "Yupp TV")
BAD_KEYWORDS = ["pluto", "usa", "yupp", "sunnxt", "overseas"]

def should_skip(line):
    """Checks if the line contains any BAD_KEYWORDS in the group-title."""
    # 1. Extract the group title using Regex
    match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
    if match:
        group_name = match.group(1).lower().replace(" ", "") # Remove spaces (sun nxt -> sunnxt)
        
        # 2. Check if any bad keyword is inside the clean group name
        for bad in BAD_KEYWORDS:
            if bad in group_name:
                return True
    return False

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

    # Header with Timestamp
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

        # Ignore original header
        if line.startswith("#EXTM3U"): continue

        # Start of a new channel block (#EXTINF usually starts it)
        if line.startswith("#EXTINF"):
            # New channel started, check if previous buffer needs saving
            if current_buffer and not skip_this_channel:
                final_lines.extend(current_buffer)
            
            # Reset for new channel
            current_buffer = []
            skip_this_channel = False
            
            # CHECK IF WE SHOULD DELETE THIS NEW CHANNEL
            if should_skip(line):
                skip_this_channel = True

        # Add line to buffer
        current_buffer.append(line)

        # If it's a link (end of block), verify logic
        if not line.startswith("#"):
            # If we are NOT skipping, save the buffer now
            if not skip_this_channel:
                final_lines.extend(current_buffer)
            # Clear buffer immediately to avoid duplication
            current_buffer = []
            skip_this_channel = False

    # Append Temporary Channels
    if os.path.exists(YOUTUBE_FILE):
        print("   + Appending youtube.txt")
        with open(YOUTUBE_FILE, "r") as f:
            for l in f:
                if "title" in l.lower(): 
                    parts = l.split(":", 1)
                    if len(parts) > 1:
                        final_lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="",{parts[1].strip()}')
                elif l.startswith("http"): final_lines.append(l.strip())

    # Save to file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print(f"\n✅ DONE. Saved cleaned playlist to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
