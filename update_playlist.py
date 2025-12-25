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

def process_manual_link(line, link):
    """Handles Group Renaming, YouTube User-Agent, and Direct Links."""
    
    # 1. Rename Group to "Youtube and live events"
    if 'group-title="YouTube"' in line:
        line = line.replace('group-title="YouTube"', 'group-title="Youtube and live events"')
    
    # 2. If it's a YouTube Link -> Add User-Agent to stop redirect
    if "youtube.com" in link or "youtu.be" in link:
        if 'http-user-agent' not in line.lower():
            # Insert UA before the comma
            parts = line.rsplit(',', 1)
            if len(parts) == 2:
                line = f'{parts[0]} http-user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",{parts[1]}'
    
    # 3. If it's a Direct Link (m3u8, mp4) -> Keep as is (Group is already renamed above)
    
    return [line, link]

def parse_youtube_txt():
    """Parses youtube.txt for Title/Logo/Link blocks."""
    new_entries = []
    try:
        with open(youtube_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Regex to find Title : ... Logo : ... Link : ...
        pattern = r"Title\s*:\s*(.*?)\n.*?Logo\s*:\s*(.*?)\n.*?Link\s*:\s*(.*?)(?:\n|$)"
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
        
        for title, logo, link in matches:
            title = title.strip()
            logo = logo.strip()
            link = link.strip()
            
            # Create EXTINF line with NEW Group Name
            line = f'#EXTINF:-1 group-title="Youtube and live events" tvg-logo="{logo}",{title}'
            
            # Process (Add UA if YouTube, leave alone if m3u8)
            processed_entry = process_manual_link(line, link)
            new_entries.extend(processed_entry)
            
        print(f"✅ youtube.txt: Parsed {len(matches)} links.")
        return new_entries
    except FileNotFoundError:
        return []

def update_playlist():
    print("--- STARTING UPDATE ---")
    
    # 1. Load Maps
    channel_map = load_reference_ids(reference_file)
    final_lines = ["#EXTM3U x-tvg-url=\"http://192.168.0.146:5350/epg.xml.gz\""]

    # 2. Process Template (JioTV + Existing Manual Links)
    try:
        with open(template_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            line = line.strip()
            
            if line.startswith("#EXTINF"):
                # Grab the URL from the next line
                url = ""
                if i + 1 < len(lines):
                    url = lines[i+1].strip()

                # LOGIC:
                # A) If Placeholder -> Try to find JioTV ID
                if "http://placeholder" in url:
                    name_parts = line.split(",")[-1].strip()
                    lookup_name = name_parts.lower()
                    if channel_map and lookup_name in channel_map:
                        final_lines.append(line)
                        final_lines.append(f"{base_url}/{channel_map[lookup_name]}.m3u8")
                    else:
                        print(f"⚠️ Missing ID for: {name_parts}")

                # B) If Manual Link (YouTube OR Direct m3u8)
                elif url and not url.startswith("#"):
                    # Process it (Rename Group, Add UA if YouTube)
                    processed = process_manual_link(line, url)
                    final_lines.extend(processed)

    except FileNotFoundError:
        print(f"❌ ERROR: {template_file} not found!")

    # 3. Process youtube.txt (Extra Links)
    txt_links = parse_youtube_txt()
    if txt_links:
        final_lines.extend(txt_links)

    # 4. Add Fancode
    try:
        response = requests.get(fancode_url)
        if response.status_code == 200:
            f_lines = response.text.splitlines()
            if f_lines and f_lines[0].startswith("#EXTM3U"): f_lines = f_lines[1:]
            final_lines.append("\n" + "\n".join(f_lines))
            print("✅ Fancode merged.")
    except:
        print("⚠️ Fancode failed.")

    # 5. Save
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    print(f"🎉 Playlist Updated Successfully!")

if __name__ == "__main__":
    update_playlist()
