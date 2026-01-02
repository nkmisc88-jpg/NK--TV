Import requests
import re
import datetime
import os

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"
youtube_file = "youtube.txt"
reference_file = "jiotv_playlist.m3u.m3u8"
output_file = "playlist.m3u"

# LOCAL SERVER (Strict Priority)
base_url = "http://192.168.0.146:5350/live" 
backup_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"

# EXTERNAL SOURCES
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
sony_m3u = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
zee_m3u = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# POCKET TV SOURCE (Arunjunan20)
pocket_url = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/refs/heads/main/index.html"

# EPG HEADER
EPG_HEADER = '#EXTM3U x-tvg-url="http://192.168.0.146:5350/epg.xml.gz,https://avkb.short.gy/epg.xml.gz" tvg-shift="-5.5"'

# REMOVE LIST
REMOVE_KEYWORDS = ["zee thirai"]

# FORCE BACKUP LIST (For Sony/Zee main channels)
FORCE_BACKUP_KEYWORDS = [
    "zee", "vijay", "asianet", "suvarna", "maa", "hotstar", "sony", "set", "sab",
    "nick", "cartoon", "pogo", "disney", "hungama", "sonic", "discovery", 
    "history", "tlc", "animal planet", "travelxp", "bbc earth", "movies now", "mnx", "romedy", "mn+", "pix",
    "&pictures", "ten"
]

# NAME MAPPING
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

# LOGO LIBRARY (Fallback)
CHANNEL_META = {
    "sony sports ten 1": {"id": "Sony Ten 1 HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_Ten_1_HD.png"},
    "sony sports ten 2": {"id": "Sony Ten 2 HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_Ten_2_HD.png"},
    "sony sports ten 3": {"id": "Sony Ten 3 HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_Ten_3_HD.png"},
    "sony sports ten 4": {"id": "Sony Ten 4 HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_Ten_4_HD.png"},
    "sony sports ten 5": {"id": "Sony Six HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_Six_HD.png"},
    "zee tamil": {"id": "Zee Tamil HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Zee_Tamil_HD.png"},
    "zee thirai": {"id": "Zee Thirai HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Zee_Thirai_HD.png"},
    "astro cricket": {"id": "Astro Cricket", "logo": "https://i.imgur.com/7Xj4G6d.png"},
    "sky sports cricket": {"id": "Sky Sports Cricket", "logo": "https://i.imgur.com/Frw9n3r.png"},
    "vijay takkar": {"id": "Vijay Takkar", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Vijay_Takkar.png"},
}

# ==========================================
# 1. HELPER FUNCTIONS
# ==========================================
def clean_name_key(name):
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

def enrich_metadata(line, channel_name):
    clean_name = clean_name_key(channel_name)
    
    # 1. FORCE TIME SHIFT
    if 'tvg-shift' not in line:
        line = line.replace("#EXTINF:-1", '#EXTINF:-1 tvg-shift="-5.5"')
    
    # 2. Add Meta (Only if missing)
    meta = None
    for k, v in CHANNEL_META.items():
        if k in clean_name: 
            meta = v; break
            
    if meta:
        if 'tvg-logo' not in line:
            line = line.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-logo="{meta["logo"]}"')
        elif 'tvg-logo=""' in line:
            line = line.replace('tvg-logo=""', f'tvg-logo="{meta["logo"]}"')
            
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
        r = requests.get(url, timeout=15)
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
# 2. FETCHERS
# ==========================================
def parse_youtube_txt():
    entries = []
    if not os.path.exists(youtube_file): return []
    with open(youtube_file, "r", encoding="utf-8") as f: lines = f.readlines()
    current = {}
    for line in lines:
        line = line.strip()
        if not line: continue
        if line.lower().startswith("title") and ":" in line:
            if 'link' in current:
                 l = f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{current.get("logo","")}",{current["title"]}\n{current["link"]}'
                 entries.append(enrich_metadata(l.split('\n')[0], current["title"]) + '\n' + l.split('\n')[1])
            current = {}
        if ':' in line:
            parts = line.split(':', 1)
            current[parts[0].strip().lower()] = parts[1].strip()
    if 'link' in current:
         l = f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{current.get("logo","")}",{current["title"]}\n{current["link"]}'
         entries.append(enrich_metadata(l.split('\n')[0], current["title"]) + '\n' + l.split('\n')[1])
    return entries

def fetch_and_group(url, group_name):
    entries = []
    print(f"🌍 Fetching into '{group_name}'...")
    try:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        r = requests.get(url, headers={"User-Agent": ua}, timeout=15)
        if r.status_code == 200:
            lines = r.text.splitlines()
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#EXTM3U"): continue
                if line.startswith("#EXTINF"):
                    line = re.sub(r'group-title="[^"]*"', '', line)
                    line = re.sub(r'(#EXTINF:[-0-9]+)', f'\\1 group-title="{group_name}"', line)
                    name = line.split(",")[-1].strip()
                    line = enrich_metadata(line, name)
                entries.append(line)
            print(f"✅ Merged {len(entries)//2} channels into {group_name}.")
    except Exception as e: print(f"❌ Error fetching: {e}")
    return entries

# --- [UPDATED] STRICT POCKET TV FILTER ---
def fetch_pocket_extras():
    entries = []
    print(f"🌍 Fetching & Filtering Pocket TV...")
    try:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        r = requests.get(pocket_url, headers={"User-Agent": ua}, timeout=15)
        
        # STRICT LISTS
        SPORTS_WANTED = ["astro cricket", "sony ten", "sky sports"]
        TAMIL_WANTED = [
            "zee tamil", "zee thirai", "vijay takkar", "rasi",
            "astro thangathirai", "astro vellithirai", "astro vaanavil", "astro vinmeen"
        ]
        
        if r.status_code == 200:
            lines = r.text.splitlines()
            count = 0
            for i in range(len(lines)):
                line = lines[i].strip()
                
                if "#EXTINF" in line:
                    name = line.split(",")[-1].strip()
                    name_lower = name.lower()
                    
                    # Grab Source Logo
                    logo = ""
                    logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                    if logo_match: logo = logo_match.group(1)
                    
                    target_group = None
                    
                    # CHECK STRICT MATCHES
                    if any(x in name_lower for x in SPORTS_WANTED):
                        target_group = "Sports Extra"
                    elif any(x in name_lower for x in TAMIL_WANTED):
                        target_group = "Tamil Extra"
                    
                    if target_group:
                        # Find link
                        link = ""
                        for j in range(i + 1, min(i + 5, len(lines))):
                            potential = lines[j].strip()
                            if potential and not potential.startswith("#"):
                                link = potential; break
                        
                        if link:
                            # Rebuild Clean Line
                            meta = f'#EXTINF:-1 group-title="{target_group}" tvg-logo="{logo}",{name}'
                            meta = enrich_metadata(meta, name)
                            entries.append(meta)
                            entries.append(link)
                            count += 1
                            
            print(f"✅ Extracted {count} Requested Channels.")
            
    except Exception as e: print(f"❌ Error Pocket TV: {e}")
    return entries

# ==========================================
# 3. MAIN EXECUTION
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
                # Clean old groups
                if 'group-title="live events' in lower_line or 'group-title="temporary' in lower_line:
                    skip_next_url = True; continue              
                
                skip_next_url = False
                original_name = line.split(",")[-1].strip()
                ch_name_lower = original_name.lower()
                
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
    print("🎥 Appending Live Events...")
    final_lines.extend(fetch_and_group(fancode_url, "Live Events"))
    final_lines.extend(fetch_and_group(sony_m3u, "Live Events"))
    final_lines.extend(fetch_and_group(zee_m3u, "Live Events"))

    # 3. APPEND EXTRAS (Strictly Filtered)
    final_lines.extend(fetch_pocket_extras())

    # 4. APPEND MANUAL
    print("🎥 Appending Temporary Channels...")
    final_lines.extend(parse_youtube_txt())

    with open(output_file, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print(f"🎉 DONE. Local: {stats['local']} | Backup: {stats['backup']} | Missing: {stats['missing']}")

if __name__ == "__main__":
    update_playlist()
