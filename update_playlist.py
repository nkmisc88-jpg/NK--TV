import requests
import re
import datetime
import os

# ==========================================
# 1. CONFIGURATION
# ==========================================
template_file = "template.m3u"
youtube_file = "youtube.txt"
reference_file = "jiotv_playlist.m3u.m3u8" # MUST BE IN REPO
output_file = "playlist.m3u"

# SOURCES
# Priority 1: Local Server (JioTVGo)
LOCAL_BASE = "http://192.168.0.146:5350/live"

# Priority 2: Fakeall (For Star/Sports)
URL_FAKEALL = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"

# Priority 3: Arunjunan (For Zee, Sony, and Pocket TV Extras)
URL_ARUN = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/refs/heads/main/index.html"

# LIVE EVENT SOURCES
URL_FANCODE = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
URL_SONY_LIVE = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
URL_ZEE_LIVE = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# HEADER
EPG_HEADER = '#EXTM3U x-tvg-url="http://192.168.0.146:5350/epg.xml.gz,https://avkb.short.gy/epg.xml.gz" tvg-shift="-5.5"'

# HEADERS (To look like a browser)
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ==========================================
# 2. PARSING ENGINE
# ==========================================
DB_FAKEALL = {}
DB_ARUN = {}
DB_LOCAL = {}

def clean_name(name):
    """Standardizes names for comparison"""
    if not name: return ""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def extract_info(line):
    """Extracts Name and Logo from an #EXTINF line safely"""
    # 1. Name after comma
    name = line.split(",")[-1].strip()
    # 2. Fallback to tvg-name
    if not name:
        match = re.search(r'tvg-name="([^"]*)"', line)
        if match: name = match.group(1)
    # 3. Logo
    logo = ""
    match_logo = re.search(r'tvg-logo="([^"]*)"', line)
    if match_logo: logo = match_logo.group(1)
    # 4. ID (For Local)
    ch_id = ""
    match_id = re.search(r'tvg-id="(\d+)"', line)
    if match_id: ch_id = match_id.group(1)
    
    return name, logo, ch_id

def parse_m3u_to_dict(url, source_name, is_local=False, local_file_path=None):
    data = {}
    print(f"📥 Loading {source_name}...")
    lines = []
    try:
        if is_local:
            if os.path.exists(local_file_path):
                with open(local_file_path, "r", encoding="utf-8") as f: lines = f.readlines()
            else:
                print(f"   ⚠️ File not found: {local_file_path}")
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
                    for j in range(i+1, min(i+5, len(lines))):
                        potential = lines[j].strip()
                        if potential and not potential.startswith("#"):
                            link = potential; break
                
                if key and link:
                    data[key] = {'link': link, 'logo': logo, 'raw_name': name}
        print(f"   ✅ Loaded {len(data)} channels from {source_name}")
    except Exception as e: print(f"   ❌ Error {source_name}: {e}")
    return data

# ==========================================
# 3. ROUTING & FILTERING
# ==========================================
def find_best_stream(channel_name):
    key = clean_name(channel_name)
    link = None; logo = None
    
    # 1. Prefer Source Logo (High Quality)
    if key in DB_ARUN and DB_ARUN[key]['logo']: logo = DB_ARUN[key]['logo']
    elif key in DB_FAKEALL and DB_FAKEALL[key]['logo']: logo = DB_FAKEALL[key]['logo']
    
    lower_name = channel_name.lower()
    
    # RULE 1: STAR / SPORTS -> Fakeall > Local
    if "star" in lower_name or "sports" in lower_name:
        if key in DB_FAKEALL:   link = DB_FAKEALL[key]['link']
        elif key in DB_LOCAL:   link = DB_LOCAL[key]['link']
        elif key in DB_ARUN:    link = DB_ARUN[key]['link']
            
    # RULE 2: ZEE / SONY -> Arun > Fakeall > Local
    elif any(x in lower_name for x in ["zee", "sony", "set "]):
        if key in DB_ARUN:      link = DB_ARUN[key]['link']
        elif key in DB_FAKEALL: link = DB_FAKEALL[key]['link']
        elif key in DB_LOCAL:   link = DB_LOCAL[key]['link']

    # RULE 3: DEFAULT -> Local > Fakeall > Arun
    else:
        if key in DB_LOCAL:     link = DB_LOCAL[key]['link']
        elif key in DB_FAKEALL: link = DB_FAKEALL[key]['link']
        elif key in DB_ARUN:    link = DB_ARUN[key]['link']
        
    return link, logo

def get_extras_from_arun():
    """Extracts strictly requested Astro/Rasi/PocketTV channels"""
    extras = []
    print("\n🔍 Scanning for Extras (Astro/Rasi)...")
    
    # Strict Keywords
    SPORTS_WANTED = ["astro cricket", "sony ten", "sky sports"]
    TAMIL_WANTED = [
        "zee tamil", "zee thirai", "vijay takkar", "rasi",
        "astro thangathirai", "astro vellithirai", "astro vaanavil", "astro vinmeen"
    ]
    
    for key, val in DB_ARUN.items():
        name_lower = val['raw_name'].lower()
        target_group = None
        
        if any(x in name_lower for x in SPORTS_WANTED):
            target_group = "Sports Extra"
        elif any(x in name_lower for x in TAMIL_WANTED):
            target_group = "Tamil Extra"
            
        if target_group:
            extras.append(f'#EXTINF:-1 group-title="{target_group}" tvg-logo="{val["logo"]}",{val["raw_name"]}')
            extras.append(val['link'])
            
    print(f"   ✅ Found {len(extras)//2} Extras.")
    return extras

# ==========================================
# 4. MAIN BUILDER
# ==========================================
def main():
    global DB_FAKEALL, DB_ARUN, DB_LOCAL
    
    # 1. Load Sources
    DB_LOCAL = parse_m3u_to_dict(None, "Local Map", True, reference_file)
    DB_FAKEALL = parse_m3u_to_dict(URL_FAKEALL, "Fakeall")
    DB_ARUN = parse_m3u_to_dict(URL_ARUN, "Arunjunan20")
    
    final_lines = [EPG_HEADER]
    
    # Time & Status
    utc_now = datetime.datetime.utcnow()
    ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
    time_str = ist_now.strftime("%d-%m-%Y %I:%M %p")
    final_lines.append(f"# Updated on: {time_str} IST")
    
    status = "✅ Local Connected" if len(DB_LOCAL) > 0 else "❌ Local Map MISSING"
    final_lines.append(f'#EXTINF:-1 group-title="Update Info" tvg-logo="https://i.imgur.com/7Xj4G6d.png",🟡 {status}')
    final_lines.append("http://0.0.0.0")

    # 2. PROCESS TEMPLATE (Your Manual List)
    print("\n🔨 Building from Template...")
    if os.path.exists(template_file):
        with open(template_file, "r", encoding="utf-8") as f: lines = f.readlines()
            
        for i in range(len(lines)):
            line = lines[i].strip()
            if line.startswith("#EXTINF"):
                name, tmpl_logo, _ = extract_info(line)
                group_match = re.search(r'group-title="([^"]*)"', line)
                group = group_match.group(1) if group_match else "General"
                
                link, source_logo = find_best_stream(name)
                
                # Logic: Use Source Logo if found, else Template Logo
                final_logo = source_logo if source_logo else tmpl_logo
                logo_str = f'tvg-logo="{final_logo}"'
                
                if link:
                    final_lines.append(f'#EXTINF:-1 group-title="{group}" {logo_str},{name}')
                    final_lines.append(link)
                else:
                    # Fuzzy Recovery
                    found_fuzzy = False
                    key = clean_name(name)
                    for db_key, val in DB_ARUN.items():
                        if key in db_key:
                            final_lines.append(f'#EXTINF:-1 group-title="{group}" {logo_str},{name}')
                            final_lines.append(val['link'])
                            found_fuzzy = True; break
                    
                    if not found_fuzzy:
                        print(f"   ⚠️ Missing: {name}")
                        final_lines.append(f'#EXTINF:-1 group-title="{group}" {logo_str},⚠️ Offline: {name}')
                        final_lines.append("http://0.0.0.0")
    else: print("   ❌ Template file missing!")

    # 3. ADD EXTRAS (Astro/Rasi/PocketTV)
    final_lines.extend(get_extras_from_arun())

    # 4. ADD LIVE EVENTS
    print("\n🎥 Adding Live Events...")
    def add_live(url):
        data = parse_m3u_to_dict(url, "Live")
        for key, val in data.items():
            final_lines.append(f'#EXTINF:-1 group-title="Live Events" tvg-logo="{val["logo"]}",{val["raw_name"]}')
            final_lines.append(val['link'])
    add_live(URL_FANCODE); add_live(URL_SONY_LIVE); add_live(URL_ZEE_LIVE)

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
