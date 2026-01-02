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

# Sources
URL_ARUN = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/refs/heads/main/index.html"
URL_FAKEALL = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"

# Live Events
URL_FANCODE = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
URL_SONY_LIVE = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
URL_ZEE_LIVE = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# Headers
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}

# ==========================================
# 2. LOGIC
# ==========================================
def get_core_name(name):
    """
    Reduces name to its absolute core for matching.
    'Star Sports 1 HD (Backup)' -> 'starsports1hd'
    """
    if not name: return ""
    # Remove things in brackets
    name = re.sub(r'[\(\[\{].*?[\)\]\}]', '', name.lower())
    # Remove non-alphanumeric
    return re.sub(r'[^a-z0-9]', '', name)

def load_playlist(url, source_name):
    print(f"📥 Loading {source_name}...")
    dataset = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            lines = r.text.splitlines()
            for i in range(len(lines)):
                line = lines[i].strip()
                if line.startswith("#EXTINF"):
                    raw_name = line.split(",")[-1].strip()
                    core_name = get_core_name(raw_name)
                    
                    logo = ""
                    m = re.search(r'tvg-logo="([^"]*)"', line)
                    if m: logo = m.group(1)

                    link = ""
                    if i + 1 < len(lines):
                        potential_link = lines[i+1].strip()
                        if potential_link and not potential_link.startswith("#"):
                            link = potential_link
                            # APPEND USER-AGENT TO FIX PLAYBACK
                            if "http" in link and "|" not in link:
                                link += f"|User-Agent={USER_AGENT}"
                    
                    if link and core_name:
                        dataset.append({
                            'core_name': core_name,
                            'raw_name': raw_name, 
                            'link': link, 
                            'logo': logo
                        })
        print(f"   ✅ {source_name}: {len(dataset)} channels.")
    except Exception as e:
        print(f"   ❌ Error {source_name}: {e}")
    return dataset

def find_best_match(target_name, dataset):
    target_core = get_core_name(target_name)
    
    # 1. Exact Core Match
    for ch in dataset:
        if ch['core_name'] == target_core:
            return ch
            
    # 2. Partial Core Match (Target inside Source)
    # e.g. Target 'suntv' inside Source 'suntvhd'
    for ch in dataset:
        if target_core in ch['core_name']:
            return ch
            
    return None

# ==========================================
# 3. MAIN SCRIPT
# ==========================================
def main():
    # 1. Load Sources
    DB_ARUN = load_playlist(URL_ARUN, "Arunjunan")
    DB_FAKEALL = load_playlist(URL_FAKEALL, "Fakeall")

    final_lines = ['#EXTM3U x-tvg-url="http://192.168.0.146:5350/epg.xml.gz"']
    
    # Time
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines.append(f'#EXTINF:-1 group-title="Update Info" tvg-logo="https://i.imgur.com/7Xj4G6d.png",🟡 Updated: {ist_now.strftime("%d-%m-%Y %H:%M")}')
    final_lines.append("http://0.0.0.0")

    # 2. Process Template
    print("\n🔨 Processing Template...")
    if os.path.exists(template_file):
        with open(template_file, "r") as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF"):
                target_name = line.split(",")[-1].strip()
                
                group_match = re.search(r'group-title="([^"]*)"', line)
                group = group_match.group(1) if group_match else "General"

                match = None
                
                # PRIORITY 1: ARUN
                match = find_best_match(target_name, DB_ARUN)
                
                # PRIORITY 2: FAKEALL
                if not match:
                    match = find_best_match(target_name, DB_FAKEALL)

                # OUTPUT
                logo = ""
                link = ""
                
                if match:
                    link = match['link']
                    logo = match['logo']
                
                # Fallback Logo
                if not logo:
                    m_tmpl = re.search(r'tvg-logo="([^"]*)"', line)
                    if m_tmpl: logo = m_tmpl.group(1)
                
                logo_str = f'tvg-logo="{logo}"' if logo else 'tvg-logo=""'

                if link:
                    final_lines.append(f'#EXTINF:-1 group-title="{group}" {logo_str},{target_name}')
                    final_lines.append(link)
                else:
                    print(f"   ⚠️ Missing: {target_name}")
                    final_lines.append(f'#EXTINF:-1 group-title="{group}" {logo_str},⚠️ Offline: {target_name}')
                    final_lines.append("http://0.0.0.0")
    else:
        print("❌ Template Missing!")

    # 3. Extras (Astro/Rasi) - Scan from Arun
    print("\n🔍 Adding Extras...")
    wanted_keywords = ["astro", "rasi", "vijay takkar", "zee thirai"]
    
    # To avoid duplicates, track what we added
    added_names = set()
    
    for ch in DB_ARUN:
        name_lower = ch['raw_name'].lower()
        if any(w in name_lower for w in wanted_keywords):
            # Check if we already added this via template
            if ch['core_name'] in added_names: continue
            
            grp = "Tamil Extra"
            if "cricket" in name_lower or "sports" in name_lower: 
                grp = "Sports Extra"
            
            final_lines.append(f'#EXTINF:-1 group-title="{grp}" tvg-logo="{ch["logo"]}",{ch["raw_name"]}')
            final_lines.append(ch['link'])
            added_names.add(ch['core_name'])

    # 4. Live Events
    print("\n🎥 Adding Live Events...")
    def add_live(url):
        d = load_playlist(url, "Live")
        for ch in d:
            final_lines.append(f'#EXTINF:-1 group-title="Live Events" tvg-logo="{ch["logo"]}",{ch["raw_name"]}')
            final_lines.append(ch['link'])

    add_live(URL_FANCODE)
    add_live(URL_SONY_LIVE)
    add_live(URL_ZEE_LIVE)

    # 5. Manual
    if os.path.exists(youtube_file):
        with open(youtube_file, "r") as f:
            for l in f:
                l = l.strip()
                if l.startswith("http"): final_lines.append(l)
                elif "title" in l.lower(): 
                    final_lines.append(f'#EXTINF:-1 group-title="Temporary" tvg-logo="",{l.split(":",1)[1].strip()}')

    with open(output_file, "w") as f:
        f.write("\n".join(final_lines))
    print("✅ Done.")

if __name__ == "__main__":
    main()
