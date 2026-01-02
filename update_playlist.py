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
# Priority 2: Fakeall
URL_FAKEALL = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"
# Priority 3: Local
URL_LOCAL = "http://192.168.0.146:5350/live"
reference_file = "jiotv_playlist.m3u.m3u8"

# Live Events
URL_FANCODE = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
URL_SONY_LIVE = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
URL_ZEE_LIVE = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# Headers (Fixed for Zee5 Playback)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}

# ==========================================
# 2. MATCHING LOGIC
# ==========================================
def get_core_name(text):
    """
    Strict Cleaner: 'Zee Tamil HD' -> 'zeetamilhd'
    Fixes spacing mismatches.
    """
    if not text: return ""
    # Remove things in brackets
    text = re.sub(r'[\(\[\{].*?[\)\]\}]', '', text.lower())
    # Remove ALL non-alphanumeric characters (including spaces)
    return re.sub(r'[^a-z0-9]', '', text)

def get_tokens(text):
    """
    Flexible Cleaner: 'Zee Tamil HD' -> {'zee', 'tamil', 'hd'}
    """
    if not text: return set()
    clean = re.sub(r'[\(\[\{].*?[\)\]\}]', '', text.lower())
    clean = re.sub(r'[^a-z0-9\s]', '', clean)
    return set(clean.split())

def load_playlist(url, source_name, is_local=False, local_file=None):
    print(f"📥 Loading {source_name}...")
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
                if is_local:
                    m_id = re.search(r'tvg-id="(\d+)"', line)
                    if m_id: ch_id = m_id.group(1)

                link = ""
                if is_local and ch_id:
                    link = f"{URL_LOCAL}/{ch_id}.m3u8"
                elif not is_local:
                    if i + 1 < len(lines):
                        potential_link = lines[i+1].strip()
                        if potential_link and not potential_link.startswith("#"):
                            link = potential_link
                            # FIX PLAYBACK: FORCE USER AGENT
                            if "http" in link and "|" not in link:
                                link += f"|User-Agent={USER_AGENT}"
                
                if link:
                    dataset.append({
                        'name': name,
                        'core': get_core_name(name),   # Pre-calculate zeetamilhd
                        'tokens': get_tokens(name),    # Pre-calculate {zee, tamil, hd}
                        'link': link,
                        'logo': logo
                    })
        print(f"   ✅ {source_name}: {len(dataset)} channels.")
    except Exception as e:
        print(f"   ❌ Error {source_name}: {e}")
    return dataset

def find_best_match(target_name, database):
    """
    Tries 2 methods to find a channel:
    1. Core Match (zeethiraihd == zeethiraihd) -> Fixes spacing
    2. Token Subset ({zee, thirai, hd} in {zee, thirai, hd, backup}) -> Fixes extra words
    """
    target_core = get_core_name(target_name)
    target_tokens = get_tokens(target_name)
    
    # Method 1: Exact Core Match (Strongest)
    for ch in database:
        if ch['core'] == target_core:
            return ch
            
    # Method 2: Token Subset (Flexible)
    for ch in database:
        if target_tokens.issubset(ch['tokens']):
            return ch
            
    return None

# ==========================================
# 3. MAIN SCRIPT
# ==========================================
def main():
    # 1. Load Sources
    DB_LOCAL = load_playlist(None, "Local Map", True, reference_file)
    DB_ARUN = load_playlist(URL_ARUN, "Arunjunan20")
    DB_FAKEALL = load_playlist(URL_FAKEALL, "Fakeall")

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
                
                group_match = re.search(r'group-title="([^"]*)"', line)
                group = group_match.group(1) if group_match else "General"

                match = None
                source_used = "None"
                
                # --- PRIORITY LOGIC ---
                
                # A. Star/Sony/Zee -> Arunjunan First
                if any(x in target_name.lower() for x in ["star", "sony", "zee", "set "]):
                    match = find_best_match(target_name, DB_ARUN)
                    if not match: match = find_best_match(target_name, DB_FAKEALL)
                    if not match: match = find_best_match(target_name, DB_LOCAL)

                # B. Others -> Local First
                else:
                    match = find_best_match(target_name, DB_LOCAL)
                    if not match: match = find_best_match(target_name, DB_ARUN)
                    if not match: match = find_best_match(target_name, DB_FAKEALL)

                # --- WRITE ---
                logo = ""
                link = ""
                
                if match:
                    link = match['link']
                    logo = match['logo']
                
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

    # 3. Extras (Astro/Rasi)
    print("\n🔍 Adding Extras...")
    wanted = ["astro", "rasi", "vijay takkar", "zee thirai"]
    # Track added so we don't duplicate
    added_cores = set()
    
    for ch in DB_ARUN:
        name_lower = ch['name'].lower()
        if any(w in name_lower for w in wanted):
            if ch['core'] in added_cores: continue
            
            grp = "Tamil Extra"
            if "cricket" in name_lower or "sports" in name_lower: grp = "Sports Extra"
            
            final_lines.append(f'#EXTINF:-1 group-title="{grp}" tvg-logo="{ch["logo"]}",{ch["name"]}')
            final_lines.append(ch['link'])
            added_cores.add(ch['core'])

    # 4. Live & Manual
    print("\n🎥 Adding Live/Manual...")
    def add_live(url):
        d = load_playlist(url, "Live")
        for ch in d:
            final_lines.append(f'#EXTINF:-1 group-title="Live Events" tvg-logo="{ch["logo"]}",{ch["name"]}')
            final_lines.append(ch["link"])
    add_live(URL_FANCODE); add_live(URL_SONY_LIVE); add_live(URL_ZEE_LIVE)

    if os.path.exists(youtube_file):
        with open(youtube_file, "r") as f:
            for l in f:
                l = l.strip()
                if l.startswith("http"): final_lines.append(l)
                elif "title" in l.lower(): 
                    final_lines.append(f'#EXTINF:-1 group-title="Temporary" tvg-logo="",{l.split(":",1)[1].strip()}')

    with open(output_file, "w") as f: f.write("\n".join(final_lines))
    print("✅ Done.")

if __name__ == "__main__":
    main()
