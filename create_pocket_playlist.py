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

# 1. GROUPS TO DELETE ENTIRELY
BAD_KEYWORDS = ["pluto", "usa", "yupp", "sunnxt", "overseas"]

# 2. ASTRO GO ALLOW LIST (Only keep these 6)
ASTRO_KEEP = [
    "vinmeen", 
    "thangathirai", 
    "vaanavil", 
    "vasantham", 
    "vellithirai", 
    "sports plus"
]

def get_group_and_name(line):
    """Extracts group-title and channel name from #EXTINF line."""
    # Extract Group
    grp_match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
    group = grp_match.group(1).lower() if grp_match else ""
    
    # Extract Name (after the last comma)
    name = line.split(",")[-1].lower().strip()
    
    return group, name

def should_keep_channel(extinf_line):
    """Decides whether to keep or skip a channel based on rules."""
    group, name = get_group_and_name(extinf_line)
    
    # RULE 1: Global Deletions (Pluto, Yupp, etc.)
    # We check if the group name contains any bad keyword
    # We remove spaces to match "Sun NXT" as "sunnxt"
    clean_group = group.replace(" ", "")
    for bad in BAD_KEYWORDS:
        if bad in clean_group:
            return False # DELETE
            
    # RULE 2: Astro GO Filter (Keep only 6 specific channels)
    if "astro go" in group:
        # Check if the name matches any of our allowed list
        is_allowed = False
        for allowed in ASTRO_KEEP:
            if allowed in name:
                is_allowed = True
                break
        
        if not is_allowed:
            return False # DELETE (It's Astro GO but not one of the 6)

    # If it passed all checks, KEEP it
    return True

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

        # Ignore source header
        if line.startswith("#EXTM3U"): continue

        # Start of a new channel block
        if line.startswith("#EXTINF"):
            # 1. Save previous channel if valid
            if current_buffer and not skip_this_channel:
                final_lines.extend(current_buffer)
            
            # 2. Reset for new channel
            current_buffer = []
            skip_this_channel = False
            
            # 3. Check logic
            if not should_keep_channel(line):
                skip_this_channel = True

        # Add line to buffer
        current_buffer.append(line)

        # End of block (Link)
        if not line.startswith("#"):
            # If valid, save now
            if not skip_this_channel:
                final_lines.extend(current_buffer)
            # Clear buffer
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

    # Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print(f"\n✅ DONE. Saved cleaned playlist to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
