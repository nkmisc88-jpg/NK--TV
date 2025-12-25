import requests
import re

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"
youtube_file = "youtube.txt"
reference_file = "jiotv_playlist.m3u.m3u8"
output_file = "playlist.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
base_url = "http://192.168.0.146:5350/live" 

# Standard User-Agent for playing YouTube directly (No Redirect)
direct_ua = 'http-user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"'
# ==========================================

def load_reference_ids(ref_file):
    id_map = {}
    try:
        with open(ref_file, "r", encoding="utf-8") as f:
            content = f.read()
        pattern = r'tvg-id="(\d+)".*?tvg-name="([^"]+)"'
        matches = re.findall(pattern, content)
        for ch_id, ch_name in matches:
            clean_name = ch_name.strip().lower()
            id_map[clean_name] = ch_id
        print(f"✅ Reference Loaded: {len(id_map)} channels.")
        return id_map
    except FileNotFoundError:
        print(f"❌ CRITICAL ERROR: '{ref_file}' not found.")
        return {}

def process_manual_link(line, link, vpn_req=False):
    """Handles Group Renaming and User-Agents."""
    
    # 1. Rename Group to "Youtube and live events"
    if 'group-title="YouTube"' in line:
        line = line.replace('group-title="YouTube"', 'group-title="Youtube and live events"')
    
    # 2. Add User-Agent for YouTube Links to stop redirect
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
            
            title = data.get('title', 'Unknown Channel')
            logo = data.get('logo', '')
            link = data.get('link', '')
            vpn_req = data.get('vpn required', 'no').lower()
            vpn_country = data.get('vpn country', '')

            if not link: continue

            # LOGIC: Handle VPN Labeling
            is_vpn_needed = False
            if vpn_req == 'yes':
                is_vpn_needed = True
                if vpn_country:
                    title = f"{title} [VPN: {vpn_country}]"
                else:
                    title = f"{title} [VPN Required]"

            line = f'#EXTINF:-1 group-title="Youtube and live events" tvg-logo="{logo}",{title}'
            
            processed_entry = process_manual_link(line, link, is_vpn_needed)
            new_entries.extend(processed_entry)
            
        print(f"✅ youtube.txt: Parsed {len(new_entries)//2} links.")
        return new_entries
    except FileNotFoundError:
        print("⚠️ youtube.txt not found.")
        return []

def update_playlist():
    print("--- STARTING UPDATE ---")
    
    channel_map = load_reference_ids(reference_file)
    final_lines = ["#EXTM3U x-tvg-url=\"http://192.168.0.146:5350/epg.xml.gz\""]

    # 1. Process Template (JioTV + Manual)
    try:
        with open(template_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("#EXTINF"):
                url = ""
                if i + 1 < len(lines): url = lines[i+1].strip()

                if "http://placeholder" in url:
                    name = line.split(",")[-1].strip().lower()
                    if channel_map and name in channel_map:
                        final_lines.append(line)
                        final_lines.append(f"{base_url}/{channel_map[name]}.m3u8")
                    else:
                        # Optional: Print missing to help debug
                        # print(f"⚠️ Missing ID for: {name}") 
                        pass
                elif url and not url.startswith("#"):
                    processed = process_manual_link(line, url)
                    final_lines.extend(processed)
    except FileNotFoundError:
        print(f"❌ ERROR: {template_file} not found!")

    # 2. Process youtube.txt
    txt_links = parse_youtube_txt()
    if txt_links: final_lines.extend(txt_links)

    # 3. Add Fancode
    try:
        response = requests.get(fancode_url)
        if response.status_code == 200:
            f_lines = response.text.splitlines()
            if f_lines and f_lines[0].startswith("#EXTM3U"): f_lines = f_lines[1:]
            final_lines.append("\n" + "\n".join(f_lines))
            print("✅ Fancode merged.")
    except:
        print("⚠️ Fancode failed.")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    print(f"🎉 Playlist Updated!")

if __name__ == "__main__":
    update_playlist()
