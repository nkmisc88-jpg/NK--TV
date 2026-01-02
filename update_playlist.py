import requests
import re
import datetime
import os

# ==========================================
# 1. CONFIGURATION
# ==========================================
# FILES
template_file = "template.m3u"
youtube_file = "youtube.txt"
reference_file = "jiotv_playlist.m3u.m3u8" # Local Map
output_file = "playlist.m3u"

# SOURCES
# 1. Local (JioTVGo) - Priority for Regional/News
LOCAL_BASE = "http://192.168.0.146:5350/live"

# 2. Arunjunan (Pocket TV) - Priority for Star/Sony/Zee
URL_ARUN = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/refs/heads/main/index.html"

# 3. Fakeall - Backup
URL_FAKEALL = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"

# LIVE EVENTS
URL_FANCODE = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
URL_SONY_LIVE = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
URL_ZEE_LIVE = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# HEADER
EPG_HEADER = '#EXTM3U x-tvg-url="http://192.168.0.146:5350/epg.xml.gz,https://avkb.short.gy/epg.xml.gz" tvg-shift="-5.5"'

# HEADERS
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# ==========================================
# 2. SMART PARSING ENGINE
# ==========================================
def clean_name(name):
    """Normalize name: 'Star Sports 1 HD' -> 'starsports1hd'"""
    if not name: return ""
    # Remove common junk
    name = re.sub(r'\(.*?\)|\[.*?\]', '', name) 
    return re.sub(r'[^a-z0-9]', '', name.lower())

def extract_info(line):
    """Safely extracts Name and Logo from a raw M3U line"""
    name = line.split(",")[-1].strip()
    if not name:
        match = re.search(r'tvg-name="([^"]*)"', line)
        if match: name = match.group(1)
    
    logo = ""
    match = re.search(r'tvg-logo="([^"]*)"', line)
    if match: logo = match.group(1)
    
    # Extract ID (Generic regex to catch digits or alphanumeric IDs)
    ch_id = ""
    match = re.search(r'tvg-id="([^"]+)"', line)
    if match: ch_id = match.group(1)
    
    return name, logo, ch_id

def load_source(url, source_name, is_local=False, local_file=None):
    """Loads a source into a dictionary: { 'clean_name': {'link': ..., 'logo': ...} }"""
    dataset = {}
    print(f"📥 Loading {source_name}...")
    lines = []
    
    try:
        if is_local:
            if os.path.exists(local_file):
                with open(local_file, "r", encoding="utf-8") as f: lines = f.readlines()
            else:
                print(f"   ⚠️ Local File Missing: {local_file}")
                return {}
        else:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200: lines = r.text.splitlines()
            else: return {}

        for i in range(len(lines)):
            line = lines[i].strip()
            if "#EXTINF" in line:
                name, logo, ch_id = extract_info(line)
                key = clean_name(name)
                
                link = ""
                if is_local and ch_id:
                    link = f"{LOCAL_BASE}/{ch_id}.m3u8"
                else:
                    # Look ahead for link
                    for j in range(i+1, min(i+5, len(lines))):
                        pot = lines[j].strip()
                        if pot and not pot.startswith("#"):
                            link = pot; break
                
                if key and link:
                    dataset[key] = {'link': link, 'logo': logo, 'name': name}
                    
        print(f"   ✅ {source_name}: Loaded {len(dataset)} channels.")
    except Exception as e: print(f"   ❌ Error {source_name}: {e}")
    
    return dataset

# ==========================================
# 3. PRIORITY LOGIC (FUZZY MATCH ENABLED)
# ==========================================
DB_LOCAL = {}
DB_ARUN = {}
DB_FAKEALL = {}

def smart_lookup(target_key, database):
    """
    Tries Exact Match first. 
    If failing, tries Fuzzy Match (is target inside key? OR is key inside target?)
    """
    # 1. Exact Match
    if target_key in database:
        return database[target_key]
    
    # 2. Fuzzy Match (Expensive but necessary for 'Star Sports 1 HD' vs 'Star Sports 1 HD (Backup)')
    for db_key, data in database.items():
        if target_key in db_key or db_key in target_key:
            # Length check to avoid bad matches (e.g. 'Sony' matching 'Sony Ten')
            if abs(len(target_key) - len(db_key)) < 5: 
                return data
    return None

def get_best_link(channel_name):
    key = clean_name(channel_name)
    link = None
    logo = None
    
    # 1. LOGO STRATEGY
    arun_data = smart_lookup(key, DB_ARUN)
    fake_data = smart_lookup(key, DB_FAKEALL)
    
    if arun_data and arun_data['logo']: logo = arun_data['logo']
    elif fake_data and fake_data['logo']: logo = fake_data['logo']
        
    lower_name = channel_name.lower()
    
    # --- STRATEGY A: STAR / SONY / ZEE (Priority: Arun -> Fakeall -> Local) ---
    if any(x in lower_name for x in ["star", "sony", "zee", "set "]):
        # Try Arun
        if arun_data: link = arun_data['link']
        # Try Fakeall
        elif fake_data: link = fake_data['link']
        # Try Local
        else:
            local_data = smart_lookup(key, DB_LOCAL)
            if local_data: link = local_data['link']
        
    # --- STRATEGY B: EVERYTHING ELSE (Priority: Local -> Arun -> Fakeall) ---
    else:
        local_data = smart_lookup(key, DB_LOCAL)
        if local_data: 
            link = local_data['link']
        elif arun_data:
            link = arun_data['link']
        elif fake_data:
            link = fake_data['link']
        
    return link, logo

def get_extras_filtered():
    """Adds only the requested 'Extra' channels from Arunjunan"""
    extras = []
    print("\n🔍 Scanning for Extras...")
    
    SPORTS_WANTED = ["astro cricket", "sony ten", "sky sports"]
    TAMIL_WANTED = [
        "zee tamil", "zee thirai", "vijay takkar", "rasi",
        "astro thangathirai", "astro vellithirai", "astro vaanavil", "astro vinmeen"
    ]
    
    for key, val in DB_ARUN.items():
        name_lower = val['name'].lower()
        target_group = None
        
        if any(x in name_lower for x in SPORTS_WANTED):
            target_group = "Sports Extra"
        elif any(x in name_lower for x in TAMIL_WANTED):
            target_group = "Tamil Extra"
            
        if target_group:
            extras.append(f'#EXTINF:-1 group-title="{target_group}" tvg-logo="{val["logo"]}",{val["name"]}')
            extras.append(val['link'])
            
    print(f"   ✅ Found {len(extras)//2} Extras.")
    return extras

# ==========================================
# 4. MAIN EXECUTION
# ==========================================
def main():
    global DB_LOCAL, DB_ARUN, DB_FAKEALL
    
    # 1. LOAD SOURCES
    DB_LOCAL = load_source(None, "Local (JioTVGo)", True, reference_file)
    DB_ARUN = load_source(URL_ARUN, "Arunjunan (Pocket TV)")
    DB_FAKEALL = load_source(URL_FAKEALL, "Fakeall")
    
    final_lines = [EPG_HEADER]
    
    # Time & Status
    utc_now = datetime.datetime.utcnow()
    ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
    time_str = ist_now.strftime("%d-%m-%Y %I:%M %p")
    final_lines.append(f"# Updated on: {time_str} IST")
    
    status_msg = "✅ Local Ready" if len(DB_LOCAL) > 0 else "❌ Local Map MISSING"
    final_lines.append(f'#EXTINF:-1 group-title="Update Info" tvg-logo="https://i.imgur.com/7Xj4G6d.png",🟡 {status_msg}')
    final_lines.append("http://0.0.0.0")

    # 2. PROCESS TEMPLATE
    print("\n🔨 Building Playlist from Template...")
    if os.path.exists(template_file):
        with open(template_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for i in range(len(lines)):
            line = lines[i].strip()
            
            if line.startswith("#EXTINF"):
                name, tmpl_logo, _ = extract_info(line)
                group_match = re.search(r'group-title="([^"]*)"', line)
                group = group_match.group(1) if group_match else "General"
                
                # GET LINK (Using Smart Fuzzy Logic)
                link, source_logo = get_best_link(name)
                
                # FINAL LOGO
                final_logo = source_logo if source_logo else tmpl_logo
                logo_str = f'tvg-logo="{final_logo}"'
                
                if link:
                    final_lines.append(f'#EXTINF:-1 group-title="{group}" {logo_str},{name}')
                    final_lines.append(link)
                else:
                    print(f"   ⚠️ Missing: {name}")
                    final_lines.append(f'#EXTINF:-1 group-title="{group}" {logo_str},⚠️ Offline: {name}')
                    final_lines.append("http://0.0.0.0")
    else:
        print("   ❌ Template file missing!")

    # 3. ADD EXTRAS
    final_lines.extend(get_extras_filtered())

    # 4. ADD LIVE EVENTS
    print("\n🎥 Adding Live Events...")
    def add_live(url):
        data = load_source(url, "Live")
        for key, val in data.items():
            final_lines.append(f'#EXTINF:-1 group-title="Live Events" tvg-logo="{val["logo"]}",{val["name"]}')
            final_lines.append(val['link'])
            
    add_live(URL_FANCODE)
    add_live(URL_SONY_LIVE)
    add_live(URL_ZEE_LIVE)

    # 5. ADD MANUAL
    print("\n🎥 Adding Manual Links...")
    if os.path.exists(youtube_file):
        with open(youtube_file, "r", encoding="utf-8") as f: yt_lines = f.readlines()
        current = {}
        for line in yt_lines:
            line = line.strip()
            if line.lower().startswith("title") and ":" in line:
                if 'link' in current:
                    final_lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{current.get("logo","")}",{current["title"]}')
                    final_lines.append(current['link'])
                current = {}
            if ':' in line: parts = line.split(':', 1); current[parts[0].strip().lower()] = parts[1].strip()
        if 'link' in current:
            final_lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{current.get("logo","")}",{current["title"]}')
            final_lines.append(current['link'])

    # 6. SAVE
    with open(output_file, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print(f"\n🎉 Done. Saved {len(final_lines)//2} channels to {output_file}")

if __name__ == "__main__":
    main()