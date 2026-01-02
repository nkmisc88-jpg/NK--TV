import requests
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

# EXTERNAL SOURCES
base_url = "http://192.168.0.146:5350/live" 
backup_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# LIVE EVENT SOURCES
sony_m3u = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
zee_m3u = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# POCKET TV SOURCE (Arunjunan20)
pocket_url = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/refs/heads/main/index.html"

# REMOVAL LIST
REMOVE_KEYWORDS = ["zee thirai", "zee tamil"]

# MAPPING
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

# ==========================================
# 1. HELPER FUNCTIONS
# ==========================================
def clean_name_key(name):
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

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
# 2. SMART PARSER & FETCHERS
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
            print(f"   ✨ Converted: {title}")
    else:
        print(f"   ▶️  Media Link: {title}")
    return f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{logo}",{title}\n{link}'

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
                entries.append(line)
            print(f"✅ Merged {len(entries)//2} channels into {group_name}.")
    except Exception as e:
        print(f"❌ Error fetching: {e}")
    return entries

# --- MODIFIED FUNCTION: POCKET TV (ARUNJUNAN) EXTRACTION ---
# NO DEDUPLICATION - Adds EVERYTHING it finds
def fetch_pocket_extras():
    entries = []
    print(f"🌍 Fetching & Filtering Pocket TV...")
    try:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        r = requests.get(pocket_url, headers={"User-Agent": ua}, timeout=15)
        
        # SPECIFIC REQUESTS (Keywords if grouping fails)
        SPECIFIC_WANTED = ["rasi", "astro", "vijay takkar"]
        
        if r.status_code == 200:
            lines = r.text.splitlines()
            count = 0
            for i in range(len(lines)):
                line = lines[i].strip()
                
                if "#EXTINF" in line:
                    name = line.split(",")[-1].strip()
                    name_lower = name.lower()
                    
                    target_group = None
                    
                    # 1. DETECT GROUPS FROM SOURCE
                    # Sports
                    if 'group-title="Sports"' in line or 'group-title="Sports HD"' in line:
                        target_group = "Sports Extra"
                    # Tamil
                    elif 'group-title="Tamil"' in line or 'group-title="Tamil HD"' in line:
                        target_group = "Tamil Extra"
                    
                    # 2. CHECK KEYWORDS (For channels not correctly grouped in source)
                    elif any(x in name_lower for x in SPECIFIC_WANTED):
                         # Assign group based on content
                         if "cricket" in name_lower or "sport" in name_lower:
                             target_group = "Sports Extra"
                         else:
                             target_group = "Tamil Extra"
                    
                    if target_group:
                        # Grab logo
                        logo = ""
                        logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                        if logo_match: logo = logo_match.group(1)
                        
                        # Find link
                        link = ""
                        for j in range(i + 1, min(i + 5, len(lines))):
                            potential = lines[j].strip()
                            if potential and not potential.startswith("#"):
                                link = potential; break
                        
                        if link:
                            # FIX PLAYBACK: Append User-Agent if missing
                            if "http" in link and "|" not in link:
                                link += f"|User-Agent={ua}"
                                
                            # Rebuild Clean Line
                            meta = f'#EXTINF:-1 group-title="{target_group}" tvg-logo="{logo}",{name}'
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
    final_lines = ["#EXTM3U", f"# Updated on: {current_time}"]
    
    local_map = load_local_map(reference_file)
    backup_map = fetch_backup_map(backup_url)
    stats = {"local": 0, "backup": 0, "missing": 0}
    
    try:
        with open(template_file, "r", encoding="utf-8") as f: lines = f.readlines()
        skip_next_url = False 
        for i, line in enumerate(lines):
            line = line.strip()
            if not line: continue
            
            if line.startswith("#EXTINF"):
                lower_line = line.lower()
                if 'group-title="youtube' in lower_line or 'group-title="temporary' in lower_line:
                    skip_next_url = True; continue              
                
                skip_next_url = False
                original_name = line.split(",")[-1].strip()
                ch_name_lower = original_name.lower()
                
                should_remove = False
                for rm in REMOVE_KEYWORDS:
                    if rm in ch_name_lower: should_remove = True; break
                if should_remove: 
                    skip_next_url = True; continue

                if i + 1 < len(lines) and "http://placeholder" in lines[i+1]:
                    clean_key = clean_name_key(original_name)
                    found_block = None
                    
                    # 1. TRY LOCAL (Preferred)
                    mapped_key = clean_name_key(NAME_OVERRIDES.get(ch_name_lower, ""))
                    if clean_key in local_map:
                         final_lines.append(line)
                         final_lines.append(f"{base_url}/{local_map[clean_key]}.m3u8")
                         skip_next_url = True
                         stats["local"] += 1
                    elif mapped_key and mapped_key in local_map:
                         final_lines.append(line)
                         final_lines.append(f"{base_url}/{local_map[mapped_key]}.m3u8")
                         skip_next_url = True
                         stats["local"] += 1
                    else:
                         # 2. BACKUP
                         found_block = find_best_backup_link(original_name, backup_map)
                         if found_block:
                             final_lines.append(line); final_lines.extend(found_block)
                             skip_next_url = True
                             stats["backup"] += 1
                         else:
                             final_lines.append(line); final_lines.append(f"{base_url}/000.m3u8")
                             skip_next_url = True
                             stats["missing"] += 1
                else:
                    final_lines.append(line)
            elif not line.startswith("#"):
                if skip_next_url: skip_next_url = False
                else: final_lines.append(line)

    except FileNotFoundError: pass

    # 1. LIVE EVENTS
    print("🎥 Appending Live Events...")
    final_lines.extend(fetch_and_group(fancode_url, "Live Events"))
    final_lines.extend(fetch_and_group(sony_m3u, "Live Events"))
    final_lines.extend(fetch_and_group(zee_m3u, "Live Events"))

    # 2. POCKET TV EXTRAS (ALL Sports + ALL Tamil)
    # Deduplication logic removed
    final_lines.extend(fetch_pocket_extras())

    # 3. MANUAL / YOUTUBE
    print("🎥 Appending Temporary Channels...")
    final_lines.extend(parse_youtube_txt())

    with open(output_file, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print(f"🎉 DONE. Local: {stats['local']} | Backup: {stats['backup']} | Missing: {stats['missing']}")

if __name__ == "__main__":
    update_playlist()