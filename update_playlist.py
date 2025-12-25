import requests
import re

# ==========================================
# FILES configuration
# ==========================================
template_file = "template.m3u"
youtube_file = "youtube.txt"
reference_file = "jiotv_playlist.m3u.m3u8"
output_file = "playlist.m3u"

# SOURCES
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
jiotv_base_url = "http://192.168.0.146:5350/live" 

# PLAYER SETTINGS
user_agent = 'http-user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"'
# ==========================================

def load_reference_ids(ref_file):
    id_map = {}
    try:
        with open(ref_file, "r", encoding="utf-8") as f:
            content = f.read()
        pattern = r'tvg-id="(\d+)".*?tvg-name="([^"]+)"'
        matches = re.findall(pattern, content)
        for ch_id, ch_name in matches:
            id_map[ch_name.strip()] = ch_id
        print(f"✅ Reference Loaded: {len(id_map)} channels.")
        return id_map
    except FileNotFoundError:
        print(f"❌ ERROR: {ref_file} not found.")
        return {}

def parse_youtube_file():
    yt_lines = []
    try:
        with open(youtube_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Split by blocks separated by newlines or process line by line
        # We look for blocks of Title, Logo, Link
        entries = content.split("\n\n") # Assuming empty line between channels is safer, or we parse generally
        
        # More robust parsing: find all blocks
        # Regex to find blocks like "Title : ... \n Logo : ... \n Link : ..."
        # This regex handles variations in spacing
        pattern = r"Title\s*:\s*(.*?)\n.*?Logo\s*:\s*(.*?)\n.*?Link\s*:\s*(.*?)(?:\n|$)"
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
        
        if not matches:
            # Fallback for single block or tight spacing
            return []

        for title, logo, link in matches:
            title = title.strip()
            logo = logo.strip()
            link = link.strip()
            
            # Clean YouTube Link (Remove query params like ?si=...)
            if "youtube.com" in link or "youtu.be" in link:
                # Extract Video ID to standardize
                vid_id_match = re.search(r'(?:v=|\/live\/|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', link)
                if vid_id_match:
                    link = f"https://www.youtube.com/watch?v={vid_id_match.group(1)}"
            
            # Create M3U Entry
            entry = f'#EXTINF:-1 group-title="YouTube" tvg-logo="{logo}" {user_agent},{title}\n{link}'
            yt_lines.append(entry)
            
        print(f"✅ YouTube: Parsed {len(yt_lines)} channels.")
        return yt_lines
        
    except FileNotFoundError:
        print("⚠️ No youtube.txt found. Skipping.")
        return []

def update_playlist():
    print("--- STARTING UPDATE ---")
    final_lines = ["#EXTM3U x-tvg-url=\"http://192.168.0.146:5350/epg.xml.gz\""]

    # 1. YOUTUBE CHANNELS (From txt file)
    yt_channels = parse_youtube_file()
    if yt_channels:
        final_lines.extend(yt_channels)

    # 2. JIOTV CHANNELS (From Template + Reference)
    channel_map = load_reference_ids(reference_file)
    if channel_map:
        try:
            with open(template_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines):
                line = line.strip()
                if line.startswith("#EXTINF"):
                    name = line.split(",")[-1].strip()
                    if name in channel_map:
                        final_lines.append(line)
                        final_lines.append(f"{jiotv_base_url}/{channel_map[name]}.m3u8")
                    else:
                        # Keep manual lines if they aren't placeholder YouTube ones
                        if "http://placeholder" not in lines[i+1]:
                             final_lines.append(line)
                             if i + 1 < len(lines) and not lines[i+1].startswith("#"):
                                final_lines.append(lines[i+1].strip())
        except FileNotFoundError:
            print("❌ Template file not found.")

    # 3. FANCODE
    try:
        response = requests.get(fancode_url)
        if response.status_code == 200:
            f_lines = response.text.splitlines()
            if f_lines and f_lines[0].startswith("#EXTM3U"): f_lines = f_lines[1:]
            final_lines.append("\n" + "\n".join(f_lines))
            print("✅ Fancode merged.")
    except:
        print("⚠️ Fancode failed.")

    # SAVE
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    print(f"🎉 Playlist Updated!")

if __name__ == "__main__":
    update_playlist()
