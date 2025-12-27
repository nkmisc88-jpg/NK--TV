import requests
import re
import datetime
import os
import json

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"
youtube_file = "youtube.txt"
reference_file = "jiotv_playlist.m3u.m3u8"
output_file = "playlist.m3u"

# EXTERNAL SOURCES
base_url = "http://192.168.0.146:5350/live" 
backup_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# REMOVAL LIST
REMOVE_KEYWORDS = [
    "sony ten", "sonyten", "sony sports ten", 
    "star sports 1", "star sports 2",
    "zee thirai",                
    "star sports 1 kannada hd"   
]

FORCE_BACKUP_KEYWORDS = [
    "star", "zee", "vijay", "asianet", "suvarna", "maa", "hotstar", "sony", "set", "sab",
    "nick", "cartoon", "pogo", "disney", "hungama", "sonic", "discovery", "nat geo", 
    "history", "tlc", "animal planet", "travelxp", "bbc earth", "movies now", "mnx", "romedy", "mn+", "pix",
    "&pictures", "sports", "ten"
]

NAME_OVERRIDES = {
    "star sports 2 hindi hd": "Sports18 1 HD",
    "star sports 2 tamil hd": "Star Sports 2 Tamil HD",
    "zee tamil": "Zee Tamil HD",
    "nat geo hd": "National Geographic HD",
    "star sports 1 hd": "Star Sports HD1",
    "star sports 2 hd": "Star Sports HD2",
    "star sports 1 hindi hd": "Star Sports HD1 Hindi",
    "sony sports ten 1 hd": "sony ten 1",
    "sony sports ten 2 hd": "sony ten 2",
    "sony sports ten 3 hd": "sony ten 3",
    "sony sports ten 4 hd": "sony ten 4",
    "sony sports ten 5 hd": "sony ten 5",
    "nat geo wild hd": "nat geo wild",
    "discovery hd world": "discovery channel",
    "history tv18 hd": "history",
    "cartoon network hd+ english": "cartoon network",
    "nick hd+": "nick",
    "star movies hd": "star movies",
    "sony pix hd": "sony pix"
}

# ==========================================
# SMART LIVE SCRAPER (The Magic Logic)
# ==========================================

def get_live_video_id(url):
    """
    Finds the CURRENT Live Video ID from a Channel URL.
    1. Tries direct scraping (Fast).
    2. If that fails (Geo-block), tries Piped API (Proxy).
    """
    # Strategy 1: Direct Scrape (Works for Indian Channels)
    try:
        session = requests.Session()
        session.cookies.set('CONSENT', 'YES+cb', domain='.youtube.com')
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
        
        # If user gave a channel/live link, we fetch that page
        if "/live" in url:
            print(f"      ...Scanning Channel for Live ID: {url}")
            response = session.get(url, headers=headers, allow_redirects=True)
            
            # Check for redirect to a specific video
            if "watch?v=" in response.url:
                vid_id = response.url.split("v=")[1].split("&")[0]
                return vid_id
            
            # If no redirect, look in HTML
            match = re.search(r'"videoId":"(.*?)"', response.text)
            if match: return match.group(1)

    except: pass
    
    # Strategy 2: Piped API (The "VPN Logic" for Blocked Channels)
    try:
        print("      ...Direct scan failed. Trying Piped Proxy...")
        # Extract handle or channel ID
        if "@" in url:
            handle = url.split("@")[1].split("/")[0]
            api_url = f"https://pipedapi.kavin.rocks/user/{handle}"
        else:
            return None # Cannot proceed without handle

        resp = requests.get(api_url, timeout=10).json()
        # Look for a live stream in the channel data
        if resp.get('livestream'):
            return resp['livestream']['id']
    except: pass

    return None

def parse_youtube_txt():
    """
    Parses youtube.txt.
    - Handles Channel Links (@channel/live) -> Auto-Updates ID
    - Handles Geo-Blocking via Proxy Mode
    """
    new_entries = []
    
    if not os.path.exists(youtube_file):
        print(f"❌ Error: {youtube_file} NOT FOUND.")
        return []

    print(f"📂 Reading {youtube_file}...")
    
    with open(youtube_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_entry = {}
    
    for line in lines:
        line = line.strip()
        if not line: 
            if 'link' in current_entry:
                new_entries.append(process_entry(current_entry))
            current_entry = {} 
            continue

        if ':' in line:
            parts = line.split(':', 1)
            key = parts[0].strip().lower()
            val = parts[1].strip()
            current_entry[key] = val
    
    if 'link' in current_entry:
        new_entries.append(process_entry(current_entry))

    print(f"✅ Live Events: Parsed {len(new_entries)} entries.")
    return new_entries

def process_entry(data):
    title = data.get('title', 'Unknown Event')
    logo = data.get('logo', '')
    link = data.get('link', '')
    vpn_req = data.get('vpn required', 'no').lower()
    mode = data.get('worker', 'auto').lower()

    if "yes" in vpn_req: title = f"{title} [VPN]"
    final_link = link

    # --- AUTO-UPDATE LOGIC ---
    if "youtube.com" in link or "youtu.be" in link:
        video_id = None
        
        # 1. If it's a Channel Live Link, FIND the ID first
        if "/live" in link or "channel/" in link or "@" in link:
             video_id = get_live_video_id(link)
             if video_id:
                 print(f"   ✅ Found Live ID: {video_id} for {title}")
             else:
                 print(f"   ⚠️ No Live Stream found for {title}")
                 return "" # Skip offline channels
        
        # 2. If it's already a specific video link
        elif "v=" in link or "youtu.be" in link:
            match = re.search(r'(?:v=|\/live\/|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', link)
            if match: video_id = match.group(1)

        if video_id:
            # --- GENERATE LINK BASED ON MODE ---
            if "proxy" in mode:
                # Geo-Blocked? Use Piped Stream directly (Built-in VPN)
                final_link = f"https://pipedapi.kavin.rocks/streams/{video_id}"
            elif "no" in mode:
                # Direct Link
                final_link = f"https://www.youtube.com/watch?v={video_id}"
            else:
                # Default: Jitendra Worker (Best for Stable Live)
                final_link = f"https://youtube.jitendraunatti.workers.dev/wanda.m3u8?id={video_id}"

    return f'#EXTINF:-1 group-title="Youtube and live events" tvg-logo="{logo}",{title}\n{final_link}'

# ==========================================
# HELPER FUNCTIONS (UNCHANGED)
# ==========================================

def clean_name_key(name):
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

def get_significant_words(name):
    name = name.lower().replace("sports18", "sports 18") 
    name = re.sub(r'\b(hd|sd|tv|channel|network|india|world|english|tamil|hindi|telugu|kannada|movies|cinema)\b', '', name)
    words = re.findall(r'[a-z0-9]+', name)
    return set(words)

def fuzzy_match_logic(target_name, map_keys):
    target_words = get_significant_words(target_name)
    if not target_words: return None
    for key in map_keys:
        key_lower = key.lower().replace("sports18", "sports 18")
        key_words = set(re.findall(r'[a-z0-9]+', key_lower))
        if target_words.issubset(key_words): return key
    return None

def find_best_backup_link(original_name, backup_map):
    if "star sports 2 tamil hd" in original_name.lower():
        for k in backup_map:
            if "star sports 2 tamil hd" in k.lower(): return backup_map[k]

    clean_orig = clean_name_key(original_name)
    if clean_orig in backup_map: return backup_map[clean_orig]
    
    clean_mapped = None
    for k, v in NAME_OVERRIDES.items():
        if clean_name_key(k) == clean_orig:
            clean_mapped = clean_name_key(v); break
    if clean_mapped:
        if clean_mapped in backup_map: return backup_map[clean_mapped]
        fuzzy_mapped = fuzzy_match_logic(NAME_OVERRIDES.get(original_name.lower(), clean_mapped), backup_map.keys())
        if fuzzy_mapped: return backup_map[fuzzy_mapped]
    
    fuzzy_key = fuzzy_match_logic(original_name, backup_map.keys())
    if fuzzy_key: return backup_map[fuzzy_key]
    return None

def load_local_map(ref_file):
    id_map = {}
    try:
        with open(ref_file, "r", encoding="utf-8") as f: content = f.read()
        pattern = r'tvg-id="(\d+)".*?tvg-name="([^"]+)"'
        matches = re.findall(pattern, content)
        for ch_id, ch_name in matches:
            id_map[clean_name_key(ch_name)] = ch_id
        print(f"✅ Local JioTV: Found {len(id_map)} channels.")
        return id_map
    except FileNotFoundError: return {}

def fetch_backup_map(url):
    block_map = {}
    try:
        print("🌍 Fetching Backup Source...")
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        response = requests.get(url, headers={"User-Agent": ua}, timeout=15)
        if response.status_code == 200:
            lines = response.text.splitlines()
            current_block = []; current_name = ""
            for line in lines:
                line = line.strip()
                if not line: continue
                if line.startswith("#EXTINF"):
                    if current_name and current_block:
                        key = clean_name_key(current_name)
                        data = [l for l in current_block if not l.startswith("#EXTINF")]
                        block_map[key] = data; block_map[current_name] = data 
                    current_name = line.split(",")[-1].strip()
                    current_block = [line]
                else:
                    if current_block: current_block.append(line)
            if current_name and current_block:
                key = clean_name_key(current_name)
                data = [l for l in current_block if not l.startswith("#EXTINF")]
                block_map[key] = data; block_map[current_name] = data
            print(f"✅ Backup Playlist: Parsed {len(block_map)} entries.")
    except: pass
    return block_map

def should_force_backup(name):
    norm = name.lower()
    if "star sports 2 hindi hd" in norm: return False
    for k in FORCE_BACKUP_KEYWORDS:
        if k in norm: return True
    return False

# ==========================================
# MAIN EXECUTION
# ==========================================

def update_playlist():
    print("--- STARTING UPDATE ---")
    
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_lines = [
        "#EXTM3U x-tvg-url=\"http://192.168.0.146:5350/epg.xml.gz\"",
        f"# Updated on: {current_time}"
    ]
    
    local_map = load_local_map(reference_file)
    backup_map = fetch_backup_map(backup_url)
    stats = {"local": 0, "backup": 0, "missing": 0}

    # 1. PROCESS MAIN TEMPLATE
    try:
        with open(template_file, "r", encoding="utf-8") as f: lines = f.readlines()
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Look ahead for URL
            url = ""
            if i + 1 < len(lines): url = lines[i+1].strip()

            # Ignore old youtube entries in template
            if line.startswith("#EXTINF") and 'group-title="Youtube and live events"' in line: continue

            if line.startswith("#EXTINF"):
                original_name = line.split(",")[-1].strip()
                ch_name_lower = original_name.lower()

                if "zee thirai" in ch_name_lower: continue
                if "kannada" in ch_name_lower and "star sports 1" in ch_name_lower: continue

                should_remove = False
                for rm in REMOVE_KEYWORDS:
                    if rm in ch_name_lower:
                        if "star sports 1" in rm or "star sports 2" in rm:
                            if "hd" in ch_name_lower and "kannada" not in ch_name_lower: 
                                continue 
                        should_remove = True; break
                if should_remove: continue

                if "star sports 2 hindi hd" in ch_name_lower:
                    line = line.replace("Star Sports 2 Hindi HD", "Sports18 1 HD")

                if "http://placeholder" in url:
                    clean_local_key = clean_name_key(original_name)
                    found_block = None
                    
                    if should_force_backup(original_name):
                        found_block = find_best_backup_link(original_name, backup_map)
                        if found_block: stats["backup"] += 1
                        elif clean_name_key(NAME_OVERRIDES.get(ch_name_lower, "")) in local_map:
                             found_block = [f"{base_url}/{local_map[clean_name_key(NAME_OVERRIDES[ch_name_lower])]}.m3u8"]
                             stats["local"] += 1
                        elif clean_local_key in local_map:
                            found_block = [f"{base_url}/{local_map[clean_local_key]}.m3u8"]
                            stats["local"] += 1
                    else:
                        mapped_key = clean_name_key(NAME_OVERRIDES.get(ch_name_lower, ""))
                        if clean_local_key in local_map:
                            found_block = [f"{base_url}/{local_map[clean_local_key]}.m3u8"]
                            stats["local"] += 1
                        elif mapped_key and mapped_key in local_map:
                            found_block = [f"{base_url}/{local_map[mapped_key]}.m3u8"]
                            stats["local"] += 1
                        else:
                            found_block = find_best_backup_link(original_name, backup_map)
                            if found_block: stats["backup"] += 1

                    if found_block:
                        final_lines.append(line); final_lines.extend(found_block)
                    else:
                        final_lines.append(line)
                        if clean_local_key in local_map: final_lines.append(f"{base_url}/{local_map[clean_local_key]}.m3u8")
                        else: final_lines.append(f"{base_url}/000.m3u8")
                        stats["missing"] += 1

                elif url and not url.startswith("#"):
                    if 'group-title="Youtube and live events"' not in line:
                         final_lines.append(line)
                         final_lines.append(url)
    except FileNotFoundError: pass

    # 2. APPEND LIVE EVENTS (With ID Conversion)
    print("🎥 Appending Live Events...")
    live_entries = parse_youtube_txt()
    if live_entries:
        final_lines.append("") 
        final_lines.extend(live_entries)

    # 3. APPEND FANCODE
    try:
        r = requests.get(fancode_url)
        if r.status_code == 200:
            flines = r.text.splitlines()
            if flines and flines[0].startswith("#EXTM3U"): flines = flines[1:]
            final_lines.append("\n" + "\n".join(flines))
            print("✅ Fancode merged.")
    except: pass

    with open(output_file, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print(f"\n🎉 DONE: Local: {stats['local']} | Backup: {stats['backup']} | Missing: {stats['missing']}")

if __name__ == "__main__":
    update_playlist()
