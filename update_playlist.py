import requests
import re
import datetime
import os

# ==========================================
# 1. SETUP
# ==========================================
template_file = "template.m3u"
youtube_file = "youtube.txt"
output_file = "playlist.m3u"

# Priority 1: Arunjunan20 (Pocket TV)
URL_ARUN = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/refs/heads/main/index.html"
# Priority 2: Fakeall (Backup)
URL_FAKEALL = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"

# Live Events
URL_FANCODE = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
URL_SONY_LIVE = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
URL_ZEE_LIVE = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# Headers
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def clean_for_match(name):
    """
    Simplifies name for comparison.
    'Star Sports 1 HD' -> 'starsports1hd'
    """
    if not name: return ""
    # Remove things in brackets like (Backup) or [HD] to matching core name
    name_clean = re.sub(r'\(.*?\)|\[.*?\]', '', name)
    return re.sub(r'[^a-z0-9]', '', name_clean.lower())

def load_playlist_data(url):
    """
    Loads playlist into a list of dicts for easier scanning.
    """
    print(f"📥 Loading {url}...")
    channels = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            lines = r.text.splitlines()
            for i in range(len(lines)):
                line = lines[i].strip()
                if line.startswith("#EXTINF"):
                    # Extract Name
                    raw_name = line.split(",")[-1].strip()
                    clean_name = clean_for_match(raw_name)
                    
                    # Extract Logo
                    logo = ""
                    match_logo = re.search(r'tvg-logo="([^"]*)"', line)
                    if match_logo: logo = match_logo.group(1)

                    # Extract Link
                    link = ""
                    if i + 1 < len(lines):
                        next_line = lines[i+1].strip()
                        if next_line and not next_line.startswith("#"):
                            link = next_line
                    
                    if clean_name and link:
                        channels.append({
                            'clean_name': clean_name,
                            'raw_name': raw_name,
                            'link': link,
                            'logo': logo
                        })
        print(f"   ✅ Loaded {len(channels)} channels.")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    return channels

def find_channel_in_list(target_clean_name, channel_list):
    """
    Scans the list. Returns the FIRST entry where:
    1. The names match exactly.
    2. OR the source name contains the target name.
    """
    # Pass 1: Exact Match
    for ch in channel_list:
        if ch['clean_name'] == target_clean_name:
            return ch
            
    # Pass 2: Containment Match (Target inside Source)
    # e.g. Target: "suntvhd" -> Source: "suntvhdbackup"
    for ch in channel_list:
        if target_clean_name in ch['clean_name']:
            return ch
            
    return None

# ==========================================
# 3. MAIN SCRIPT
# ==========================================
def main():
    # 1. Load Sources
    ARUN_LIST = load_playlist_data(URL_ARUN)
    FAKEALL_LIST = load_playlist_data(URL_FAKEALL)

    final_lines = ['#EXTM3U x-tvg-url="http://192.168.0.146:5350/epg.xml.gz"']
    
    # Time
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines.append(f'#EXTINF:-1 group-title="Update Info" tvg-logo="https://i.imgur.com/7Xj4G6d.png",🟡 Updated: {ist_now.strftime("%d-%m-%Y %H:%M")}')
    final_lines.append("http://0.0.0.0")

    # 2. Process Template
    print("\n🔨 Processing Template...")
    if os.path.exists(template_file):
        with open(template_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF"):
                # Parse Target
                target_name = line.split(",")[-1].strip()
                target_clean = clean_for_match(target_name)
                
                # Get Group
                group_match = re.search(r'group-title="([^"]*)"', line)
                group = group_match.group(1) if group_match else "General"

                # SEARCH: Arun -> Fakeall
                match = find_channel_in_list(target_clean, ARUN_LIST)
                if not match:
                    match = find_channel_in_list(target_clean, FAKEALL_LIST)
                
                # Result
                logo = ""
                link = ""
                
                if match:
                    link = match['link']
                    logo = match['logo']
                
                # Fallback Logo from Template
                if not logo:
                    tmpl_logo = re.search(r'tvg-logo="([^"]*)"', line)
                    if tmpl_logo: logo = tmpl_logo.group(1)
                
                logo_str = f'tvg-logo="{logo}"' if logo else 'tvg-logo=""'

                if link:
                    final_lines.append(f'#EXTINF:-1 group-title="{group}" {logo_str},{target_name}')
                    final_lines.append(link)
                else:
                    print(f"   ⚠️ Could not find: {target_name}")
                    final_lines.append(f'#EXTINF:-1 group-title="{group}" {logo_str},⚠️ Check Source: {target_name}')
                    final_lines.append("http://0.0.0.0")
    else:
        print("❌ Template Missing")

    # 3. Add Live Events
    print("\n🎥 Adding Live Events...")
    def add_live(url):
        raw_list = load_playlist_data(url)
        for ch in raw_list:
            final_lines.append(f'#EXTINF:-1 group-title="Live Events" tvg-logo="{ch["logo"]}",{ch["raw_name"]}')
            final_lines.append(ch['link'])

    add_live(URL_FANCODE)
    add_live(URL_SONY_LIVE)
    add_live(URL_ZEE_LIVE)

    # 4. Add Manual
    print("\n🎥 Adding Manual...")
    if os.path.exists(youtube_file):
        with open(youtube_file, "r") as f:
            yt_lines = f.readlines()
        current_title = ""
        current_logo = ""
        for line in yt_lines:
            line = line.strip()
            if line.lower().startswith("title:"):
                current_title = line.split(":", 1)[1].strip()
            elif line.lower().startswith("logo:"):
                current_logo = line.split(":", 1)[1].strip()
            elif line.lower().startswith("link:") or line.startswith("http"):
                link = line.split(":", 1)[1].strip() if "link:" in line.lower() else line
                if current_title:
                    final_lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{current_logo}",{current_title}')
                    final_lines.append(link)
                    current_title = ""

    # 5. Save
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    print(f"✅ Saved {len(final_lines)//2} channels.")

if __name__ == "__main__":
    main()
