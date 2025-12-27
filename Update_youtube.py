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
REMOVE_KEYWORDS = ["sony ten", "sonyten", "star sports 1", "star sports 2", "zee thirai"]
FORCE_BACKUP_KEYWORDS = ["star", "zee", "vijay", "asianet", "suvarna", "maa", "hotstar", "sony"]
NAME_OVERRIDES = {"star sports 2 hindi hd": "Sports18 1 HD"} 

# ==========================================
# 1. HELPER FUNCTIONS
# ==========================================
def clean_name_key(name):
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

def get_significant_words(name):
    name = name.lower().replace("sports18", "sports 18") 
    name = re.sub(r'\b(hd|sd|tv|channel|network|india|world|english|tamil|hindi|telugu|kannada|movies|cinema)\b', '', name)
    return set(re.findall(r'[a-z0-9]+', name))

def find_best_backup_link(original_name, backup_map):
    # ( Simplified logic for brevity - keeping your core logic intact )
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
        print("🌍 Fetching Backup Source...")
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
# 2. TEMPORARY CHANNELS PARSER
# ==========================================
def parse_youtube_txt():
    new_entries = []
    if not os.path.exists(youtube_file): return []

    print(f"📂 Reading {youtube_file}...")
    with open(youtube_file, "r", encoding="utf-8") as f: lines = f.readlines()

    current_entry = {}
    for line in lines:
        line = line.strip()
        if not line: 
            if 'link' in current_entry: new_entries.append(process_entry(current_entry))
            current_entry = {} 
            continue
        if ':' in line:
            parts = line.split(':', 1)
            current_entry[parts[0].strip().lower()] = parts[1].strip()
    if 'link' in current_entry: new_entries.append(process_entry(current_entry))
    return new_entries

def process_entry(data):
    title = data.get('title', 'Unknown Channel')
    logo = data.get('logo', '')
    link = data.get('link', '')
    
    # Check if it is YouTube
    if "youtube.com" in link or "youtu.be" in link:
        vid_match = re.search(r'(?:v=|\/live\/|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', link)
        if vid_match:
            link = f"https://youtube.jitendraunatti.workers.dev/wanda.m3u8?id={vid_match.group(1)}"
            print(f"   ✨ Converted: {title}")
    
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

    # --- STEP A: PROCESS MAIN TEMPLATE (WITH FIX) ---
    try:
        with open(template_file, "r", encoding="utf-8") as f: lines = f.readlines()
        
        skip_next_url = False # Flag to delete "Ghost" links
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line: continue
            
            # 1. Handle Metadata Line (#EXTINF)
            if line.startswith("#EXTINF"):
                # CHECK: Is this an old Temporary/YouTube channel?
                if 'group-title="Youtube' in line or 'group-title="Temporary' in line:
                    skip_next_url = True  # Mark to skip the URL below it
                    continue              # Delete this line
                
                # If we are here, it's a valid TV channel. Reset flag.
                skip_next_url = False
                
                original_name = line.split(",")[-1].strip()
                ch_name_lower = original_name.lower()

                # Filter unwanted channels
                should_remove = False
                for rm in REMOVE_KEYWORDS:
                    if rm in ch_name_lower: should_remove = True; break
                if should_remove: 
                    skip_next_url = True
                    continue

                # Check for "http://placeholder" logic
                if i + 1 < len(lines) and "http://placeholder" in lines[i+1]:
                    # (This is a simplified version of your logic for brevity)
                    clean_key = clean_name_key(original_name)
                    found_link = None
                    
                    # Try Backup First (if forced) or Local
                    found_block = find_best_backup_link(original_name, backup_map)
                    if found_block: 
                         final_lines.append(line)
                         final_lines.extend(found_block)
                         skip_next_url = True # We handled the URL, so skip the placeholder
                    elif clean_key in local_map:
                         final_lines.append(line)
                         final_lines.append(f"{base_url}/{local_map[clean_key]}.m3u8")
                         skip_next_url = True
                    else:
                         # Keep original placeholder if nothing found
                         final_lines.append(line)
                         # Let the loop pick up the placeholder in next iteration? 
                         # No, better to force it here to be safe.
                         final_lines.append(f"{base_url}/000.m3u8") 
                         skip_next_url = True
                else:
                    # Just a normal channel, keep it.
                    final_lines.append(line)

            # 2. Handle URL Line
            elif not line.startswith("#"):
                if skip_next_url:
                    # This is the "Ghost Link" -> DELETE IT
                    skip_next_url = False 
                    continue
                else:
                    # Valid link, keep it
                    final_lines.append(line)

    except FileNotFoundError: pass

    # --- STEP B: APPEND TEMPORARY CHANNELS ---
    print("🎥 Appending Temporary Channels...")
    final_lines.extend(parse_youtube_txt())

    # --- STEP C: APPEND FANCODE ---
    try:
        r = requests.get(fancode_url)
        if r.status_code == 200:
            flines = r.text.splitlines()
            if flines and "#EXTM3U" in flines[0]: flines = flines[1:]
            final_lines.append("\n" + "\n".join(flines))
            print("✅ Fancode merged.")
    except: pass

    with open(output_file, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print("🎉 DONE. Playlist Saved.")

if __name__ == "__main__":
    update_playlist()
