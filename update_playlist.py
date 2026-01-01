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

# 1. LOCAL SOURCE (Strictly for Star/Nat Geo)
base_url = "http://192.168.0.146:5350/live" 

# 2. EXTERNAL SOURCES (Strictly for Sony/Zee)
sony_m3u = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
zee_m3u = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# EPG SOURCE
EPG_HEADER = '#EXTM3U x-tvg-url="http://192.168.0.146:5350/epg.xml.gz,https://avkb.short.gy/epg.xml.gz,https://www.tsepg.cf/epg.xml.gz"'

# DATA MAPPING (To ensure Local Links find the right ID)
LOCAL_NAME_MAP = {
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
# HELPER FUNCTIONS
# ==========================================
def clean_name_key(name):
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

def load_local_map(ref_file):
    id_map = {}
    try:
        with open(ref_file, "r", encoding="utf-8") as f: content = f.read()
        pattern = r'tvg-id="(\d+)".*?tvg-name="([^"]+)"'
        matches = re.findall(pattern, content)
        for ch_id, ch_name in matches: id_map[clean_name_key(ch_name)] = ch_id
    except: pass
    return id_map

# ==========================================
# FETCHERS
# ==========================================
def fetch_and_clean_m3u(url, group_name):
    entries = []
    print(f"🌍 Fetching {group_name}...")
    try:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        r = requests.get(url, headers={"User-Agent": ua}, timeout=15)
        if r.status_code == 200:
            lines = r.text.splitlines()
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#EXTM3U"): continue
                
                if line.startswith("#EXTINF"):
                    # Force Group Name
                    line = re.sub(r'group-title="[^"]*"', '', line)
                    line = line.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group_name}"')
                entries.append(line)
            print(f"✅ {group_name} merged.")
    except: pass
    return entries

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
    
    # YouTube Converter
    if "youtube.com" in link or "youtu.be" in link:
        vid_match = re.search(r'(?:v=|\/live\/|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', link)
        if vid_match:
            link = f"https://youtube.jitendraunatti.workers.dev/wanda.m3u8?id={vid_match.group(1)}"
            
    return f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{logo}",{title}\n{link}'

# ==========================================
# MAIN EXECUTION
# ==========================================
def update_playlist():
    print("--- STARTING UPDATE ---")
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_lines = [EPG_HEADER, f"# Updated on: {current_time}"]
    
    local_map = load_local_map(reference_file)
    stats = {"local": 0, "skipped": 0}

    # 1. PROCESS TEMPLATE (Only keep Star/Nat Geo Local)
    try:
        with open(template_file, "r", encoding="utf-8") as f: lines = f.readlines()
        skip_next_url = False 
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line: continue
            
            if line.startswith("#EXTINF"):
                lower_line = line.lower()
                
                # CLEANUP: Remove old auto-groups to prevent duplicates
                if 'group-title="youtube' in lower_line or 'group-title="temporary' in lower_line:
                    skip_next_url = True; continue

                original_name = line.split(",")[-1].strip()
                ch_name_lower = original_name.lower()

                # LOGIC:
                # 1. If it is Sony or Zee -> SKIP IT (We will auto-fetch the working version later)
                if "sony" in ch_name_lower or "zee" in ch_name_lower or "ten" in ch_name_lower:
                    skip_next_url = True
                    stats["skipped"] += 1
                    continue

                # 2. If it is Star Sports / Nat Geo -> USE LOCAL
                skip_next_url = False
                if i + 1 < len(lines) and "http://placeholder" in lines[i+1]:
                    clean_key = clean_name_key(original_name)
                    mapped_key = clean_name_key(LOCAL_NAME_MAP.get(ch_name_lower, ""))
                    
                    if clean_key in local_map:
                         final_lines.append(line); final_lines.append(f"{base_url}/{local_map[clean_key]}.m3u8")
                         skip_next_url = True; stats["local"] += 1
                    elif mapped_key and mapped_key in local_map:
                         final_lines.append(line); final_lines.append(f"{base_url}/{local_map[mapped_key]}.m3u8")
                         skip_next_url = True; stats["local"] += 1
                    else:
                         # Keep placeholder if local missing (don't break formatting)
                         final_lines.append(line); final_lines.append(f"{base_url}/000.m3u8")
                         skip_next_url = True
                else:
                    final_lines.append(line)

            elif not line.startswith("#"):
                if skip_next_url: skip_next_url = False
                else: final_lines.append(line)

    except FileNotFoundError: pass

    # 2. APPEND WORKING EXTERNAL CHANNELS
    # (Replaces the broken ones we skipped in Step 1)
    
    print("🎥 Appending Sony/Zee (Working)...")
    final_lines.extend(fetch_and_clean_m3u(sony_m3u, "Temporary Channels")) # Put in Temp folder as requested
    final_lines.extend(fetch_and_clean_m3u(zee_m3u, "Temporary Channels"))

    print("🎥 Appending Manual YouTube.txt...")
    final_lines.extend(parse_youtube_txt())

    print("🎥 Appending Fancode...")
    final_lines.extend(fetch_and_clean_m3u(fancode_url, "Fancode"))

    with open(output_file, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print(f"🎉 DONE. Local Star/NatGeo: {stats['local']} | Replaced Sony/Zee: {stats['skipped']}")

if __name__ == "__main__":
    update_playlist()
