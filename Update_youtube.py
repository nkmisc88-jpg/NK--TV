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

# EXTERNAL SOURCES
base_url = "http://192.168.0.146:5350/live" 
backup_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# REMOVAL LIST
REMOVE_KEYWORDS = ["sony ten", "sonyten", "star sports 1", "star sports 2", "zee thirai"]
FORCE_BACKUP_KEYWORDS = ["star", "zee", "vijay", "asianet", "suvarna", "maa", "hotstar", "sony"]
NAME_OVERRIDES = {"star sports 2 hindi hd": "Sports18 1 HD"} 

# ==========================================
# STABLE PARSER (No Experiments)
# ==========================================

def parse_youtube_txt():
    new_entries = []
    if not os.path.exists(youtube_file): return []

    print(f"📂 Reading {youtube_file}...")
    with open(youtube_file, "r", encoding="utf-8") as f: lines = f.readlines()

    current_entry = {}
    for line in lines:
        line = line.strip()
        if not line: 
            if 'link' in current_entry: new_entries.append(process_entry(current_entry))
            current_entry = {} 
            continue
        if ':' in line:
            parts = line.split(':', 1)
            current_entry[parts[0].strip().lower()] = parts[1].strip()
    
    if 'link' in current_entry: new_entries.append(process_entry(current_entry))
    return new_entries

def process_entry(data):
    title = data.get('title', 'Unknown Event')
    logo = data.get('logo', '')
    link = data.get('link', '')
    
    # Simple Logic: If user writes "Worker : No", we use direct link. 
    # Otherwise, we use Jitendra (Stable).
    use_worker = True
    if "no" in data.get('worker', '').lower(): use_worker = False

    final_link = link

    if ("youtube.com" in link or "youtu.be" in link) and use_worker:
        # Extract ID and use Worker
        vid_match = re.search(r'(?:v=|\/live\/|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', link)
        if vid_match:
            vid_id = vid_match.group(1)
            final_link = f"https://youtube.jitendraunatti.workers.dev/wanda.m3u8?id={vid_id}"
            print(f"   ✨ Converted: {title}")
    else:
        print(f"   ▶️  Direct: {title}")

    return f'#EXTINF:-1 group-title="Youtube and live events" tvg-logo="{logo}",{title}\n{final_link}'

# ==========================================
# MAIN EXECUTION
# ==========================================

def update_playlist():
    print("--- STARTING UPDATE ---")
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_lines = ["#EXTM3U", f"# Updated on: {current_time}"]

    # 1. READ TEMPLATE (Keeping your clean logic)
    try:
        with open(template_file, "r", encoding="utf-8") as f: 
            for line in f:
                if "youtube" not in line.lower(): final_lines.append(line.strip())
    except: pass

    # 2. APPEND YOUTUBE
    print("🎥 Appending Youtube...")
    final_lines.extend(parse_youtube_txt())

    # 3. SAVE
    with open(output_file, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print("🎉 DONE")

if __name__ == "__main__":
    update_playlist()
