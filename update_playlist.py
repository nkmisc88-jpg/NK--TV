import requests
import re
import datetime
import os

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"
youtube_file = "youtube.txt"
reference_file = "jiotv_playlist.m3u.m3u8"
output_file = "playlist.m3u"

# EXTERNAL SOURCES (JioTV & Backup)
base_url = "http://192.168.0.146:5350/live" 
backup_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# CLEANUP LISTS
REMOVE_KEYWORDS = ["sony ten", "sonyten", "star sports 1", "star sports 2", "zee thirai"]
NAME_OVERRIDES = {"star sports 2 hindi hd": "Sports18 1 HD"} 

# ==========================================
# 1. TEMPORARY CHANNELS PARSER
# ==========================================

def parse_youtube_txt():
    """
    Reads youtube.txt.
    - YouTube Link -> Converts to Jitendra Worker.
    - Media Link (m3u8/mp4) -> Keeps EXACTLY as is.
    - Section Name -> "Temporary Channels"
    """
    new_entries = []
    
    if not os.path.exists(youtube_file):
        print(f"❌ Error: {youtube_file} NOT FOUND.")
        return []

    print(f"📂 Reading {youtube_file}...")
    
    with open(youtube_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_entry = {}
    
    for line in lines:
        line = line.strip()
        if not line: 
            if 'link' in current_entry:
                new_entries.append(process_entry(current_entry))
            current_entry = {} 
            continue

        if ':' in line:
            parts = line.split(':', 1)
            key = parts[0].strip().lower()
            val = parts[1].strip()
            current_entry[key] = val
    
    if 'link' in current_entry:
        new_entries.append(process_entry(current_entry))

    print(f"✅ Temporary Channels: Parsed {len(new_entries)} entries.")
    return new_entries

def process_entry(data):
    title = data.get('title', 'Unknown Channel')
    logo = data.get('logo', '')
    link = data.get('link', '')
    
    # 1. Check if it is YouTube
    if "youtube.com" in link or "youtu.be" in link:
        # Extract the ID
        vid_match = re.search(r'(?:v=|\/live\/|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', link)
        if vid_match:
            vid_id = vid_match.group(1)
            # FORCE JITENDRA SCRIPT
            final_link = f"https://youtube.jitendraunatti.workers.dev/wanda.m3u8?id={vid_id}"
            print(f"   ✨ YouTube Converted: {title}")
        else:
            # Fallback if ID extraction fails (keeps original)
            final_link = link
            print(f"   ⚠️ YouTube ID missing, keeping original: {title}")
            
    else:
        # 2. Not YouTube? Keep it EXACTLY as it is.
        final_link = link
        print(f"   ▶️  Media Link: {title}")

    # Set Group Title to "Temporary Channels"
    return f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{logo}",{title}\n{final_link}'

# ==========================================
# 2. EXISTING LOGIC (JioTV / Backup)
# ==========================================
# (I am hiding the helper functions to keep this clean, 
#  but they are needed. Ensure 'clean_name_key' etc are included if you wiped the file.
#  If you just copy-paste, I will include the MINIMUM required helpers below.)

def clean_name_key(name):
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

def load_local_map(ref_file):
    id_map = {}
    try:
        with open(ref_file, "r", encoding="utf-8") as f: content = f.read()
        pattern = r'tvg-id="(\d+)".*?tvg-name="([^"]+)"'
        matches = re.findall(pattern, content)
        for ch_id, ch_name in matches:
            id_map[clean_name_key(ch_name)] = ch_id
    except: pass
    return id_map

# ==========================================
# MAIN EXECUTION
# ==========================================

def update_playlist():
    print("--- STARTING UPDATE ---")
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_lines = [
        "#EXTM3U x-tvg-url=\"http://192.168.0.146:5350/epg.xml.gz\"",
        f"# Updated on: {current_time}"
    ]

    # 1. READ TEMPLATE (SKIP old "Youtube" sections to prevent duplicates)
    try:
        with open(template_file, "r", encoding="utf-8") as f: 
            for line in f:
                # Filter out old group titles if they exist in template
                if 'group-title="Youtube' not in line and 'group-title="Temporary' not in line:
                    final_lines.append(line.strip())
    except: pass

    # 2. APPEND TEMPORARY CHANNELS (From text file)
    print("🎥 Appending Temporary Channels...")
    final_lines.extend(parse_youtube_txt())

    # 3. APPEND FANCODE (Optional)
    try:
        r = requests.get(fancode_url)
        if r.status_code == 200:
            flines = r.text.splitlines()
            if flines and flines[0].startswith("#EXTM3U"): flines = flines[1:]
            final_lines.append("\n" + "\n".join(flines))
            print("✅ Fancode merged.")
    except: pass

    with open(output_file, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print(f"\n🎉 DONE. Playlist Saved.")

if __name__ == "__main__":
    update_playlist()
