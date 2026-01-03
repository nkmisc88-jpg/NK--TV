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

# SOURCES
POCKET_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html" 
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SONY_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
ZEE_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# FILTERS: DELETE THESE
BAD_KEYWORDS = ["pluto", "usa", "yupp", "sunnxt", "overseas"]

# ASTRO: KEEP ONLY THESE 6
ASTRO_KEEP = ["vinmeen", "thangathirai", "vaanavil", "vasantham", "vellithirai", "sports plus"]

# ==========================================
# GROUPING LOGIC
# ==========================================

def get_new_group(name, old_group):
    """Maps a channel to one of the specific groups requested."""
    n = name.lower()
    g = old_group.lower()

    # 1. SPECIFIC OVERRIDES (Fixes from previous requests)
    if "vijay takkar" in n: return "Tamil SD"
    if "cn hd+" in n: return "Kids"
    
    # 2. TAMIL CHANNELS
    if "tamil" in n or "tamil" in g:
        if "news" in n: return "Tamil News"
        if "hd" in n: return "Tamil HD"
        return "Tamil SD"

    # 3. SPORTS
    # Check for sport/cricket keywords
    if "sport" in n or "cricket" in n or "sport" in g:
        if "hd" in n: return "Sports HD"
        return "Sports SD"

    # 4. INFOTAINMENT
    info_keys = ["discovery", "nat geo", "animal planet", "history", "tlc", "travelxp", "bbc earth", "sony bbc"]
    if any(k in n for k in info_keys):
        if "hd" in n: return "Infotainment HD"
        return "Infotainment SD"

    # 5. KIDS
    kids_keys = ["cartoon", "nick", "disney", "pogo", "sonic", "hungama", "kids", "jetix", "animax", "super hungama"]
    if any(k in n for k in kids_keys):
        return "Kids"

    # 6. NEWS (English/Hindi)
    # We already caught Tamil News above, so this catches the rest
    if "news" in n or "ndtv" in n or "cnn" in n or "times now" in n or "republic" in n or "aaj tak" in n:
        return "English and Hindi News"

    # 7. LOCAL CHANNELS
    if "local" in g:
        return "Local Channels"

    # 8. OTHERS (Everything else falls here)
    return "Others"

# ==========================================
# MAIN SCRIPT
# ==========================================

def get_group_and_name(line):
    grp_match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
    group = grp_match.group(1).lower() if grp_match else ""
    name = line.split(",")[-1].strip()
    return group, name

def should_keep(group, name):
    # Filter Garbage
    clean_group = group.replace(" ", "")
    for bad in BAD_KEYWORDS:
        if bad in clean_group: return False
        
    # Filter Astro
    if "astro go" in group:
        return any(allowed in name.lower() for allowed in ASTRO_KEEP)
        
    return True

def fetch_live(url):
    items = []
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code == 200:
            for line in r.text.splitlines():
                if line.startswith("#EXTINF"):
                    # Force group to Live Events
                    line = re.sub(r'group-title="([^"]*)"', '', line)
                    line = re.sub(r'(#EXTINF:[-0-9]+)', r'\1 group-title="Live Events"', line)
                    items.append(line)
                elif not line.startswith("#") and line.strip():
                    items.append(line.strip())
    except: pass
    return items

def main():
    print("📥 Downloading Main Source...")
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
    current_props = []
    
    for i in range(len(source_lines)):
        line = source_lines[i].strip()
        if not line: continue
        
        # Keep License Keys
        if line.startswith("#KODIPROP") or line.startswith("#EXTVLCOPT"):
            current_props.append(line)
            continue

        if line.startswith("#EXTINF"):
            group, name = get_group_and_name(line)
            
            # 1. CHECK FILTER
            if not should_keep(group, name):
                current_props = [] # Discard keys
                continue
            
            # 2. DETERMINE NEW GROUP
            new_group = get_new_group(name, group)
            
            # 3. REWRITE LINE
            # Remove old group tag
            line = re.sub(r'group-title="([^"]*)"', '', line)
            # Insert new group tag
            line = re.sub(r'(#EXTINF:[-0-9]+)', f'\\1 group-title="{new_group}"', line)
            
            # 4. GET LINK
            link = ""
            if i + 1 < len(source_lines):
                link = source_lines[i+1].strip()
            
            if link and not link.startswith("#"):
                final_lines.extend(current_props)
                final_lines.append(line)
                final_lines.append(link)
            
            current_props = []

    # ADD LIVE EVENTS
    print("📥 Adding Live Events...")
    final_lines.extend(fetch_live(FANCODE_URL))
    final_lines.extend(fetch_live(SONY_LIVE_URL))
    final_lines.extend(fetch_live(ZEE_LIVE_URL))

    # ADD TEMPORARY (Simple Append)
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
