import requests
import re

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"
youtube_file = "youtube.txt"
reference_file = "jiotv_playlist.m3u.m3u8"
output_file = "playlist.m3u"

# BACKUP SOURCE (Jstar - For missing Star/Hotstar channels)
jstar_url = "https://livetv-cb7.pages.dev/hotstar"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# LOCAL SERVER BASE URL
base_url = "http://192.168.0.146:5350/live" 

# USER AGENTS
# 1. For YouTube (Browser Mode - Tricks Player)
browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

# 2. For Jstar (Mobile Mode - Required for Access)
jstar_ua = "Dalvik/2.1.0 (Linux; U; Android 9; Pixel 4 Build/PQ3A.190801.002)"
# ==========================================

def clean_name_key(name):
    """Normalizes names: 'Star Sports 1 HD' -> 'starsports1hd'"""
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

def fetch_jstar_map(url):
    """Downloads Jstar playlist to fill in missing channels."""
    link_map = {}
    headers = {"User-Agent": jstar_ua, "Accept-Encoding": "gzip"}
    try:
        print("🌍 Fetching Jstar Backup Playlist...")
        response = requests.get(url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            lines = response.text.splitlines()
            current_name = ""
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    # Jstar format usually: #EXTINF:-1 tvg-logo="...",Channel Name
                    current_name = line.split(",")[-1].strip()
                elif line and not line.startswith("#"):
                    if current_name:
                        key = clean_name_key(current_name)
                        # Append User-Agent to the link so the player can play it
                        if "|User-Agent" not in line:
                            line = f"{line}|User-Agent={jstar_ua}"
                        link_map[key] = line
                        current_name = ""
            print(f"✅ Jstar Playlist: Loaded {len(link_map)} channels.")
        else:
            print(f"⚠️ Jstar Error: Status {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ Failed to fetch Jstar: {e}")
    return link_map

def process_manual_link(line, link):
    """Handles renaming groups and FIXES YouTube redirection."""
    
    # 1. Rename Group
    if 'group-title="YouTube"' in line:
        line = line.replace('group-title="YouTube"', 'group-title="Youtube and live events"')
    
    # 2. Fix YouTube Redirection (Anti-Redirect Trick)
    if "youtube.com" in link or "youtu.be" in link:
        link = link.split('|')[0] # Clean pipe
        vid_id_match = re.search(r'(?:v=|\/live\/|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', link)
        if vid_id_match:
            vid_id = vid_id_match.group(1)
            # Add fake extension + User Agent
            link = f"https://www.youtube.com/watch?v={vid_id}&.m3u8|User-Agent={browser_ua}"
        else:
            link = f"{link}|User-Agent={browser_ua}"
            
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
    print("--- STARTING STRICT MASTER LIST UPDATE ---")
    
    local_map = load_local_map(reference_file)
    jstar_map = fetch_jstar_map(jstar_url)
    
    final_lines = ["#EXTM3U x-tvg-url=\"http://192.168.0.146:5350/epg.xml.gz\""]
    
    matched_local = 0
    matched_backup = 0
    missing_count = 0

    # 1. Process Template (THE MASTER LIST)
    try:
        with open(template_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("#EXTINF"):
                url = ""
                if i + 1 < len(lines): url = lines[i+1].strip()

                # Logic for Channels (Placeholders)
                if "http://placeholder" in url:
                    original_name = line.split(",")[-1].strip()
                    lookup_key = clean_name_key(original_name)
                    
                    # PRIORITY 1: LOCAL JIO (Fastest)
                    if lookup_key in local_map:
                        final_lines.append(line)
                        final_lines.append(f"{base_url}/{local_map[lookup_key]}.m3u8")
                        matched_local += 1
                    
                    # PRIORITY 2: JSTAR BACKUP (Only for missing channels)
                    elif lookup_key in jstar_map:
                        print(f"🔹 Backup Used: {original_name}")
                        final_lines.append(line) # Use OUR Group/Logo
                        final_lines.append(jstar_map[lookup_key]) # Use THEIR Link
                        matched_backup += 1
                        
                    else:
                        print(f"❌ MISSING: {original_name}")
                        missing_count += 1

                # Logic for existing manual links (YouTube etc in template)
                elif url and not url.startswith("#"):
                    processed = process_manual_link(line, url)
                    final_lines.extend(processed)
    except FileNotFoundError:
        print("Template not found.")

    # 2. Add YouTube/ICC from Text File
    final_lines.extend(parse_youtube_txt())

    # 3. Add Fancode (Separate Section)
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
    
    print(f"\n🎉 UPDATE COMPLETE")
    print(f"   - Local JioTV Matches: {matched_local}")
    print(f"   - Backup (Jstar) Matches: {matched_backup}")
    print(f"   - Still Missing: {missing_count}")

if __name__ == "__main__":
    update_playlist()
