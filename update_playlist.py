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

# Priority 1: Arunjunan20
URL_ARUN = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/refs/heads/main/index.html"
# Priority 2: Fakeall
URL_FAKEALL = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"

# Live Events
URL_FANCODE = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
URL_SONY_LIVE = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
URL_ZEE_LIVE = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# Headers
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}

# ==========================================
# 2. LOGIC
# ==========================================
def clean_key(name):
    """Normalize names: 'Star Sports 1 HD' -> 'starsports1hd'"""
    if not name: return ""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def load_playlist(url):
    """Downloads and parses a playlist into a dictionary."""
    print(f"📥 Loading {url}...")
    db = {}
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            lines = r.text.splitlines()
            for i in range(len(lines)):
                line = lines[i].strip()
                if line.startswith("#EXTINF"):
                    # Extract Name
                    name_part = line.split(",")[-1].strip()
                    key = clean_key(name_part)
                    
                    # Extract Logo
                    logo = ""
                    logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                    if logo_match: logo = logo_match.group(1)

                    # Extract Link (Next Line)
                    link = ""
                    if i + 1 < len(lines):
                        next_line = lines[i+1].strip()
                        if next_line and not next_line.startswith("#"):
                            link = next_line
                    
                    if key and link:
                        db[key] = {'link': link, 'logo': logo}
        print(f"   ✅ Loaded {len(db)} channels.")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    return db

def fuzzy_find(target_key, database):
    """
    Tries to find a channel even if the name isn't perfect.
    Example: 'starsports1hd' matches 'starsports1hdbackup'
    """
    # 1. Exact Match (Best)
    if target_key in database:
        return database[target_key]
    
    # 2. Containment Match (Good)
    # Check if our target key is inside a database key (or vice versa)
    for db_key in database:
        if target_key in db_key:
            return database[db_key]
            
    return None

# ==========================================
# 3. EXECUTION
# ==========================================
def main():
    # 1. Load Sources
    DB_ARUN = load_playlist(URL_ARUN)
    DB_FAKEALL = load_playlist(URL_FAKEALL)

    final_lines = ['#EXTM3U x-tvg-url="http://192.168.0.146:5350/epg.xml.gz"']
    
    # 2. Add Update Time
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines.append(f'#EXTINF:-1 group-title="Update Info" tvg-logo="https://i.imgur.com/7Xj4G6d.png",🟡 Updated: {ist_now.strftime("%d-%m-%Y %H:%M")}')
    final_lines.append("http://0.0.0.0")

    # 3. Process Template
    print("\n🔨 Processing Template...")
    if os.path.exists(template_file):
        with open(template_file, "r") as f:
            template_lines = f.readlines()
            
        for line in template_lines:
            line = line.strip()
            if line.startswith("#EXTINF"):
                # Parse Template Line
                name = line.split(",")[-1].strip()
                key = clean_key(name)
                
                # Get Group
                group_match = re.search(r'group-title="([^"]*)"', line)
                group = group_match.group(1) if group_match else "General"

                # FIND LINK (Arun -> Fakeall)
                # We use fuzzy_find to match partial names
                data = fuzzy_find(key, DB_ARUN)
                if not data:
                    data = fuzzy_find(key, DB_FAKEALL)
                
                link = None
                logo = None
                
                if data:
                    link = data['link']
                    logo = data['logo']
                
                # Use Template Logo if Source Logo is missing
                if not logo:
                    tmpl_logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                    if tmpl_logo_match: logo = tmpl_logo_match.group(1)

                logo_str = f'tvg-logo="{logo}"' if logo else 'tvg-logo=""'

                if link:
                    final_lines.append(f'#EXTINF:-1 group-title="{group}" {logo_str},{name}')
                    final_lines.append(link)
                else:
                    # If STILL not found, keep the original placeholder so it's not "Offline"
                    # But print a warning to console
                    print(f"   ⚠️ Could not find stream for: {name}")
                    final_lines.append(f'#EXTINF:-1 group-title="{group}" {logo_str},{name}')
                    final_lines.append("http://0.0.0.0") 
    else:
        print("❌ Template Missing!")

    # 4. Add Live Events
    print("\n🎥 Adding Live Events...")
    def add_live(url):
        db = load_playlist(url)
        for key, data in db.items():
            final_lines.append(f'#EXTINF:-1 group-title="Live Events" tvg-logo="{data["logo"]}",{key}')
            final_lines.append(data['link'])

    add_live(URL_FANCODE)
    add_live(URL_SONY_LIVE)
    add_live(URL_ZEE_LIVE)

    # 5. Add Manual/Youtube
    print("\n🎥 Adding Manual/Youtube...")
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

    # 6. Save
    with open(output_file, "w") as f:
        f.write("\n".join(final_lines))
    print("✅ Done.")

if __name__ == "__main__":
    main()
