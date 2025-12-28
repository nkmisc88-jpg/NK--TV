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

# REMOVAL LIST
REMOVE_KEYWORDS = ["zee thirai"]

FORCE_BACKUP_KEYWORDS = [
    "zee", "vijay", "asianet", "suvarna", "maa", "hotstar", "sony", "set", "sab",
    "nick", "cartoon", "pogo", "disney", "hungama", "sonic", "discovery", "nat geo", 
    "history", "tlc", "animal planet", "travelxp", "bbc earth", "movies now", "mnx", "romedy", "mn+", "pix",
    "&pictures", "ten"
    # REMOVED "star" and "sports" so they use Local JioTV
]

NAME_OVERRIDES = {
    "star sports 2 hindi hd": "Sports18 1 HD",
    "star sports 2 tamil hd": "Star Sports 2 Tamil HD",
    "star sports 1 hd": "Star Sports HD1",
    "star sports 2 hd": "Star Sports HD2",
    "star sports 1 hindi hd": "Star Sports HD1 Hindi",
    "star sports select 1 hd": "Star Sports Select HD1",
    "star sports select 2 hd": "Star Sports Select HD2",
}

# ==========================================
# 1. HELPER FUNCTIONS
# ==========================================
def clean_name_key(name):
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

def should_force_backup(name):
    norm = name.lower()
    # FIX: Always try LOCAL first for Star Sports
    if "star sports" in norm: return False
    
    for k in FORCE_BACKUP_KEYWORDS:
        if k in norm: return True
    return False

def find_best_backup_link(original_name, backup_map):
    # Skip backup logic for Star Sports (try local first)
    if "star sports" in original_name.lower(): return None

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
# 2. SMART PARSER
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
            if 'link' in current_entry:
                new_entries.append(process_entry(current_entry))
            current_entry = {} 
        
        if ':' in line:
            parts = line.split(':', 1)
            key = parts[0].strip().lower()
            val = parts[1].strip()
            current_entry[key] = val
    
    if 'link' in current_entry:
        new_entries.append(process_entry(current_entry))

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
                    
                    # 1. Check Forced Backup
                    if should_force_backup(original_name):
                        found_block = find_best_backup_link(original_name, backup_map)
                    
                    # 2. Try Local if not forced or not found in backup
                    if not found_block:
                         # Check overrides
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
                             # Last resort: Backup
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
                        final_lines.append(line); final_lines.extend(found_block)
                        skip_next_url = True
                        stats["backup"] += 1
                else:
                    final_lines.append(line)

            elif not line.startswith("#"):
                if skip_next_url: skip_next_url = False
                else: final_lines.append(line)

    except FileNotFoundError: pass

    print("🎥 Appending Temporary Channels...")
    final_lines.extend(parse_youtube_txt())

    try:
        r = requests.get(fancode_url)
        if r.status_code == 200:
            flines = r.text.splitlines()
            if flines and "#EXTM3U" in flines[0]: flines = flines[1:]
            final_lines.append("\n" + "\n".join(flines))
            print("✅ Fancode merged.")
    except: pass

    with open(output_file, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print(f"🎉 DONE. Local: {stats['local']} | Backup: {stats['backup']} | Missing: {stats['missing']}")

if __name__ == "__main__":
    update_playlist()
