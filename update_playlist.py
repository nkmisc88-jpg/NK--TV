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

# LOCAL SERVER (Star Sports / Nat Geo)
base_url = "http://192.168.0.146:5350/live" 

# EXTERNAL BACKUPS (Sony/Zee/Fancode)
sony_m3u = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
zee_m3u = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# EPG HEADER
EPG_HEADER = '#EXTM3U x-tvg-url="http://192.168.0.146:5350/epg.xml.gz,https://avkb.short.gy/epg.xml.gz,https://www.tsepg.cf/epg.xml.gz"'

# LOGO LIBRARY (Kept since it's already there)
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
    "star sports 1 hd": {"id": "Star Sports 1 HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Star_Sports_1_HD.png"},
    "star sports 2 hd": {"id": "Star Sports 2 HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Star_Sports_2_HD.png"},
    "star sports 1 hindi": {"id": "Star Sports 1 Hindi HD", "logo": "https://jiotvimages.cdn.jio.com/dare_images/images/Star_Sports_1_Hindi_HD.png"},
}

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

def enrich_metadata(line, channel_name):
    clean_name = clean_name_key(channel_name)
    meta = None
    for k, v in CHANNEL_META.items():
        if k in clean_name: 
            meta = v; break
            
    if meta:
        if 'tvg-logo=' in line:
            line = re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{meta["logo"]}"', line)
        else:
            line = line.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-logo="{meta["logo"]}"')
            
        if 'tvg-id=' in line:
             line = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{meta["id"]}"', line)
        else:
             line = line.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-id="{meta["id"]}"')
    return line

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
# 2. FETCHERS
# ==========================================
def fetch_and_group_m3u(url, group_name):
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
                    # FORCE THE GROUP NAME
                    line = re.sub(r'group-title="[^"]*"', '', line)
                    line = line.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group_name}"')
                    
                    # Fix Meta
                    name = line.split(",")[-1].strip()
                    line = enrich_metadata(line, name)
                entries.append(line)
            print(f"✅ Merged into {group_name}.")
    except: pass
    return entries

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

# ==========================================
# 3. MAIN EXECUTION
# ==========================================
def update_playlist():
    print("--- STARTING UPDATE ---")
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_lines = [EPG_HEADER, f"# Updated on: {current_time}"]
    
    local_map = load_local_map(reference_file)
    stats = {"local": 0, "skipped": 0}

    # 1. PROCESS TEMPLATE (Safe Mode - Just Map, Don't Delete)
    try:
        with open(template_file, "r", encoding="utf-8") as f: lines = f.readlines()
        skip_next_url = False 
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line: continue
            
            if line.startswith("#EXTINF"):
                # Clean up old temporary groups from the template
                lower = line.lower()
                if 'group-title="live events' in lower or 'group-title="temporary' in lower or 'group-title="pocket' in lower:
                    skip_next_url = True; continue

                skip_next_url = False
                original_name = line.split(",")[-1].strip()
                ch_name_lower = original_name.lower()
                
                # Apply Logos/EPG
                line = enrich_metadata(line, original_name)

                if i + 1 < len(lines) and "http://placeholder" in lines[i+1]:
                    clean_key = clean_name_key(original_name)
                    mapped_key = clean_name_key(NAME_OVERRIDES.get(ch_name_lower, ""))
                    
                    # Try to map to LOCAL JioTV
                    if clean_key in local_map:
                         final_lines.append(line); final_lines.append(f"{base_url}/{local_map[clean_key]}.m3u8")
                         skip_next_url = True; stats["local"] += 1
                    elif mapped_key and mapped_key in local_map:
                         final_lines.append(line); final_lines.append(f"{base_url}/{local_map[mapped_key]}.m3u8")
                         skip_next_url = True; stats["local"] += 1
                    else:
                         # Keep placeholder if local missing
                         final_lines.append(line); final_lines.append(f"{base_url}/000.m3u8")
                         skip_next_url = True
                else:
                    final_lines.append(line)
            elif not line.startswith("#"):
                if skip_next_url: skip_next_url = False
                else: final_lines.append(line)
    except FileNotFoundError: pass

    # 2. APPEND EXTERNAL GROUPS (All merged into "Live Events")
    print("🎥 Appending Fancode -> Live Events")
    final_lines.extend(fetch_and_group_m3u(fancode_url, "Live Events"))
    
    print("🎥 Appending Sony Backup -> Live Events")
    final_lines.extend(fetch_and_group_m3u(sony_m3u, "Live Events"))
    
    print("🎥 Appending Zee Backup -> Live Events")
    final_lines.extend(fetch_and_group_m3u(zee_m3u, "Live Events"))

    # 3. APPEND MANUAL TEXT (Kept separate for easy finding)
    print("🎥 Appending Manual Channels...")
    final_lines.extend(parse_youtube_txt())

    with open(output_file, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print(f"🎉 DONE. Local: {stats['local']} | External: Merged to 'Live Events'")

if __name__ == "__main__":
    update_playlist()