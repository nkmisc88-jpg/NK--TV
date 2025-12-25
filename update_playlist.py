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
# 1. Local JioTV (Priority 1 - Safe Channels)
base_url = "http://192.168.0.146:5350/live" 

# 2. FakeAll/Backup (Priority 2 - Star/Zee/Asianet)
backup_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"

# 3. Fancode
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# CHANNELS TO FORCE FROM BACKUP
FORCE_BACKUP_KEYWORDS = [
    "star", "zee", "vijay", "asianet", "suvarna", "maa", "hotstar"
]

# USER AGENTS
# Agent A: For YouTube (Tricks TiviMate to play internally)
ua_browser = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

# Agent B: For FakeAll/Jio streams (REQUIRED for playback)
ua_mobile = "Dalvik/2.1.0 (Linux; U; Android 9; Pixel 4 Build/PQ3A.190801.002)"

# ==========================================

def clean_name_key(name):
    """Normalizes names (e.g. 'Star Sports 1 HD' -> 'starsports1hd')."""
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

def fuzzy_find(target_key, map_keys):
    """Finds a key even if it's slightly different."""
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
    """Fetches the FakeAll Playlist and prepares links."""
    link_map = {}
    try:
        print("🌍 Fetching FakeAll Backup...")
        # Use Browser UA to fetch the FILE itself (GitHub allows this)
        response = requests.get(url, headers={"User-Agent": ua_browser}, timeout=20)
        
        if response.status_code == 200:
            lines = response.text.splitlines()
            current_name = ""
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    current_name = line.split(",")[-1].strip()
                elif line and not line.startswith("#"):
                    if current_name:
                        key = clean_name_key(current_name)
                        
                        # CRITICAL FIX: Ensure Link has Mobile UA attached for playback
                        # If the link from FakeAll doesn't have it, we append it.
                        # If it has a pipe | already, we respect it, otherwise add ours.
                        if "User-Agent" not in line:
                            clean_link = line.split('|')[0] # Safety cleaning
                            final_link = f"{clean_link}|User-Agent={ua_mobile}"
                        else:
                            final_link = line
                            
                        link_map[key] = final_link
                        current_name = ""
            print(f"✅ FakeAll Playlist: Found {len(link_map)} channels.")
        else:
            print(f"⚠️ FakeAll Error: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Failed to fetch Backup: {e}")
    return link_map

def should_force_backup(name):
    """Returns True if the channel is in the 'Broken' list."""
    norm_name = name.lower()
    for keyword in FORCE_BACKUP_KEYWORDS:
        if keyword in norm_name:
            return True
    return False

def process_manual_link(line, link):
    """Fixes YouTube redirection (Browser UA)."""
    if 'group-title="YouTube"' in line:
        line = line.replace('group-title="YouTube"', 'group-title="Youtube and live events"')
    
    if "youtube.com" in link or "youtu.be" in link:
        # Add Header for OTT Navigator
        if 'http-user-agent' not in line.lower():
            parts = line.rsplit(',', 1)
            if len(parts) == 2:
                line = f'{parts[0]} http-user-agent="{ua_browser}",{parts[1]}'
        
        # Add URL Param for TiviMate
        link = link.split('|')[0]
        vid_id_match = re.search(r'(?:v=|\/live\/|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', link)
        if vid_id_match:
            link = f"https://www.youtube.com/watch?v={vid_id_match.group(1)}&.m3u8|User-Agent={ua_browser}"
        else:
            link = f"{link}|User-Agent={ua_browser}"
            
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
    print("--- STARTING UPDATE ---")
    
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
                    found_link = None
                    
                    # 1. LOGIC: Broken Channels (Star/Zee) -> Use Backup (FakeAll)
                    if should_force_backup(original_name):
                        # Try exact match
                        if lookup_key in backup_map:
                            found_link = backup_map[lookup_key]
                        # Try Fuzzy match
                        else:
                            fuzzy_key = fuzzy_find(lookup_key, backup_map.keys())
                            if fuzzy_key:
                                found_link = backup_map[fuzzy_key]
                        
                        if found_link:
                            stats["backup"] += 1
                        # Panic Fallback: If not in FakeAll, try Local
                        elif lookup_key in local_map:
                            found_link = f"{base_url}/{local_map[lookup_key]}.m3u8"
                            stats["local"] += 1

                    # 2. LOGIC: Safe Channels (Sun/News) -> Use Local
                    else:
                        if lookup_key in local_map:
                            found_link = f"{base_url}/{local_map[lookup_key]}.m3u8"
                            stats["local"] += 1
                        # Fallback to Backup
                        elif lookup_key in backup_map:
                            found_link = backup_map[lookup_key]
                            stats["backup"] += 1

                    # 3. WRITE TO FILE
                    if found_link:
                        final_lines.append(line)
                        final_lines.append(found_link)
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
    
    print("\n🎉 UPDATE SUMMARY:")
    print(f"   - Local JioTV: {stats['local']}")
    print(f"   - FakeAll Backup: {stats['backup']}")
    print(f"   - Missing: {stats['missing']}")

if __name__ == "__main__":
    update_playlist()
