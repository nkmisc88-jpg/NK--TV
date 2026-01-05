import requests
import re
import datetime
import os
import sys
from collections import Counter

# ==========================================
# CONFIGURATION
# ==========================================
OUTPUT_FILE = "pocket_playlist.m3u"
YOUTUBE_FILE = "youtube.txt"
POCKET_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html" 

# 1. MOVE TO TAMIL HD
MOVE_TO_TAMIL_HD = [
    "Sun TV HD", "Star Vijay HD", "Colors Tamil HD", 
    "Zee Tamil HD", "KTV HD", "Sun Music HD", "Jaya TV HD",
    "Zee Thirai HD", "Vijay Super HD"
]

# 2. MOVE TO TAMIL NEWS
MOVE_TO_TAMIL_NEWS = [
    "Sun News", "News7 Tamil", "Thanthi TV", "Raj News 24x7", 
    "Tamil Janam", "Jaya Plus", "M Nadu", "News J", 
    "News18 Tamil Nadu", "News Tamil 24x7", "Win TV", 
    "Zee Tamil News", "Polimer News", "Puthiya Thalaimurai", 
    "Seithigal TV", "Sathiyam TV", "MalaiMurasu Seithigal"
]

# 3. MOVE TO INFOTAINMENT SD
MOVE_TO_INFOTAINMENT_SD = [
    "GOOD TiMES", "Food Food"
]

# 4. SPORTS HD LIST
SPORTS_HD_KEEP = [
    "Star Sports 1 HD", "Star Sports 2 HD", 
    "Star Sports 1 Tamil HD", "Star Sports 2 Tamil HD", 
    "Star Sports Select 1 HD", "Star Sports Select 2 HD", 
    "SONY TEN 1 HD", "SONY TEN 2 HD", "SONY TEN 5 HD"
]

# 5. INFOTAINMENT KEYWORDS (For SD Group)
INFOTAINMENT_KEYWORDS = [
    "discovery", "animal planet", "nat geo", "history tv", 
    "tlc", "bbc earth", "sony bbc", "fox life", "travelxp"
]

# 6. FILTERS
BAD_KEYWORDS = ["pluto", "usa", "yupp", "sunnxt", "overseas", "extras", "apac", "fashion"]

# 7. ASTRO KEEP LIST
ASTRO_KEEP = [
    "vinmeen", "thangathirai", "vaanavil", 
    "vasantham", "vellithirai", "sports plus"
]

# 8. LIVE EVENTS
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SONY_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
ZEE_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# 9. AUTO LOGO MAP
LOGO_MAP = {
    "willow": "https://i.imgur.com/39s1fL3.png",
    "fox": "https://i.imgur.com/39s1fL3.png",
    "star sports": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/Star_Sports_network.svg/1200px-Star_Sports_network.svg.png",
    "sony": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Sony_LIV_logo.svg/512px-Sony_LIV_logo.svg.png",
    "zee": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Zee5_logo.svg/512px-Zee5_logo.svg.png",
    "sun": "https://upload.wikimedia.org/wikipedia/en/thumb/8/80/Sun_TV_Network_Logo.png/220px-Sun_TV_Network_Logo.png",
    "colors": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Colors_TV_Logo.png/800px-Colors_TV_Logo.png",
    "astro": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Astro_logo.svg/800px-Astro_logo.svg.png",
    "fancode": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/54/FanCode_Logo.png/800px-FanCode_Logo.png",
    "discovery": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Discovery_Channel_logo.svg/800px-Discovery_Channel_logo.svg.png",
    "history": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/History_Logo.svg/800px-History_Logo.svg.png"
}

# HEADERS
UA_HEADER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def get_group_and_name(line):
    grp_match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
    group = grp_match.group(1).strip() if grp_match else ""
    name = line.split(",")[-1].strip()
    return group, name

def should_keep_channel(group, name):
    if "----" in name: return False
    if "apac" in name.lower(): return False
    
    clean_group = group.lower().replace(" ", "")
    for bad in BAD_KEYWORDS:
        if bad in clean_group or bad in name.lower(): return False 
            
    if "astro go" in group.lower():
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

def get_auto_logo(channel_name):
    name_lower = channel_name.lower()
    for key, url in LOGO_MAP.items():
        if key in name_lower:
            return url
    return ""

def parse_youtube_txt():
    temp_channels = []
    if not os.path.exists(YOUTUBE_FILE): return []
    
    print("📥 Processing youtube.txt...")
    try:
        with open(YOUTUBE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        
        current_title = ""
        current_logo = ""
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            if line.lower().startswith("title"):
                parts = line.split(":", 1)
                if len(parts) > 1: current_title = parts[1].strip()
            
            elif line.lower().startswith("logo"):
                parts = line.split(":", 1)
                if len(parts) > 1: current_logo = parts[1].strip()

            elif line.lower().startswith("link") or line.startswith("http"):
                url = line
                if line.lower().startswith("link"):
                    parts = line.split(":", 1)
                    if len(parts) > 1: url = parts[1].strip()
                
                if url.startswith("http") or url.startswith("rtmp"):
                    if not current_title: current_title = "Temporary Channel"
                    
                    if not current_logo or len(current_logo) < 5:
                        current_logo = get_auto_logo(current_title)

                    entry = f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{current_logo}",{current_title}'
                    temp_channels.append(entry)
                    
                    if "http" in url and "|" not in url:
                        url += f"|User-Agent={UA_HEADER}"
                    temp_channels.append(url)
                    
                    current_title = ""
                    current_logo = ""
    except: pass
    return temp_channels

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

    # 1. PARSE ALL CHANNELS FIRST (Fixes Missing Channel Bug)
    all_channels = []
    current_buffer = []
    
    for line in source_lines:
        line = line.strip()
        if not line: continue
        if line.startswith("#EXTM3U"): continue
        
        if line.startswith("#EXTINF"):
            if current_buffer:
                 # Check if buffer has link
                 if len(current_buffer) >= 2:
                     all_channels.append(current_buffer)
            current_buffer = []
            
        current_buffer.append(line)
    
    # Add last channel
    if current_buffer and len(current_buffer) >= 2:
        all_channels.append(current_buffer)

    print(f"✅ Parsed {len(all_channels)} raw channels.")

    # 2. COUNT DUPLICATES
    # We create a "clean ID" for every channel to count them
    channel_ids = []
    for ch in all_channels:
        _, name = get_group_and_name(ch[0])
        clean_id = re.sub(r'[^a-z0-9]', '', name.lower().strip())
        channel_ids.append(clean_id)
    
    id_counts = Counter(channel_ids)
    seen_counters = Counter()

    # 3. PROCESS AND FILTER
    for i, channel_data in enumerate(all_channels):
        extinf = channel_data[0]
        link = channel_data[1]
        
        group, name = get_group_and_name(extinf)
        clean_name = name.lower().strip()
        clean_id = channel_ids[i]
        
        # Increment seen count
        seen_counters[clean_id] += 1
        current_count = seen_counters[clean_id]
        total_count = id_counts[clean_id]

        # --- SMART DEDUPLICATION LOGIC ---
        keep_this = False
        
        if "zee tamil hd" in clean_name or "zee zest hd" in clean_name:
            # Special Rule: Keep 2nd copy if exists. If only 1, keep 1st.
            if total_count >= 2:
                if current_count == 2: keep_this = True
            else:
                keep_this = True # Only 1 exists, keep it!
        else:
            # Standard Rule: Keep 1st copy only
            if current_count == 1: keep_this = True
        
        if not keep_this: continue

        # --- FILTERS ---
        if not should_keep_channel(group, name): continue

        # --- LOGO FIX ---
        new_logo = get_auto_logo(clean_name)
        if new_logo:
            if 'tvg-logo="' in extinf:
                extinf = re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{new_logo}"', extinf)
            else:
                extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-logo="{new_logo}"')

        # --- GROUP RENAMING ---
        group_lower = group.lower()
        new_group = group 
        
        if group_lower == "tamil": new_group = "Tamil SD"
        if group_lower == "local channels": new_group = "Tamil Extra"
        if "premium 24/7" in group_lower: new_group = "Tamil Extra"
        if "astro go" in group_lower: new_group = "Tamil Extra"
        if group_lower == "sports": new_group = "Sports Extra"
        
        # NEW: Entertainment -> Others
        if "entertainment" in group_lower: new_group = "Others"

        if "news" in group_lower and "tamil" not in group_lower: new_group = "English and Hindi News"
        if "infotainment" in group_lower: new_group = "Infotainment HD"

        # Specific Moves
        if "j movies" in clean_name or "raj digital plus" in clean_name: new_group = "Tamil SD"
        if "rasi movies" in clean_name or "rasi hollywood" in clean_name: new_group = "Tamil Extra"
        if "dd sports" in clean_name: new_group = "Sports Extra"
        
        if any(target.lower() in clean_name for target in MOVE_TO_INFOTAINMENT_SD): new_group = "Infotainment SD"
        if any(k in clean_name for k in INFOTAINMENT_KEYWORDS):
            if "hd" not in clean_name: new_group = "Infotainment SD"

        for target in SPORTS_HD_KEEP:
            if target.lower() in clean_name: new_group = "Sports HD"; break
        
        if any(target.lower() == clean_name for target in [x.lower() for x in MOVE_TO_TAMIL_NEWS]): new_group = "Tamil News"
        if any(target.lower() == clean_name for target in [x.lower() for x in MOVE_TO_TAMIL_HD]): new_group = "Tamil HD"

        # Apply Group Change
        if new_group != group:
            if 'group-title="' in extinf:
                extinf = re.sub(r'group-title="([^"]*)"', f'group-title="{new_group}"', extinf)
            else:
                extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{new_group}"')
        
        # --- PLAYBACK FIX ---
        if "http" in link and "|" not in link:
            link += f"|User-Agent={UA_HEADER}"
        
        # Colors Tamil HD Specific Fix
        if "colors tamil hd" in clean_name:
             if "Content-Type" not in link:
                 link += "&Content-Type=application/dash+xml"

        # Write to final list
        final_lines.append(extinf)
        final_lines.append(link)

    # ADD LIVE & TEMP
    print("📥 Adding Live Events...")
    final_lines.extend(fetch_live_events(FANCODE_URL))
    final_lines.extend(fetch_live_events(SONY_LIVE_URL))
    final_lines.extend(fetch_live_events(ZEE_LIVE_URL))
    final_lines.extend(parse_youtube_txt())

    # SAVE
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print(f"\n✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
