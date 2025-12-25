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

# CHANNELS TO FORCE FROM BACKUP (Broken locally)
FORCE_BACKUP_KEYWORDS = [
    "star", "zee", "vijay", "asianet", "suvarna", "maa", "hotstar", "discovery", "nat geo", "sony"
]

# Browser UA (Only for YouTube)
browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
# ==========================================

def clean_name_key(name):
    """Normalizes names."""
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

def fuzzy_find(target_key, map_keys):
    """Finds best match."""
    for key in map_keys:
        if target_key in key or key in target_key:
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
    """Fetches Backup Playlist and captures FULL BLOCKS (Headers+Links)."""
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
                
                # Start of a new channel entry
                if line.startswith("#EXTINF"):
                    # If we were building a block, save the previous one first
                    if current_name and current_block:
                        key = clean_name_key(current_name)
                        # Store everything EXCEPT the #EXTINF line itself (we use our own)
                        # We only want the URL and any #KODIPROP/#EXTVLCOPT lines
                        data_lines = [l for l in current_block if not l.startswith("#EXTINF")]
                        if data_lines:
                            block_map[key] = data_lines
                    
                    # Start new block
                    current_name = line.split(",")[-1].strip()
                    current_block = [line]
                
                # Metadata lines (Kodiprop, headers) OR URL lines
                else:
                    if current_block:
                        current_block.append(line)
            
            # Save the very last block
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
    """Checks if channel is broken locally."""
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
    print("--- STARTING FULL BLOCK UPDATE ---")
    
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
                    
                    # 1. LOGIC: Force Backup for Star/Zee/Vijay
                    if should_force_backup(original_name):
                        if lookup_key in backup_map:
                            found_block = backup_map[lookup_key]
                        else:
                            # Fuzzy Find
                            fuzzy_key = fuzzy_find(lookup_key, backup_map.keys())
                            if fuzzy_key:
                                found_block = backup_map[fuzzy_key]
                        
                        if found_block:
                            stats["backup"] += 1
                        # Fallback to local
                        elif lookup_key in local_map:
                            found_block = [f"{base_url}/{local_map[lookup_key]}.m3u8"]
                            stats["local"] += 1

                    # 2. LOGIC: Safe Channels (Sun/News)
                    else:
                        if lookup_key in local_map:
                            found_block = [f"{base_url}/{local_map[lookup_key]}.m3u8"]
                            stats["local"] += 1
                        elif lookup_key in backup_map:
                            found_block = backup_map[lookup_key]
                            stats["backup"] += 1

                    # 3. WRITE TO FILE
                    if found_block:
                        final_lines.append(line) # Our nice EXTINF
                        final_lines.extend(found_block) # Their URL + Headers + Cookies
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
