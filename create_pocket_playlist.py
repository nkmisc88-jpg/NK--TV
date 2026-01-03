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

# ONLY ONE SOURCE (The one you know works)
POCKET_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html" 

# Headers for Astro/Web channels
UA_BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ==========================================
# LOGIC
# ==========================================

def get_source_data():
    print("📥 Downloading Source Playlist...")
    items = []
    try:
        r = requests.get(POCKET_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if r.status_code != 200:
            print(f"❌ Critical Error: Status {r.status_code}")
            sys.exit(1)

        lines = r.text.splitlines()
        current_props = []
        
        for i in range(len(lines)):
            line = lines[i].strip()
            if not line: continue
            
            # 1. Capture License Keys (Do not touch these!)
            if line.startswith("#KODIPROP") or line.startswith("#EXTVLCOPT"):
                current_props.append(line)
                continue

            # 2. Capture Channel Info
            if line.startswith("#EXTINF"):
                # Extract Group Title
                grp = ""
                m_grp = re.search(r'group-title="([^"]*)"', line)
                if m_grp: grp = m_grp.group(1)

                # SANITIZE GROUP: Fix the "Raw Github" error
                # If group is empty OR looks like a URL, force it to "Others"
                if not grp or "http" in grp or "github" in grp:
                    grp = "Others"

                # 3. Capture Link
                link = ""
                if i + 1 < len(lines):
                    pot_link = lines[i+1].strip()
                    if pot_link and not pot_link.startswith("#"):
                        link = pot_link

                if link:
                    items.append({
                        'line_raw': line, # Keep original line info
                        'group_clean': grp,
                        'link': link,
                        'props': current_props
                    })
                
                current_props = [] # Reset for next channel
        
        print(f"✅ Source Loaded: {len(items)} channels.")
        return items

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def main():
    source_items = get_source_data()
    
    # Header
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines = ["#EXTM3U"]
    final_lines.append(f"# Last Updated: {ist_now.strftime('%Y-%m-%d %H:%M:%S IST')}")
    final_lines.append("http://0.0.0.0")

    # PROCESS EVERY SINGLE CHANNEL
    for item in source_items:
        # 1. Add License Keys (if any)
        final_lines.extend(item['props'])

        # 2. Rebuild #EXTINF Line with Clean Group
        # We strip the old group-title and add our clean one
        old_line = item['line_raw']
        old_line = re.sub(r'group-title="[^"]*"', '', old_line) # Remove old group
        # Insert new group safely
        new_line = re.sub(r'(#EXTINF:[-0-9]+)', f'\\1 group-title="{item["group_clean"]}"', old_line)
        final_lines.append(new_line)

        # 3. Add Link (With Astro Fix)
        link = item['link']
        
        # FIX: If it is Astro/Cinemania and has NO license keys, it likely needs a Browser Header
        # We check "http" to ensure we don't break local files or rtmp
        is_jio_zee = len(item['props']) > 0
        if not is_jio_zee and "http" in link:
             # Check if we need to fix Astro or Web channels
             if "astro" in new_line.lower() or "cinema" in new_line.lower():
                 if "|" in link: link = link.split("|")[0] # Clean existing params
                 link += f"|User-Agent={UA_BROWSER}"
        
        final_lines.append(link)

    # 4. Add Temporary Channels (Youtube.txt)
    if os.path.exists(YOUTUBE_FILE):
        with open(YOUTUBE_FILE, "r") as f:
            for l in f:
                if "title" in l.lower(): 
                    parts = l.split(":", 1)
                    if len(parts) > 1:
                        final_lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="",{parts[1].strip()}')
                elif l.startswith("http"): final_lines.append(l.strip())

    # Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print(f"\n✅ DONE. Saved to {OUTPUT_FILE} ({len(source_items)} channels)")

if __name__ == "__main__":
    main()
