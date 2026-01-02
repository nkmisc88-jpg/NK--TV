import requests
import re
import datetime
import os

# ==========================================
# 1. SETUP
# ==========================================
template_file = "template.m3u"
youtube_file = "youtube.txt"
reference_file = "jiotv_playlist.m3u.m3u8" # Local Map
output_file = "playlist.m3u"

# Source URLs
URL_ARUN = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/refs/heads/main/index.html"
URL_FAKEALL = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"
URL_LOCAL = "http://192.168.0.146:5350/live"

# Live Events
URL_FANCODE = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
URL_SONY_LIVE = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
URL_ZEE_LIVE = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}

# ==========================================
# 2. LOGIC
# ==========================================
def normalize(text):
    """Converts 'Star Sports 1 HD' -> {'star', 'sports', '1', 'hd'}"""
    if not text: return set()
    # Remove brackets and non-alphanumeric chars
    clean = re.sub(r'[\(\[\{].*?[\)\]\}]', '', text.lower())
    clean = re.sub(r'[^a-z0-9\s]', '', clean)
    return set(clean.split())

def match_score(target_set, candidate_name):
    """Returns True if ALL words in target are inside candidate."""
    candidate_set = normalize(candidate_name)
    # Check if target words are a subset of candidate words
    return target_set.issubset(candidate_set)

def load_playlist(url, is_local=False, local_file=None):
    print(f"📥 Loading {url if not is_local else local_file}...")
    dataset = []
    lines = []
    try:
        if is_local:
            if os.path.exists(local_file):
                with open(local_file, "r") as f: lines = f.readlines()
        else:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200: lines = r.text.splitlines()

        for i in range(len(lines)):
            line = lines[i].strip()
            if line.startswith("#EXTINF"):
                name = line.split(",")[-1].strip()
                
                logo = ""
                m = re.search(r'tvg-logo="([^"]*)"', line)
                if m: logo = m.group(1)
                
                ch_id = ""
                m_id = re.search(r'tvg-id="(\d+)"', line)
                if m_id: ch_id = m_id.group(1)

                link = ""
                if is_local and ch_id:
                    link = f"{URL_LOCAL}/{ch_id}.m3u8"
                elif not is_local:
                    if i + 1 < len(lines) and "http" in lines[i+1]:
                        link = lines[i+1].strip()
                
                if link:
                    dataset.append({'name': name, 'link': link, 'logo': logo})
        print(f"   ✅ Loaded {len(dataset)} channels.")
    except: pass
    return dataset

# ==========================================
# 3. MAIN
# ==========================================
def main():
    # 1. Load Everything
    DB_LOCAL = load_playlist(None, True, reference_file)
    DB_ARUN = load_playlist(URL_ARUN)
    DB_FAKEALL = load_playlist(URL_FAKEALL)

    final_lines = ['#EXTM3U x-tvg-url="http://192.168.0.146:5350/epg.xml.gz"']
    
    # Time
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines.append(f'#EXTINF:-1 group-title="Update Info" tvg-logo="https://i.imgur.com/7Xj4G6d.png",🟡 Updated: {ist_now.strftime("%d-%m-%Y %H:%M")}')
    final_lines.append("http://0.0.0.0")

    # 2. Process Template
    print("\n🔨 Processing Template...")
    if os.path.exists(template_file):
        with open(template_file, "r") as f: lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF"):
                target_name = line.split(",")[-1].strip()
                target_tokens = normalize(target_name)
                
                group_match = re.search(r'group-title="([^"]*)"', line)
                group = group_match.group(1) if group_match else "General"

                link = None
                logo = None
                
                # --- MATCHING LOGIC ---
                
                # A. Special Channels (Star/Sony/Zee) -> Use ARUN
                if any(x in target_name.lower() for x in ["star", "sony", "zee", "set "]):
                    # Scan Arun
                    for ch in DB_ARUN:
                        if match_score(target_tokens, ch['name']):
                            link = ch['link']; logo = ch['logo']; break
                    # Backup Fakeall
                    if not link:
                        for ch in DB_FAKEALL:
                            if match_score(target_tokens, ch['name']):
                                link = ch['link']; logo = ch['logo']; break
                    # Backup Local
                    if not link:
                         for ch in DB_LOCAL:
                            if match_score(target_tokens, ch['name']):
                                link = ch['link']; break

                # B. Normal Channels -> Use LOCAL
                else:
                    # Scan Local
                    for ch in DB_LOCAL:
                        if match_score(target_tokens, ch['name']):
                            link = ch['link']; break
                    # Backup Arun
                    if not link:
                        for ch in DB_ARUN:
                             if match_score(target_tokens, ch['name']):
                                link = ch['link']; logo = ch['logo']; break

                # --- WRITE ---
                if not logo:
                    m_tmpl = re.search(r'tvg-logo="([^"]*)"', line)
                    if m_tmpl: logo = m_tmpl.group(1)
                
                logo_str = f'tvg-logo="{logo}"' if logo else 'tvg-logo=""'

                if link:
                    final_lines.append(f'#EXTINF:-1 group-title="{group}" {logo_str},{target_name}')
                    final_lines.append(link)
                else:
                    print(f"   ⚠️ Offline: {target_name}")
                    final_lines.append(f'#EXTINF:-1 group-title="{group}" {logo_str},⚠️ Offline: {target_name}')
                    final_lines.append("http://0.0.0.0")

    # 3. Extras (Astro/Rasi) - Explicit Add
    print("\n🔍 Adding Extras...")
    wanted = ["astro", "rasi", "vijay takkar", "zee thirai"]
    for ch in DB_ARUN:
        name_lower = ch['name'].lower()
        if any(w in name_lower for w in wanted):
            grp = "Tamil Extra"
            if "cricket" in name_lower or "sports" in name_lower: grp = "Sports Extra"
            final_lines.append(f'#EXTINF:-1 group-title="{grp}" tvg-logo="{ch["logo"]}",{ch["name"]}')
            final_lines.append(ch['link'])

    # 4. Live & Manual
    print("\n🎥 Adding Live/Manual...")
    def add_live(url):
        d = load_playlist(url)
        for ch in d:
            final_lines.append(f'#EXTINF:-1 group-title="Live Events" tvg-logo="{ch["logo"]}",{ch["name"]}')
            final_lines.append(ch['link'])
    add_live(URL_FANCODE); add_live(URL_SONY_LIVE); add_live(URL_ZEE_LIVE)

    if os.path.exists(youtube_file):
        with open(youtube_file, "r") as f:
            for l in f:
                if l.startswith("http"): final_lines.append(l.strip())
                elif "title" in l.lower(): final_lines.append(f'#EXTINF:-1 group-title="Temporary" tvg-logo="",{l.split(":",1)[1].strip()}')

    with open(output_file, "w") as f: f.write("\n".join(final_lines))
    print("✅ Done.")

if __name__ == "__main__":
    main()
