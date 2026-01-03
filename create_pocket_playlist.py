import requests
import datetime
import os
import sys

# ==========================================
# CONFIGURATION
# ==========================================
OUTPUT_FILE = "pocket_playlist.m3u"
YOUTUBE_FILE = "youtube.txt"
POCKET_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html" 

# GROUPS TO DELETE (Case insensitive)
BAD_GROUPS = ["pluto", "usa channels", "yupp tv", "sun nxt"]

def is_bad_group(line):
    """Checks if the group-title in the line matches any bad group."""
    line_lower = line.lower()
    for bad in BAD_GROUPS:
        # Check if group-title="bad" exists in the line
        if f'group-title="{bad}"' in line_lower or f'group-title="{bad}' in line_lower:
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
    # We buffer lines (props + extinf) until we hit a URL
    current_buffer = []
    
    for line in source_lines:
        line = line.strip()
        if not line: continue

        # Ignore the source's #EXTM3U header
        if line.startswith("#EXTM3U"):
            continue

        # Add line to buffer
        current_buffer.append(line)

        # If line is a URL (doesn't start with #), the channel block is complete
        if not line.startswith("#"):
            # Analyze the block to see if we should keep it
            keep_channel = True
            
            # Find the #EXTINF line in the buffer to check the group
            for buf_line in current_buffer:
                if buf_line.startswith("#EXTINF"):
                    if is_bad_group(buf_line):
                        keep_channel = False
                        break
            
            # If safe, add to final list
            if keep_channel:
                final_lines.extend(current_buffer)
            
            # Clear buffer for next channel
            current_buffer = []

    # Append Temporary Channels (if file exists)
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