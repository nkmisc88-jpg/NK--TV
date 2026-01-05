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
# Master Source (Arunjunan20)
POCKET_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html" 

# Live Event Sources
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SONY_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
ZEE_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# FILTERS (Remove these)
REMOVE_KEYWORDS = ["pluto", "usa", "yupp", "sunnxt", "overseas", "extras", "apac", "radio", "fm"]

# ASTRO ALLOW LIST (Only these 6)
ASTRO_KEEP = ["vinmeen", "thangathirai", "vaanavil", "vasantham", "vellithirai", "sports plus"]

# BROWSER HEADER (For playback fix)
UA_BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ==========================================
# 1. HELPER FUNCTIONS
# ==========================================

def clean_name_key(name):
    """Creates a unique ID for deduplication (e.g., 'Sun TV HD' -> 'suntvhd')"""
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name) # Remove brackets
    name = re.sub(r'[^a-zA-Z0-9]', '', name)    # Remove special chars
    return name.lower().strip()

def determine_group(name, old_group):
    """Sorts channels into your desired groups based on Name/Old Group."""
    n = name.lower()
    g = old_group.lower()

    # 1. SPECIAL MOVES
    if "astro" in n or "astro" in g: return "Tamil HD" # Move Astro to Tamil HD
    if "vijay takkar" in n: return "Tamil SD"
    if "cn hd+" in n: return "Kids"

    # 2. TAMIL LOGIC
    if "tamil" in n or "tamil" in g:
        if "news" in n: return "Tamil News"
        if "hd" in n: return "Tamil HD"
        return "Tamil SD"

    # 3. SPORTS LOGIC
    if "sport" in n or "cricket" in n or "sport" in g:
        if "hd" in n: return "Sports HD"
        return "Sports SD"

    # 4. INFOTAINMENT LOGIC
    info_keys = ["discovery", "nat geo", "animal planet", "history", "tlc", "travelxp", "bbc earth", "sony bbc"]
    if any(k in n for k in info_keys):
        if "hd" in n: return "Infotainment HD"
        return "Infotainment SD"

    # 5. KIDS LOGIC
    kids_keys = ["cartoon", "nick", "disney", "pogo", "sonic", "hungama", "kids", "jetix", "animax", "super hungama", "gubbare"]
    if any(k in n for k in kids_keys):
        return "Kids"

    # 6. NEWS LOGIC (English/Hindi)
    news_keys = ["news", "ndtv", "cnn", "times now", "republic", "aaj tak", "india today", "wion"]
    if any(k in n for k in news_keys):
        return "English and Hindi News"

    # 7. LOCAL CHANNELS
    if "local" in g: return "Local Channels"

    # 8. OTHERS
    return "Others"

def fetch_playlist_items(url, source_name, is_live_event=False):
    """Generic fetcher for M3U content."""
    items = []
    print(f"🌍 Fetching {source_name}...")
    try:
        r = requests.get(url, headers={"User-Agent": UA_BROWSER}, timeout=20)
        if r.status_code == 200:
            lines = r.text.splitlines()
            current_item = {}
            
            for line in lines:
                line = line.strip()
                if not line: continue
                
                if line.startswith("#EXTINF"):
                    # Extract Name
                    name = line.split(",")[-1].strip()
                    
                    # Extract Logo
                    logo = ""
                    logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                    if logo_match: logo = logo_match.group(1)
                    
                    # Extract Group
                    group = ""
                    grp_match = re.search(r'group-title="([^"]*)"', line)
                    if grp_match: group = grp_match.group(1)
                    
                    current_item = {
                        "name": name,
                        "logo": logo,
                        "group": "Live Events" if is_live_event else group,
                        "link": ""
                    }
                    
                elif not line.startswith("#"):
                    # This is the link
                    if current_item:
                        current_item["link"] = line
                        items.append(current_item)
                        current_item = {} # Reset
    except Exception as e:
        print(f"❌ Error fetching {source_name}: {e}")
    return items

def parse_youtube_txt():
    """Parses youtube.txt to handle Links, Names, or M3U entries."""
    items = []
    if not os.path.exists(YOUTUBE_FILE): return []
    
    print("🎥 Processing youtube.txt...")
    try:
        with open(YOUTUBE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()
            
        pending_name = "Temporary Channel"
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Case A: Header
            if line.startswith("#EXTINF"):
                # Extract name if possible
                parts = line.split(",")
                if len(parts) > 1: pending_name = parts[-1].strip()
                
            # Case B: Link
            elif line.startswith("http") or line.startswith("rtmp"):
                items.append({
                    "name": pending_name,
                    "logo": "",
                    "group": "Temporary Channels",
                    "link": line
                })
                pending_name = "Temporary Channel" # Reset
            
            # Case C: Name (Text line)
            elif not line.startswith("#"):
                pending_name = line
                
    except Exception as e:
        print(f"❌ Error parsing youtube.txt: {e}")
        
    return items

# ==========================================
# 2. MAIN EXECUTION
# ==========================================

def main():
    print("--- STARTING PLAYLIST GENERATION ---")
    
    # 1. FETCH ALL DATA
    pocket_items = fetch_playlist_items(POCKET_URL, "Pocket TV")
    live_items = []
    live_items.extend(fetch_playlist_items(FANCODE_URL, "Fancode", True))
    live_items.extend(fetch_playlist_items(SONY_LIVE_URL, "Sony Live", True))
    live_items.extend(fetch_playlist_items(ZEE_LIVE_URL, "Zee Live", True))
    temp_items = parse_youtube_txt()
    
    # 2. PROCESS POCKET ITEMS (Filter, Group, Deduplicate)
    processed_items = []
    seen_ids = set() # For deduplication
    
    print("⚙️  Processing & Grouping...")
    
    for item in pocket_items:
        name = item['name']
        group = item['group']
        clean_key = clean_name_key(name)
        
        # --- FILTERS ---
        # 1. Remove Duplicate Names
        if clean_key in seen_ids: continue
        
        # 2. Remove Bad Keywords (APAC, Extras, etc.)
        if any(bad in name.lower() or bad in group.lower() for bad in REMOVE_KEYWORDS):
            continue
            
        # 3. Astro Filter (Only allow the 6 specific ones)
        if "astro go" in group.lower():
            is_allowed = False
            for allowed in ASTRO_KEEP:
                if allowed in name.lower(): is_allowed = True; break
            if not is_allowed: continue
            
        # --- GROUPING ---
        final_group = determine_group(name, group)
        
        # --- LINK FIXING ---
        # Add User-Agent to Astro/Web links if missing
        link = item['link']
        if "http" in link and "User-Agent" not in link:
             # Only apply to Astro or known web streams to be safe
             if "astro" in name.lower() or "http" in link: 
                 if "|" not in link: # Don't break existing pipes
                     link += f"|User-Agent={UA_BROWSER}"
        
        # Add to list
        processed_items.append({
            "name": name,
            "logo": item['logo'],
            "group": final_group,
            "link": link
        })
        seen_ids.add(clean_key)

    # 3. COMBINE ALL (Pocket + Live + Temp)
    all_content = processed_items + live_items + temp_items
    
    # 4. WRITE TO FILE
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(f"# Updated on: {current_time} IST\n")
        
        # Write Empty Group Placeholders (Optional, forces order)
        GROUPS_ORDER = ["Tamil HD", "Tamil SD", "Tamil News", "Sports HD", "Sports SD", "Kids", "Infotainment HD", "Infotainment SD", "Live Events", "Temporary Channels"]
        for g in GROUPS_ORDER:
            f.write(f'#EXTINF:-1 group-title="{g}" tvg-logo="", ------------------\n')
            f.write("http://0.0.0.0\n")
            
        # Write Channels
        for item in all_content:
            line = f'#EXTINF:-1 group-title="{item["group"]}" tvg-logo="{item["logo"]}",{item["name"]}'
            f.write(line + "\n")
            f.write(item["link"] + "\n")
            
    print(f"🎉 DONE. Saved {len(all_content)} channels to {OUTPUT_FILE}")

if __name__ == "__main__":
    main() 