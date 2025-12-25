import requests
import re

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"
youtube_file = "youtube.txt"
reference_file = "jiotv_playlist.m3u.m3u8"
output_file = "playlist.m3u"

# FALLBACK SOURCE (For missing Star/Zee/Sony channels)
denver_url = "https://game.denver1769.fun/Jtv/5ojnFp/Playlist.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# LOCAL SERVER
base_url = "http://192.168.0.146:5350/live" 

# Player Config - Standard Browser Agent
user_agent_str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
# ==========================================

def clean_name_key(name):
    """Normalizes names to match 'Star Sports 1 HD' with 'Star Sports 1 HD '."""
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name) # Remove brackets
    name = re.sub(r'[^a-zA-Z0-9]', '', name)    # Remove special chars
    return name.lower().strip()

def load_local_map(ref_file):
    """Loads IDs from your uploaded JioTV file."""
    id_map = {}
    try:
        with open(ref_file, "r", encoding="utf-8") as f:
            content = f.read()
        pattern = r'tvg-id="(\d+)".*?tvg-name="([^"]+)"'
        matches = re.findall(pattern, content)
        for ch_id, ch_name in matches:
            key = clean_name_key(ch_name)
            id_map[key] = ch_id
        print(f"✅ Local JioTV: Loaded {len(id_map)} channels.")
        return id_map
    except FileNotFoundError:
        print(f"❌ ERROR: Local file '{ref_file}' not found.")
        return {}

def fetch_denver_map(url):
    """Downloads Denver playlist to fill in missing channels."""
    link_map = {}
    try:
        print("🌍 Fetching Denver Backup Playlist...")
        response = requests.get(url, timeout=20)
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
                        link_map[key] = line
                        current_name = ""
            print(f"✅ Denver Playlist: Loaded {len(link_map)} channels.")
    except Exception as e:
        print(f"⚠️ Failed to fetch Denver: {e}")
    return link_map

def process_manual_link(line, link):
    """Handles renaming groups and fixing YouTube links."""
    
    # 1. Rename Group
    if 'group-title="YouTube"' in line:
        line = line.replace('group-title="YouTube"', 'group-title="Youtube and live events"')
    
    # 2. Fix YouTube Redirection (Append User-Agent to URL)
    if ("youtube.com" in link or "youtu.be" in link):
        # Remove any existing pipe first to avoid duplication
        link = link.split('|')[0]
        # Append User-Agent using Pipe syntax (Works best for TiviMate)
        link = f"{link}|User-Agent={user_agent_str}"
            
    return [line, link]

def parse_youtube_txt():
    """Reads youtube.txt."""
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
    print("--- STARTING UPDATE ---")
    
    local_map = load_local_map(reference_file)
    denver_map = fetch_denver_map(denver_url)
    
    final_lines = ["#EXTM3U x-tvg-url=\"http://192.168.0.146:5350/epg.xml.gz\""]
    
    # 1. Process Template
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
                    
                    # PRIORITY 1: LOCAL
                    if lookup_key in local_map:
                        final_lines.append(line)
                        final_lines.append(f"{base_url}/{local_map[lookup_key]}.m3u8")
                    
                    # PRIORITY 2: DENVER BACKUP
                    elif lookup_key in denver_map:
                        final_lines.append(line)
                        final_lines.append(denver_map[lookup_key])
                        
                    else:
                        print(f"❌ MISSING: {original_name}")

                elif url and not url.startswith("#"):
                    processed = process_manual_link(line, url)
                    final_lines.extend(processed)
    except FileNotFoundError:
        print("Template not found.")

    # 2. Add YouTube/ICC
    final_lines.extend(parse_youtube_txt())

    # 3. Add Fancode
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
    print(f"🎉 Playlist Updated.")

if __name__ == "__main__":
    update_playlist()
