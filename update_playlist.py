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
# 2. MATCHING LOGIC
# ==========================================
def normalize(text):
    """
    Converts 'Star Sports 1 HD (Backup)' -> {'star', 'sports', '1', 'hd', 'backup'}
    This allows us to match names even if they aren't identical.
    """
    if not text: return set()
    # Remove brackets and symbols
    text = re.sub(r'[\(\[\{].*?[\)\]\}]', '', text.lower())
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return set(text.split())

def is_match(target_name, candidate_name):
    """
    Returns True if the core words of the Target are inside the Candidate.
    """
    target_tokens = normalize(target_name)
    candidate_tokens = normalize(candidate_name)
    
    if not target_tokens: return False
    
    # Check if ALL words in target are present in candidate
    # e.g. Target: {star, sports} is inside Candidate: {star, sports, 1, hd}
    return target_tokens.issubset(candidate_tokens)

def load_playlist(url, name):
    print(f"📥 Loading {name}...")
    dataset = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            lines = r.text.splitlines()
            for i in range(len(lines)):
                line = lines[i].strip()
                if line.startswith("#EXTINF"):
                    # Extract Name
                    ch_name = line.split(",")[-1].strip()
                    
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
                    
                    if link and ch_name:
                        dataset.append({'name': ch_name, 'link': link, 'logo': logo})
        print(f"   ✅ Loaded {len(dataset)} channels.")
    except Exception as e:
        print(f"   ❌ Error loading {name}: {e}")
    return dataset

# ==========================================
# 3. MAIN SCRIPT
# ==========================================
def main():
    # 1. Load Sources
    DB_ARUN = load_playlist(URL_ARUN, "Arunjunan20")
    DB_FAKEALL = load_playlist(URL_FAKEALL, "Fakeall")

    final_lines = ['#EXTM3U x-tvg-url="http://192.168.0.146:5350/epg.xml.gz"']
    
    # Add Time
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines.append(f'#EXTINF:-1 group-title="Update Info" tvg-logo="https://i.imgur.com/7Xj4G6d.png",🟡 Updated: {ist_now.strftime("%d-%m-%Y %H:%M")}')
    final_lines.append("http://0.0.0.0")

    # 2. Process Template
    print("\n🔨 Processing Template...")
    if os.path.exists(template_file):
        with open(template_file, "r") as f:
            template_lines = f.readlines()
            
        for line in template_lines:
            line = line.strip()
            if line.startswith("#EXTINF"):
                target_name = line.split(",")[-1].strip()
                
                # Get Group
                group_match = re.search(r'group-title="([^"]*)"', line)
                group = group_match.group(1) if group_match else "General"

                link = None
                logo = None
                
                # --- MATCHING STRATEGY ---
                # 1. Check Arunjunan (Priority)
                for ch in DB_ARUN:
                    if is_match(target_name, ch['name']):
                        link = ch['link']
                        logo = ch['logo']
                        break
                
                # 2. Check Fakeall (Backup)
                if not link:
                    for ch in DB_FAKEALL:
                        if is_match(target_name, ch['name']):
                            link = ch['link']
                            logo = ch['logo']
                            break
                
                # --- WRITE RESULT ---
                # Use source logo if found, else template logo
                if not logo:
                    tmpl_logo = re.search(r'tvg-logo="([^"]*)"', line)
                    if tmpl_logo: logo = tmpl_logo.group(1)

                logo_str = f'tvg-logo="{logo}"' if logo else 'tvg-logo=""'

                if link:
                    final_lines.append(f'#EXTINF:-1 group-title="{group}" {logo_str},{target_name}')
                    final_lines.append(link)
                else:
                    print(f"   ⚠️ Offline: {target_name}")
                    final_lines.append(f'#EXTINF:-1 group-title="{group}" {logo_str},⚠️ Offline: {target_name}')
                    final_lines.append("http://0.0.0.0")
    else:
        print("❌ Template Missing!")

    # 3. Extras (Astro/Rasi) - Scan from Arun
    print("\n🔍 Adding Extras...")
    wanted_keywords = ["astro", "rasi", "vijay takkar", "zee thirai"]
    
    for ch in DB_ARUN:
        name_lower = ch['name'].lower()
        if any(w in name_lower for w in wanted_keywords):
            grp = "Tamil Extra"
            if "cricket" in name_lower or "sports" in name_lower: 
                grp = "Sports Extra"
            
            final_lines.append(f'#EXTINF:-1 group-title="{grp}" tvg-logo="{ch["logo"]}",{ch["name"]}')
            final_lines.append(ch['link'])

    # 4. Live Events
    print("\n🎥 Adding Live Events...")
    def add_live(url):
        d = load_playlist(url, "Live")
        for ch in d:
            final_lines.append(f'#EXTINF:-1 group-title="Live Events" tvg-logo="{ch["logo"]}",{ch["name"]}')
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
