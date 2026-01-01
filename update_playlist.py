import requests
import re
import datetime
import os

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"
youtube_file = "youtube.txt"
pocket_file = "pocket.m3u"
reference_file = "jiotv_playlist.m3u.m3u8"
output_file = "playlist.m3u"

# EXTERNAL SOURCES
base_url = "http://192.168.0.146:5350/live" 
backup_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# RELIABLE BACKUPS (Sony/Zee)
sony_m3u = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
zee_m3u = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# EPG SOURCE
EPG_HEADER = '#EXTM3U x-tvg-url="http://192.168.0.146:5350/epg.xml.gz,https://avkb.short.gy/epg.xml.gz,https://www.tsepg.cf/epg.xml.gz"'

# POCKET TV WISH LIST
POCKET_WANTED = [
    "astro cricket", "sony ten", "sky sports cricket", 
    "zee tamil", "zee thirai", "vijay takkar", "rasi"
]

REMOVE_KEYWORDS = ["zee thirai"]

FORCE_BACKUP_KEYWORDS = [
    "zee", "sony", "sab", "set", "pix", "max", "wah", "pal",
    "vijay", "asianet", "suvarna", "maa", "hotstar", 
    "nick", "cartoon", "pogo", "disney", "hungama", "sonic", "discovery", 
    "history", "tlc", "animal planet", "travelxp", "bbc earth", "movies now", "mnx", "romedy", "mn+",
    "&pictures", "ten"
]

NAME_OVERRIDES = {
    "star sports 1 hd": "Star Sports HD1",
    "star sports 2 hd": "Star Sports HD2",
    "star sports 1 hindi hd": "Star Sports HD1 Hindi",
    "star sports select 1 hd": "Star Sports Select HD1",
    "star sports select 2 hd": "Star Sports Select HD2",
    "star sports 2 hindi hd": "Sports18 1 HD",
    "star sports 2 tamil hd": "Star Sports 2 Tamil HD",
    "nat geo hd": "National Geographic HD",
    "nat geo wild hd": "Nat Geo Wild HD",
}

# --- MEGA LOGO & ID LIBRARY ---
CHANNEL_META = {
    # SONY
    "sony sports ten 1": {"id": "Sony Ten 1 HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_Ten_1_HD.png"},
    "sony sports ten 2": {"id": "Sony Ten 2 HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_Ten_2_HD.png"},
    "sony sports ten 3": {"id": "Sony Ten 3 HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_Ten_3_HD.png"},
    "sony sports ten 4": {"id": "Sony Ten 4 HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_Ten_4_HD.png"},
    "sony sports ten 5": {"id": "Sony Six HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_Six_HD.png"},
    "sony sab": {"id": "Sony SAB HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_SAB_HD.png"},
    "sony pix": {"id": "Sony Pix HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_Pix_HD.png"},
    "sony bbc earth": {"id": "Sony BBC Earth HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_BBC_Earth_HD.png"},
    "set hd": {"id": "Sony SET HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_SET_HD.png"},
    
    # ZEE
    "zee tamil": {"id": "Zee Tamil HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Zee_Tamil_HD.png"},
    "zee thirai": {"id": "Zee Thirai HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Zee_Thirai_HD.png"},
    "zee tv": {"id": "Zee TV HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Zee_TV_HD.png"},
    "zee telugu": {"id": "Zee Telugu HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Zee_Telugu_HD.png"},
    
    # STAR / DISNEY
    "star movies": {"id": "Star Movies HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Star_Movies_HD.png"},
    "star plus": {"id": "Star Plus HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Star_Plus_HD.png"},
    "star sports 1 hd": {"id": "Star Sports 1 HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Star_Sports_1_HD.png"},
    "star sports 2 hd": {"id": "Star Sports 2 HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Star_Sports_2_HD.png"},
    "star sports 1 hindi": {"id": "Star Sports 1 Hindi HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Star_Sports_1_Hindi_HD.png"},
    "star sports 1 tamil": {"id": "Star Sports 1 Tamil HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Star_Sports_1_Tamil_HD.png"},
    "star sports 2 tamil": {"id": "Star Sports 2 Tamil HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Star_Sports_2_Tamil_HD.png"},
    
    # INFOTAINMENT
    "discovery hd": {"id": "Discovery HD World", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Discovery_HD_World.png"},
    "animal planet hd": {"id": "Animal Planet HD World", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Animal_Planet_HD_World.png"},
    "tlc hd": {"id": "TLC HD World", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/TLC_HD_World.png"},
    "nat geo hd": {"id": "Nat Geo HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Nat_Geo_HD.png"},
    "nat geo wild": {"id": "Nat Geo Wild HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Nat_Geo_Wild_HD.png"},
    "history tv18": {"id": "History TV18 HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/History_TV18_HD.png"},
    
    # OTHERS
    "astro cricket": {"id": "Astro Cricket", "logo": "https://i.imgur.com/7Xj4G6d.png"},
    "sky sports cricket": {"id": "Sky Sports Cricket", "logo": "https://i.imgur.com/Frw9n3r.png"},
    "vijay takkar": {"id": "Vijay Takkar", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Vijay_Takkar.png"},
    "colors hd": {"id": "Colors HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Colors_HD.png"},
    "colors kannada": {"id": "Colors Kannada HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Colors_Kannada_HD.png"},
    "gemini tv": {"id": "Gemini TV HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Gemini_TV_HD.png"},
    "udaya hd": {"id": "Udaya HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Udaya_HD.png"},
    "surya hd": {"id": "Surya HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Surya_HD.png"},
    "asianet news": {"id": "Asianet News", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Asianet_News.png"},
    "mtv hd": {"id": "MTV HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/MTV_HD_Plus.png"},
    "9xm": {"id": "9XM", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/9XM.png"},
    "zoom": {"id": "Zoom", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Zoom.png"},
    "movies now": {"id": "Movies Now HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Movies_Now_HD.png"},
    "mn+": {"id": "MN+ HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/MN_Plus_HD.png"},
    "mnx": {"id": "MNX HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/MNX_HD.png"},
    "romedy now": {"id": "Romedy Now", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Romedy_Now.png"},
}

# ==========================================
# 1. HELPER FUNCTIONS
# ==========================================
def clean_name_key(name):
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

def enrich_metadata(line, channel_name):
    """Aggressively replaces Logo and EPG ID based on channel name"""
    clean_name = clean_name_key(channel_name)
    meta = None
    
    # Find matching metadata
    for k, v in CHANNEL_META.items():
        if k in clean_name: 
            meta = v; break
            
    if meta:
        # 1. FORCE REPLACE LOGO (Regex)
        # This deletes any existing tvg-logo="..." and adds the correct one
        if 'tvg-logo=' in line:
            line = re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{meta["logo"]}"', line)
        else:
            line = line.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-logo="{meta["logo"]}"')
            
        # 2. FORCE REPLACE EPG ID
        if 'tvg-id=' in line:
             line = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{meta["id"]}"', line)
        else:
             line = line.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-id="{meta["id"]}"')
             
    return line

def should_force_backup(name):
    norm = name.lower()
    if "star sports" in norm or "nat geo" in norm: return False
    for k in FORCE_BACKUP_KEYWORDS:
        if k in norm: return True
    return False

def find_best_backup_link(original_name, backup_map):
    clean_orig = clean_name_key(original_name)
    if clean_orig in backup_map: return backup_map[clean_orig]
    
    clean_mapped = None
    for k, v in NAME_OVERRIDES.items():
        if clean_name_key(k) == clean_orig: clean_mapped = clean_name_key(v); break
    if clean_mapped and clean_mapped in backup_map: return backup_map[clean_mapped]
    return None

def load_local_map(ref_file):
    id_map = {}
    try:
        with open(ref_file, "r", encoding="utf-8") as f: content = f.read()
        pattern = r'tvg-id="(\d+)".*?tvg-name="([^"]+)"'
        matches = re.findall(pattern, content)
        for ch_id, ch_name in matches: id_map[clean_name_key(ch_name)] = ch_id
    except: pass
    return id_map

def fetch_backup_map(url):
    block_map = {}
    try:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        r = requests.get(url, headers={"User-Agent": ua}, timeout=15)
        if r.status_code == 200:
            lines = r.text.splitlines()
            current_block = []; current_name = ""
            for line in lines:
                line = line.strip()
                if not line: continue
                if line.startswith("#EXTINF"):
                    if current_name and current_block:
                        key = clean_name_key(current_name)
                        data = [l for l in current_block if not l.startswith("#EXTINF")]
                        block_map[key] = data 
                    current_name = line.split(",")[-1].strip()
                    current_block = [line]
                else:
                    if current_block: current_block.append(line)
            if current_name: block_map[clean_name_key(current_name)] = [l for l in current_block if not l.startswith("#EXTINF")]
    except: pass
    return block_map

# ==========================================
# 2. PARSERS
# ==========================================
def parse_youtube_txt():
    new_entries = []
    if not os.path.exists(youtube_file): return []
    with open(youtube_file, "r", encoding="utf-8") as f: lines = f.readlines()
    current_entry = {}
    for line in lines:
        line = line.strip()
        if not line: continue 
        if line.lower().startswith("title") and ":" in line:
            if 'link' in current_entry: new_entries.append(process_entry(current_entry))
            current_entry = {} 
        if ':' in line:
            parts = line.split(':', 1)
            current_entry[parts[0].strip().lower()] = parts[1].strip()
    if 'link' in current_entry: new_entries.append(process_entry(current_entry))
    return new_entries

def process_entry(data):
    title = data.get('title', 'Unknown Channel')
    logo = data.get('logo', '')
    link = data.get('link', '')
    if "youtube.com" in link or "youtu.be" in link:
        vid_match = re.search(r'(?:v=|\/live\/|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', link)
        if vid_match:
            link = f"https://youtube.jitendraunatti.workers.dev/wanda.m3u8?id={vid_match.group(1)}"
            
    line = f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{logo}",{title}'
    # Apply Meta fix
    line = enrich_metadata(line, title)
    return f'{line}\n{link}'

def parse_pocket_playlist():
    entries = []
    if not os.path.exists(pocket_file):
        print("⚠️ 'pocket.m3u' not found. Skipping Pocket TV extraction.")
        return []
    
    print(f"📂 Reading {pocket_file}...")
    try:
        with open(pocket_file, "r", encoding="utf-8") as f: lines = f.readlines()
        current_block = []; keep_block = False
        for line in lines:
            line = line.strip()
            if not line: continue
            
            if line.startswith("#EXTINF"):
                if keep_block and len(current_block) >= 2: entries.extend(current_block)
                current_block = [line]; keep_block = False
                line_lower = line.lower()
                for keyword in POCKET_WANTED:
                    if keyword in line_lower:
                        keep_block = True
                        meta = current_block[0]
                        name = meta.split(",")[-1].strip()
                        meta = re.sub(r'group-title="[^"]*"', '', meta)
                        meta = meta.replace("#EXTINF:-1", '#EXTINF:-1 group-title="Pocket TV Favorites"')
                        meta = enrich_metadata(meta, name)
                        current_block[0] = meta
                        break
            else:
                if current_block: current_block.append(line)
        if keep_block and len(current_block) >= 2: entries.extend(current_block)
        print(f"✅ Extracted {len(entries)//2} channels from Pocket TV.")
    except Exception as e: print(f"❌ Error reading Pocket TV: {e}")
    return entries

# ==========================================
# 3. EXTERNAL FETCHERS
# ==========================================
def fetch_sony_live_matches():
    entries = []
    try:
        print("🌍 Fetching Sony Live Matches (JSON)...")
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        r = requests.get(sony_json, headers={"User-Agent": ua}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            matches = data.get("data", [])
            for match in matches:
                try:
                    title = match['video_info']['title']
                    logo = match['image_cdn']['thumbnail']
                    link = ""
                    audio_links = match.get("MULTIPLE_AUDIO_LINKS", [])
                    if audio_links:
                        first_audio = audio_links[0].get("DATA", {})
                        if "JITENDRAUNATTI" in first_audio:
                            link = first_audio["JITENDRAUNATTI"].get("Playback_videoURL", "")
                    if link:
                        entries.append(f'#EXTINF:-1 group-title="Sony Live Events" tvg-logo="{logo}",{title}\n{link}')
                except: continue
    except: pass
    return entries

def fetch_and_group_m3u(url, group_name):
    entries = []
    try:
        print(f"🌍 Fetching {group_name}...")
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        r = requests.get(url, headers={"User-Agent": ua}, timeout=15)
        if r.status_code == 200:
            lines = r.text.splitlines()
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#EXTM3U"): continue
                if line.startswith("#EXTINF"):
                    # Fix Meta & Group
                    name = line.split(",")[-1].strip()
                    line = enrich_metadata(line, name)
                    line = re.sub(r'group-title="[^"]*"', '', line)
                    line = line.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group_name}"')
                entries.append(line)
    except: pass
    return entries

# ==========================================
# 4. MAIN EXECUTION
# ==========================================
def update_playlist():
    print("--- STARTING UPDATE ---")
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_lines = [EPG_HEADER, f"# Updated on: {current_time}"]
    
    local_map = load_local_map(reference_file)
    backup_map = fetch_backup_map(backup_url)
    stats = {"local": 0, "backup": 0, "missing": 0}

    # 1. PROCESS TEMPLATE
    try:
        with open(template_file, "r", encoding="utf-8") as f: lines = f.readlines()
        skip_next_url = False 
        for i, line in enumerate(lines):
            line = line.strip()
            if not line: continue
            
            if line.startswith("#EXTINF"):
                lower_line = line.lower()
                if 'group-title="youtube' in lower_line or 'group-title="temporary' in lower_line or 'group-title="pocket' in lower_line:
                    skip_next_url = True; continue              
                
                skip_next_url = False
                original_name = line.split(",")[-1].strip()
                ch_name_lower = original_name.lower()
                
                # --- APPLY SMART META ---
                line = enrich_metadata(line, original_name)

                should_remove = False
                for rm in REMOVE_KEYWORDS:
                    if rm in ch_name_lower: should_remove = True; break
                if should_remove: 
                    skip_next_url = True; continue

                if i + 1 < len(lines) and "http://placeholder" in lines[i+1]:
                    clean_key = clean_name_key(original_name)
                    found_block = None
                    
                    if should_force_backup(original_name):
                        found_block = find_best_backup_link(original_name, backup_map)
                    
                    if found_block:
                         final_lines.append(line); final_lines.extend(found_block)
                         skip_next_url = True; stats["backup"] += 1
                    else:
                         mapped_key = clean_name_key(NAME_OVERRIDES.get(ch_name_lower, ""))
                         if clean_key in local_map:
                             final_lines.append(line); final_lines.append(f"{base_url}/{local_map[clean_key]}.m3u8")
                             skip_next_url = True; stats["local"] += 1
                         elif mapped_key and mapped_key in local_map:
                             final_lines.append(line); final_lines.append(f"{base_url}/{local_map[mapped_key]}.m3u8")
                             skip_next_url = True; stats["local"] += 1
                         else:
                             found_block = find_best_backup_link(original_name, backup_map)
                             if found_block:
                                 final_lines.append(line); final_lines.extend(found_block)
                                 skip_next_url = True; stats["backup"] += 1
                             else:
                                 final_lines.append(line); final_lines.append(f"{base_url}/000.m3u8")
                                 skip_next_url = True; stats["missing"] += 1
                else:
                    final_lines.append(line)

            elif not line.startswith("#"):
                if skip_next_url: skip_next_url = False
                else: final_lines.append(line)

    except FileNotFoundError: pass

    # 2. APPEND EXTERNAL CONTENT
    print("🎥 Appending Sony Live Matches...")
    final_lines.extend(fetch_sony_live_matches())

    print("🎥 Appending Pocket TV Favorites...")
    final_lines.extend(parse_pocket_playlist())

    print("🎥 Appending Fancode...")
    final_lines.extend(fetch_and_group_m3u(fancode_url, "Fancode"))
    
    print("🎥 Appending Sony Backup...")
    final_lines.extend(fetch_and_group_m3u(sony_m3u, "Sony Backup"))
    
    print("🎥 Appending Zee Backup...")
    final_lines.extend(fetch_and_group_m3u(zee_m3u, "Zee Backup"))

    print("🎥 Appending Temporary Channels...")
    final_lines.extend(parse_youtube_txt())

    with open(output_file, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print(f"🎉 DONE. Local: {stats['local']} | Backup: {stats['backup']} | Missing: {stats['missing']}")

if __name__ == "__main__":
    update_playlist()
