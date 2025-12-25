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

# FORCE BACKUP LIST (Includes Infotainment & Kids now)
FORCE_BACKUP_KEYWORDS = [
    # Networks
    "star", "zee", "vijay", "asianet", "suvarna", "maa", "hotstar", "sony", "set", "sab",
    # Infotainment (The missing ones)
    "discovery", "nat geo", "history", "tlc", "animal planet", "travelxp", "bbc earth",
    # Kids
    "nick", "cartoon", "pogo", "disney", "hungama", "sonic", "discovery kids", "chutti", "kochu", "kushi",
    # Movies/English
    "movies now", "mnx", "romedy", "mn+", "pix"
]

# Browser UA
browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
# ==========================================

def clean_name_key(name):
    """Normalizes names."""
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

def smart_match(target_name, map_keys):
    """
    Advanced matching:
    1. Clean Key Match (exact)
    2. Substring Match (one inside the other)
    3. Word Match (all important words must exist)
    """
    target_clean = clean_name_key(target_name)
    
    # 1. Exact/Substring Check
    for key in map_keys:
        if target_clean == key or target_clean in key or key in target_clean:
            return key
            
    # 2. Word-based Check (Fixes 'Nat Geo Wild HD' matching 'Nat Geo Wild')
    # Filter out common noise words like 'hd', 'tv', 'channel'
    ignored_words = {'hd', 'sd', 'tv', 'channel', 'network', 'live', 'in'}
    target_words = [w for w in re.split(r'\W+', target_name.lower()) if w and w not in ignored_words]
    
    if not target_words: return None

    for key in map_keys:
        # Check if ALL core words from target exist in the backup key
        if all(word in key for word in target_words):
            return key
            
    return None

def load_local_map(ref_file):
    """Loads IDs from Local JioTV."""
    id_map = {}
    try:
        with open(ref_file, "r", encoding="utf-8") as f:
            content = f.read()
        pattern = r'tvg-id="(\d+)".*?tvg-name="([^"]+)"'
        matches = re.findall(pattern, content)
        for ch_id, ch_name in matches:
            key = clean_name_key(ch_name)
            id_map[key] = ch_id
        print(f"✅ Local JioTV: Found {len(id_map)} channels.")
        return id_map
    except FileNotFoundError:
        print(f"❌ ERROR: Local file '{ref_file}' not found.")
        return {}

def fetch_backup_map(url):
    """Fetches Backup Playlist and captures FULL BLOCKS."""
    block_map = {}
    try:
        print("🌍 Fetching FakeAll Source...")
        response = requests.get(url, headers={"User-Agent": browser_ua}, timeout=20)
        
        if response.status_code == 200:
            lines = response.text.splitlines()
            current_block = []
            current_name = ""
            
            for line in lines:
                line = line.strip()
                if not line: continue
                
                if line.startswith("#EXTINF"):
                    if current_name and current_block:
                        key = clean_name_key(current_name)
                        data_lines = [l for l in current_block if not l.startswith("#EXTINF")]
                        if data_lines:
                            block_map[key] = data_lines
                    
                    current_name = line.split(",")[-1].strip()
                    current_block = [line]
                else:
                    if current_block:
                        current_block.append(line)
            
            # Save last block
            if current_name and current_block:
                key = clean_name_key(current_name)
                data_lines = [l for l in current_block if not l.startswith("#EXTINF")]
                if data_lines:
                    block_map[key] = data_lines
                    
            print(f"✅ Backup Playlist: Parsed {len(block_map)} channel blocks.")
        else:
            print(f"⚠️ Backup Error: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Failed to fetch Backup: {e}")
    return block_map

def should_force_backup(name):
    """Checks if channel is in the 'Broken' list."""
    norm_name = name.lower()
    for keyword in FORCE_BACKUP_KEYWORDS:
        if keyword in norm_name:
            return True
    return False

def process_manual_link(line, link):
    """Fixes YouTube redirection."""
    if 'group-title="YouTube"' in line:
        line = line.replace('group-title="YouTube"', 'group-title="Youtube and live events"')
    
    if "youtube.com" in link or "youtu.be" in link:
        link = link.split('|')[0]
        vid_id_match = re.search(r'(?:v=|\/live\/|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', link)
        if vid_id_match:
            link = f"https://www.youtube.com/watch?v={vid_id_match.group(1)}&.m3u8|User-Agent={browser_ua}"
        else:
            link = f"{link}|User-Agent={browser_ua}"
            
    return [line, link]

def parse_youtube_txt():
    """Parses youtube.txt."""
    new_entries = []
    try:
        with open(youtube_file, "r", encoding="utf-8") as f:
            content = f.read()
        blocks = content.split('\n\n')
        for block in blocks:
            if not block.strip(): continue
            data = {}
            for row in block.splitlines():
                if ':' in row:
                    k, v = row.split(':', 1)
                    data[k.strip().lower()] = v.strip()
            
            title = data.get('title', 'Unknown')
            logo = data.get('logo', '')
            link = data.get('link', '')
            vpn_req = data.get('vpn required', 'no').lower()
            vpn_country = data.get('vpn country', '')

            if not link: continue
            if vpn_req == 'yes':
                title = f"{title} [VPN: {vpn_country}]" if vpn_country else f"{title} [VPN Required]"

            line = f'#EXTINF:-1 group-title="Youtube and live events" tvg-logo="{logo}",{title}'
            new_entries.extend(process_manual_link(line, link))
    except: pass
    return new_entries

def update_playlist():
    print("--- STARTING SMART UPDATE ---")
    
    local_map = load_local_map(reference_file)
    backup_map = fetch_backup_map(backup_url)
    
    final_lines = ["#EXTM3U x-tvg-url=\"http://192.168.0.146:5350/epg.xml.gz\""]
    stats = {"local": 0, "backup": 0, "missing": 0}

    try:
        with open(template_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("#EXTINF"):
                url = ""
                if i + 1 < len(lines): url = lines[i+1].strip()

                if "http://placeholder" in url:
                    original_name = line.split(",")[-1].strip()
                    lookup_key = clean_name_key(original_name)
                    found_block = None
                    
                    # 1. FORCE BACKUP (Now includes Nat Geo, Discovery, etc.)
                    if should_force_backup(original_name):
                        # Use Smart Match to find "Nat Geo Wild" for "Nat Geo Wild HD"
                        match_key = smart_match(original_name, backup_map.keys())
                        
                        if match_key:
                            found_block = backup_map[match_key]
                            stats["backup"] += 1
                        elif lookup_key in local_map:
                            found_block = [f"{base_url}/{local_map[lookup_key]}.m3u8"]
                            stats["local"] += 1

                    # 2. SAFE CHANNELS
                    else:
                        if lookup_key in local_map:
                            found_block = [f"{base_url}/{local_map[lookup_key]}.m3u8"]
                            stats["local"] += 1
                        else:
                            match_key = smart_match(original_name, backup_map.keys())
                            if match_key:
                                found_block = backup_map[match_key]
                                stats["backup"] += 1

                    if found_block:
                        final_lines.append(line)
                        final_lines.extend(found_block)
                    else:
                        print(f"❌ MISSING: {original_name}")
                        stats["missing"] += 1

                elif url and not url.startswith("#"):
                    processed = process_manual_link(line, url)
                    final_lines.extend(processed)
    except FileNotFoundError:
        print("Template file missing!")

    final_lines.extend(parse_youtube_txt())

    try:
        r = requests.get(fancode_url)
        if r.status_code == 200:
            flines = r.text.splitlines()
            if flines and flines[0].startswith("#EXTM3U"): flines = flines[1:]
            final_lines.append("\n" + "\n".join(flines))
            print("✅ Fancode merged.")
    except: pass

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print("\n🎉 SUMMARY:")
    print(f"   - Local: {stats['local']}")
    print(f"   - Backup (Full Blocks): {stats['backup']}")
    print(f"   - Missing: {stats['missing']}")

if __name__ == "__main__":
    update_playlist()
