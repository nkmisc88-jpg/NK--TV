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
# 1. Local Server (Default for working channels)
base_url = "http://192.168.0.146:5350/live" 

# 2. FakeAll/Backup (For the 40+ broken channels)
backup_url = "https://livetv-cb7.pages.dev/hotstar"

# 3. Fancode
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# KEYWORDS TO FORCE BACKUP (Use FakeAll for these even if Local exists)
FORCE_BACKUP_KEYWORDS = [
    "star",     # Star Sports, Star Plus, Star Gold, etc.
    "zee",      # Zee Tamil, Zee TV, Zee Cinema, etc.
    "vijay",    # Star Vijay, Vijay Super
    "asianet",  # Asianet News/Movies
    "suvarna"   # Star Suvarna
]

# HEADERS & AGENTS
browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
mobile_ua = "Dalvik/2.1.0 (Linux; U; Android 9; Pixel 4 Build/PQ3A.190801.002)"

backup_headers = {
    "User-Agent": mobile_ua,
    "Accept-Encoding": "gzip"
}
# ==========================================

def clean_name_key(name):
    """Normalizes names (e.g. 'Star Sports 1 HD' == 'starsports1hd')."""
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

def load_local_map(ref_file):
    """Loads IDs from your Local JioTV file."""
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
    """Fetches the FakeAll Playlist."""
    link_map = {}
    try:
        print("🌍 Fetching FakeAll Playlist...")
        response = requests.get(url, headers=backup_headers, timeout=20)
        
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
                        # Ensure Mobile UA is attached for playback
                        if "|User-Agent" not in line:
                            line = f"{line}|User-Agent={mobile_ua}"
                        link_map[key] = line
                        current_name = ""
            print(f"✅ FakeAll Playlist: Found {len(link_map)} channels.")
        else:
            print(f"⚠️ FakeAll Error: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ Failed to fetch FakeAll: {e}")
    return link_map

def should_force_backup(name):
    """Checks if the channel belongs to the 'Broken' list (Star/Zee)."""
    norm_name = name.lower()
    for keyword in FORCE_BACKUP_KEYWORDS:
        if keyword in norm_name:
            return True
    return False

def process_manual_link(line, link):
    """Handles YouTube redirection and group renaming."""
    if 'group-title="YouTube"' in line:
        line = line.replace('group-title="YouTube"', 'group-title="Youtube and live events"')
    
    # Fix YouTube Redirection
    if "youtube.com" in link or "youtu.be" in link:
        link = link.split('|')[0]
        vid_id_match = re.search(r'(?:v=|\/live\/|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', link)
        if vid_id_match:
            vid_id = vid_id_match.group(1)
            link = f"https://www.youtube.com/watch?v={vid_id}&.m3u8|User-Agent={browser_ua}"
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
    except:
        pass
    return new_entries

def update_playlist():
    print("--- STARTING SMART HYBRID UPDATE ---")
    
    local_map = load_local_map(reference_file)
    backup_map = fetch_backup_map(backup_url)
    
    final_lines = ["#EXTM3U x-tvg-url=\"http://192.168.0.146:5350/epg.xml.gz\""]
    
    stats = {"local": 0, "backup": 0, "missing": 0}

    # 1. PROCESS THE MASTER TEMPLATE
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
                    
                    # CHECK: Is this a "Broken" channel? (Star, Zee, etc.)
                    if should_force_backup(original_name):
                        # Force check FakeAll FIRST
                        if lookup_key in backup_map:
                            final_lines.append(line)
                            final_lines.append(backup_map[lookup_key])
                            stats["backup"] += 1
                            # print(f"🔹 Forced Backup: {original_name}")
                        else:
                            # If not in backup, try local as last resort
                            if lookup_key in local_map:
                                final_lines.append(line)
                                final_lines.append(f"{base_url}/{local_map[lookup_key]}.m3u8")
                                stats["local"] += 1
                            else:
                                print(f"❌ MISSING (Forced): {original_name}")
                                stats["missing"] += 1

                    # ELSE: It is a "Safe" channel (Sun, KTV, News)
                    else:
                        if lookup_key in local_map:
                            final_lines.append(line)
                            final_lines.append(f"{base_url}/{local_map[lookup_key]}.m3u8")
                            stats["local"] += 1
                        elif lookup_key in backup_map:
                             # Fallback if local is genuinely missing
                            final_lines.append(line)
                            final_lines.append(backup_map[lookup_key])
                            stats["backup"] += 1
                        else:
                            print(f"❌ MISSING (Safe): {original_name}")
                            stats["missing"] += 1

                elif url and not url.startswith("#"):
                    processed = process_manual_link(line, url)
                    final_lines.extend(processed)
    except FileNotFoundError:
        print("Template missing!")

    # 2. ADD YOUTUBE
    final_lines.extend(parse_youtube_txt())

    # 3. ADD FANCODE
    try:
        r = requests.get(fancode_url)
        if r.status_code == 200:
            flines = r.text.splitlines()
            if flines and flines[0].startswith("#EXTM3U"): flines = flines[1:]
            final_lines.append("\n" + "\n".join(flines))
            print("✅ Fancode merged.")
    except:
        pass

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print("\n🎉 UPDATE SUMMARY:")
    print(f"   - Local JioTV (Safe Channels): {stats['local']}")
    print(f"   - FakeAll (Forced Star/Zee + Backups): {stats['backup']}")
    print(f"   - Missing: {stats['missing']}")

if __name__ == "__main__":
    update_playlist()
