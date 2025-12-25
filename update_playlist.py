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
denver_url = "https://game.denver1769.fun/Jtv/5ojnFp/Playlist.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
base_url = "http://192.168.0.146:5350/live" 

# CONFIG
direct_ua = 'http-user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"'
# ==========================================

def clean_name_key(name):
    """Normalizes names (lowercase, remove spaces/special chars) for better matching."""
    # Remove everything inside brackets like [HD] or (Live)
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    # Remove special chars and extra spaces
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

def load_local_map(ref_file):
    """Loads Local JioTV Go channels."""
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
        print(f"❌ ERROR: Local reference file '{ref_file}' not found.")
        return {}

def fetch_denver_map(url):
    """Fetches and parses the Denver Playlist for missing channels."""
    url_map = {}
    try:
        print(f"🌍 Fetching Denver Playlist...")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        current_name = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF"):
                # Extract name after the last comma
                current_name = line.split(",")[-1].strip()
            elif line and not line.startswith("#"):
                if current_name:
                    key = clean_name_key(current_name)
                    url_map[key] = line
                    current_name = "" # Reset
                    
        print(f"✅ Denver Playlist: Loaded {len(url_map)} channels.")
        return url_map
    except Exception as e:
        print(f"⚠️ Denver fetch failed: {e}")
        return {}

def process_manual_link(line, link):
    """Handles renaming groups and adding User-Agent for YouTube."""
    if 'group-title="YouTube"' in line:
        line = line.replace('group-title="YouTube"', 'group-title="Youtube and live events"')
    
    # Add User-Agent for YouTube
    if ("youtube.com" in link or "youtu.be" in link) and 'http-user-agent' not in line.lower():
        parts = line.rsplit(',', 1)
        if len(parts) == 2:
            line = f'{parts[0]} {direct_ua},{parts[1]}'
            
    return [line, link]

def parse_youtube_txt():
    """Parses youtube.txt blocks."""
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
                    key, val = row.split(':', 1)
                    data[key.strip().lower()] = val.strip()
            
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
            
        return new_entries
    except FileNotFoundError:
        return []

def update_playlist():
    print("--- STARTING HYBRID UPDATE ---")
    
    # 1. Load Sources
    local_map = load_local_map(reference_file)
    denver_map = fetch_denver_map(denver_url)
    
    final_lines = ["#EXTM3U x-tvg-url=\"http://192.168.0.146:5350/epg.xml.gz\""]
    matched_local = 0
    matched_denver = 0
    missing_count = 0

    # 2. Process Template
    try:
        with open(template_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            line = line.strip()
            
            if line.startswith("#EXTINF"):
                url = ""
                if i + 1 < len(lines): url = lines[i+1].strip()

                # Logic for Channels
                if "http://placeholder" in url:
                    original_name = line.split(",")[-1].strip()
                    lookup_key = clean_name_key(original_name)
                    
                    # PRIORITY 1: Local JioTV
                    if lookup_key in local_map:
                        final_lines.append(line)
                        final_lines.append(f"{base_url}/{local_map[lookup_key]}.m3u8")
                        matched_local += 1
                        
                    # PRIORITY 2: Denver Fallback
                    elif lookup_key in denver_map:
                        final_lines.append(line) # Keep our logo/group
                        final_lines.append(denver_map[lookup_key]) # Use their link
                        matched_denver += 1
                        print(f"🔹 Fallback used for: {original_name}")
                        
                    else:
                        print(f"❌ MISSING: {original_name}")
                        missing_count += 1

                # Logic for Manual Links (YouTube/Direct)
                elif url and not url.startswith("#"):
                    processed = process_manual_link(line, url)
                    final_lines.extend(processed)
                    
    except FileNotFoundError:
        print(f"❌ ERROR: {template_file} not found!")

    # 3. Add Youtube.txt
    txt_links = parse_youtube_txt()
    if txt_links: final_lines.extend(txt_links)

    # 4. Add Fancode
    try:
        response = requests.get(fancode_url)
        if response.status_code == 200:
            f_lines = response.text.splitlines()
            if f_lines and f_lines[0].startswith("#EXTM3U"): f_lines = f_lines[1:]
            final_lines.append("\n" + "\n".join(f_lines))
    except:
        pass

    # 5. Save
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print(f"\n🎉 DONE! Stats:")
    print(f"   - Local JioTV Matches: {matched_local}")
    print(f"   - Denver Fallback Matches: {matched_denver}")
    print(f"   - Still Missing: {missing_count}")

if __name__ == "__main__":
    update_playlist()
