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

# THE SOURCE (Arunjunan20)
POCKET_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html" 

# Browser Header (Only for Astro/Web channels)
UA_BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

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

    # Header with Timestamp (Forces GitHub to update)
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines = ["#EXTM3U"]
    final_lines.append(f"# Last Updated: {ist_now.strftime('%Y-%m-%d %H:%M:%S IST')}")
    final_lines.append("http://0.0.0.0")

    # PROCESS LINES
    for i in range(len(source_lines)):
        line = source_lines[i].strip()
        if not line: continue

        # 1. LICENSE KEYS (Keep exactly as is)
        if line.startswith("#KODIPROP") or line.startswith("#EXTVLCOPT"):
            final_lines.append(line)
            continue

        # 2. INFO LINE (#EXTINF)
        if line.startswith("#EXTINF"):
            # FIX: "Raw Github" Group Name
            # If group-title is missing or looks like a URL, force it to "Others"
            if 'group-title="' not in line or 'group-title="http' in line:
                # Remove existing bad group if any
                line = re.sub(r'group-title="[^"]*"', '', line)
                # Insert clean group
                line = re.sub(r'(#EXTINF:[-0-9]+)', r'\1 group-title="Others"', line)
            
            final_lines.append(line)
            continue

        # 3. LINKS (URLs)
        if not line.startswith("#"):
            # FIX: Astro Playback
            # Only add headers if it's Astro and doesn't have them yet
            # We look at the PREVIOUS line to check the name
            prev_line = source_lines[i-1] if i > 0 else ""
            
            if "astro" in prev_line.lower() and "http" in line:
                # If no User-Agent is present, add the browser one
                if "User-Agent" not in line:
                    if "|" in line: line = line.split("|")[0] # Clear old params
                    line += f"|User-Agent={UA_BROWSER}"
            
            final_lines.append(line)

    # 4. ADD TEMPORARY CHANNELS (If any)
    if os.path.exists(YOUTUBE_FILE):
        with open(YOUTUBE_FILE, "r") as f:
            for l in f:
                if "title" in l.lower(): 
                    parts = l.split(":", 1)
                    if len(parts) > 1:
                        final_lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="",{parts[1].strip()}')
                elif l.startswith("http"): final_lines.append(l.strip())

    # SAVE
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print(f"\n✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
