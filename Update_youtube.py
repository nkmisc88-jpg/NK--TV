import requests
import re
import datetime
import os
import json

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"
youtube_file = "youtube.txt"
reference_file = "jiotv_playlist.m3u.m3u8"
output_file = "playlist.m3u"

# APP SOURCE (Community Maintained JSON for NetMirror)
# We use the raw GitHub link that the CloudStream extension uses.
EXTERNAL_APP_URL = "https://raw.githubusercontent.com/Sushan64/NetMirror-Extension/refs/heads/builds/Netflix.json"

# EXTERNAL SOURCES
base_url = "http://192.168.0.146:5350/live" 
backup_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# REMOVAL LIST
REMOVE_KEYWORDS = ["sony ten", "sonyten", "star sports 1", "star sports 2", "zee thirai"]
FORCE_BACKUP_KEYWORDS = ["star", "zee", "vijay", "asianet", "suvarna", "maa", "hotstar", "sony"]
NAME_OVERRIDES = {"star sports 2 hindi hd": "Sports18 1 HD"} 

# ==========================================
# 1. NETMIRROR SCRAPER (Community Source)
# ==========================================
def fetch_app_videos():
    entries = []
    print(f"📱 Fetching NetMirror Data from Community Repo...")
    try:
        r = requests.get(EXTERNAL_APP_URL, timeout=15)
        if r.status_code == 200:
            try:
                # The file is likely a JSON list of objects
                data = r.json()
                
                # Handle different JSON structures
                # Sometimes it's a list, sometimes it's {"data": [...]}
                items = data if isinstance(data, list) else data.get('data', [])
                
                count = 0
                for item in items:
                    # Extract fields based on common CloudStream JSON format
                    name = item.get('name') or item.get('title') or item.get('label')
                    url = item.get('url') or item.get('stream') or item.get('source')
                    logo = item.get('poster') or item.get('icon') or item.get('image') or ""
                    
                    if name and url:
                        # Clean up the name
                        name = name.replace("NetMirror", "").strip()
                        entries.append(f'#EXTINF:-1 group-title="NetMirror Movies" tvg-logo="{logo}",{name}\n{url}')
                        count += 1
                
                print(f"   ✅ Found {count} videos from NetMirror source.")
            except json.JSONDecodeError:
                print("   ⚠️ Source is not valid JSON. Trying line-by-line.")
    except Exception as e:
        print(f"   ❌ Failed to fetch App Data: {e}")
    
    return entries

# ==========================================
# 2. YOUTUBE PARSER (Stable & Direct)
# ==========================================
def parse_youtube_txt():
    new_entries = []
    if not os.path.exists(youtube_file): return []
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
    use_worker = True
    if "no" in data.get('worker', '').lower(): use_worker = False

    final_link = link
    if ("youtube.com" in link or "youtu.be" in link) and use_worker:
        vid_match = re.search(r'(?:v=|\/live\/|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', link)
        if vid_match:
            final_link = f"https://youtube.jitendraunatti.workers.dev/wanda.m3u8?id={vid_match.group(1)}"
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

    # 1. READ TEMPLATE
    try:
        with open(template_file, "r", encoding="utf-8") as f: 
            for line in f:
                if "youtube" not in line.lower(): final_lines.append(line.strip())
    except: pass

    # 2. APPEND YOUTUBE
    print("🎥 Appending Youtube...")
    final_lines.extend(parse_youtube_txt())

    # 3. APPEND APP VIDEOS (NETMIRROR)
    app_videos = fetch_app_videos()
    if app_videos:
        final_lines.append("")
        final_lines.extend(app_videos)

    # 4. APPEND FANCODE
    try:
        r = requests.get(fancode_url)
        if r.status_code == 200:
            flines = r.text.splitlines()
            if flines and flines[0].startswith("#EXTM3U"): flines = flines[1:]
            final_lines.append("\n" + "\n".join(flines))
            print("✅ Fancode merged.")
    except: pass

    with open(output_file, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print("🎉 DONE")

if __name__ == "__main__":
    update_playlist()
