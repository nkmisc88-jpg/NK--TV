import requests
import re

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"
youtube_file = "youtube.txt"
reference_file = "jiotv_playlist.m3u.m3u8"
output_file = "playlist.m3u"

# SOURCES
base_url = "http://192.168.0.146:5350/live" 
backup_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# CHANNELS TO COMPLETELY REMOVE (As requested)
REMOVE_LIST = [
    "star sports 1", "star sports 2", # SD versions
    "sony ten 1", "sony ten 2", "sony ten 3", "sony ten 4", "sony ten 5" # All Sony Ten
]

# NAME MAPPING (Force HD versions)
NAME_OVERRIDES = {
    "zee tamil": "zee tamil hd",
    "nat geo hd": "national geographic hd",
    "star sports select 1 hd": "star sports select 1 hd",
    "star sports select 2 hd": "star sports select 2 hd",
    "dd sports hd": "dd sports hd",
    "star sports 2 hindi hd": "sports18 1",
}

# Browser UA
browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
# ==========================================

def clean_name_key(name):
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

def word_match(target_name, map_keys):
    target_lower = target_name.lower()
    # Apply override if exists
    for k, v in NAME_OVERRIDES.items():
        if k in target_lower:
            target_lower = v
            break
            
    target_words = set(re.findall(r'[a-z0-9]+', target_lower))
    
    # Priority: Search for HD first
    for key in map_keys:
        key_lower = key.lower()
        if "hd" in target_lower and "hd" not in key_lower:
            continue
        key_words = set(re.findall(r'[a-z0-9]+', key_lower))
        if target_words.issubset(key_words):
            return key
    return None

def fetch_backup_map(url):
    block_map = {}
    try:
        response = requests.get(url, headers={"User-Agent": browser_ua}, timeout=20)
        if response.status_code == 200:
            lines = response.text.splitlines()
            current_block, current_name = [], ""
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    if current_name and current_block:
                        block_map[current_name] = [l for l in current_block if not l.startswith("#EXTINF")]
                    current_name = line.split(",")[-1].strip()
                    current_block = [line]
                elif current_block:
                    current_block.append(line)
            if current_name:
                block_map[current_name] = [l for l in current_block if not l.startswith("#EXTINF")]
    except: pass
    return block_map

def update_playlist():
    local_map = {} # Load your local file here if needed
    backup_map = fetch_backup_map(backup_url)
    final_lines = ["#EXTM3U x-tvg-url=\"http://192.168.0.146:5350/epg.xml.gz\""]

    try:
        with open(template_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            if line.startswith("#EXTINF"):
                original_name = line.split(",")[-1].strip()
                
                # Check if this channel should be removed
                if any(x == original_name.lower() for x in REMOVE_LIST):
                    continue
                
                url = lines[i+1].strip() if i+1 < len(lines) else ""
                
                if "http://placeholder" in url:
                    match_key = word_match(original_name, backup_map.keys())
                    if match_key:
                        final_lines.append(line)
                        final_lines.extend(backup_map[match_key])
                else:
                    final_lines.append(line)
                    final_lines.append(url)
                    
    except Exception as e:
        print(f"Error: {e}")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    print("Playlist updated with HD fixes and removals.")

if __name__ == "__main__":
    update_playlist()
