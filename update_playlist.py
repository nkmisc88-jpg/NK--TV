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
reference_file = "jiotv_playlist.m3u.m3u8" # Your Local Map
output_file = "playlist.m3u"

# SOURCES
# Priority 1: Local Server (JioTVGo)
LOCAL_BASE = "http://192.168.0.146:5350/live"

# Priority 2: Fakeall (For Star/Sports)
URL_FAKEALL = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"

# Priority 3: Arunjunan (For Zee, Sony, and ASTRO)
URL_ARUN = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/refs/heads/main/index.html"

# LIVE EVENT SOURCES
URL_FANCODE = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
URL_SONY_LIVE = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
URL_ZEE_LIVE = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# HEADER
EPG_HEADER = '#EXTM3U x-tvg-url="http://192.168.0.146:5350/epg.xml.gz,https://avkb.short.gy/epg.xml.gz" tvg-shift="-5.5"'

# ==========================================
# 2. DATA STRUCTURES & HELPERS
# ==========================================
DB_FAKEALL = {}
DB_ARUN = {}
DB_LOCAL = {}

def clean_name(name):
    """Normalizes channel names for matching (e.g., 'Star Sports 1 HD' -> 'starsports1hd')"""
    if not name: return ""
    name = name.lower()
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name) # Remove stuff in brackets
    name = re.sub(r'[^a-z0-9]', '', name)       # Remove spaces and special chars
    return name

def parse_m3u_to_dict(url, source_name):
    """Fetches an M3U and returns a dict { 'clean_name': {'link': url, 'logo': url} }"""
    data = {}
    print(f"📥 Fetching {source_name}...")
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            lines = r.text.splitlines()
            for i in range(len(lines)):
                line = lines[i].strip()
                if line.startswith("#EXTINF"):
                    # Extract Name
                    name = line.split(",")[-1].strip()
                    key = clean_name(name)
                    
                    # Extract Logo
                    logo = ""
                    match = re.search(r'tvg-logo="([^"]*)"', line)
                    if match: logo = match.group(1)
                    
                    # Find Link
                    link = ""
                    for j in range(i+1, min(i+5, len(lines))):
                        if lines[j].strip() and not lines[j].startswith("#"):
                            link = lines[j].strip()
                            break
                    
                    if key and link:
                        data[key] = {'link': link, 'logo': logo, 'raw_name': name}
        print(f"   ✅ Loaded {len(data)} channels from {source_name}")
    except Exception as e:
        print(f"   ❌ Failed to load {source_name}: {e}")
    return data

def load_local_map():
    """Parses your local jiotv_playlist file to map names to IDs"""
    data = {}
    if os.path.exists(reference_file):
        try:
            with open(reference_file, "r", encoding="utf-8") as f:
                content = f.read()
                matches = re.findall(r'tvg-id="(\d+)".*?tvg-name="([^"]+)"', content)
                for ch_id, name in matches:
                    key = clean_name(name)
                    data[key] = {'link': f"{LOCAL_BASE}/{ch_id}.m3u8", 'logo': ""}
            print(f"   ✅ Loaded {len(data)} channels from Local Map")
        except: print("   ⚠️ Local map file not found or unreadable.")
    return data

# ==========================================
# 3. CHANNEL ROUTING LOGIC
# ==========================================
def find_best_stream(channel_name):
    key = clean_name(channel_name)
    link = None
    logo = None
    
    # 1. Grab Logo from Arun (High Quality) if available
    if key in DB_ARUN and DB_ARUN[key]['logo']:
        logo = DB_ARUN[key]['logo']

    # 2. Determine Link Source
    lower_name = channel_name.lower()
    
    # --- RULE 1: STAR / SPORTS (Use Fakeall) ---
    if "star" in lower_name and "sports" in lower_name:
        if key in DB_FAKEALL: link = DB_FAKEALL[key]['link']
        elif key in DB_LOCAL: link = DB_LOCAL[key]['link']
        elif key in DB_ARUN:  link = DB_ARUN[key]['link']

    # --- RULE 2: ZEE / SONY / ASTRO (Use Arunjunan) ---
    elif any(x in lower_name for x in ["zee", "sony", "astro"]):
        if key in DB_ARUN:    link = DB_ARUN[key]['link']
        elif key in DB_FAKEALL: link = DB_FAKEALL[key]['link']
        elif key in DB_LOCAL:   link = DB_LOCAL[key]['link']

    # --- RULE 3: DEFAULT (Use Local JioTVGo) ---
    else:
        if key in DB_LOCAL:     link = DB_LOCAL[key]['link']
        elif key in DB_FAKEALL: link = DB_FAKEALL[key]['link']
        elif key in DB_ARUN:    link = DB_ARUN[key]['link']

    return link, logo

# ==========================================
# 4. MAIN BUILDER
# ==========================================
def main():
    global DB_FAKEALL, DB_ARUN, DB_LOCAL
    
    # 1. Load Databases
    DB_LOCAL = load_local_map()
    DB_FAKEALL = parse_m3u_to_dict(URL_FAKEALL, "Fakeall")
    DB_ARUN = parse_m3u_to_dict(URL_ARUN, "Arunjunan20")
    
    final_lines = [EPG_HEADER]
    
    # --- TIMEZONE FIX (IST = UTC + 5:30) ---
    utc_now = datetime.datetime.utcnow()
    ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
    time_str = ist_now.strftime("%d-%m-%Y %I:%M %p")
    
    final_lines.append(f"# Updated on: {time_str} IST")
    
    # ADD VISUAL TIMESTAMP CHANNEL (So you see it in the player)
    final_lines.append(f'#EXTINF:-1 group-title="Update Info" tvg-logo="https://i.imgur.com/7Xj4G6d.png",🟡 Updated: {time_str}')
    final_lines.append("http://0.0.0.0")

    # 2. PROCESS TEMPLATE (The Master List)
    print("\n🔨 Processing Master Template...")
    if os.path.exists(template_file):
        with open(template_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for i in range(len(lines)):
            line = lines[i].strip()
            
            if line.startswith("#EXTINF"):
                # Extract Info
                name = line.split(",")[-1].strip()
                group_match = re.search(r'group-title="([^"]*)"', line)
                group = group_match.group(1) if group_match else "General"
                
                # Routing Magic
                link, logo = find_best_stream(name)
                
                if link:
                    # Use found logo if available, otherwise check if template had one
                    if not logo:
                        tmpl_logo = re.search(r'tvg-logo="([^"]*)"', line)
                        if tmpl_logo: logo = tmpl_logo.group(1)
                    
                    logo_str = f'tvg-logo="{logo}"' if logo else 'tvg-logo=""'
                    
                    # Rebuild Line
                    new_line = f'#EXTINF:-1 group-title="{group}" {logo_str},{name}'
                    final_lines.append(new_line)
                    final_lines.append(link)
                else:
                    print(f"   ⚠️ No source found for: {name}")
    else:
        print("   ❌ Template file not found!")

    # 3. ADD LIVE EVENTS (Fancode / Sony / Zee)
    print("\n🎥 Processing Live Events...")
    
    def add_live_source(url, prefix):
        data = parse_m3u_to_dict(url, prefix)
        for key, val in data.items():
            final_lines.append(f'#EXTINF:-1 group-title="Live Events" tvg-logo="{val["logo"]}",{val["raw_name"]}')
            final_lines.append(val['link'])

    add_live_source(URL_FANCODE, "Fancode")
    add_live_source(URL_SONY_LIVE, "Sony Live")
    add_live_source(URL_ZEE_LIVE, "Zee Live")

    # 4. ADD TEMPORARY CHANNELS
    print("\n🎥 Processing Temporary Channels...")
    if os.path.exists(youtube_file):
        with open(youtube_file, "r", encoding="utf-8") as f:
            yt_lines = f.readlines()
        
        current_yt = {}
        for line in yt_lines:
            line = line.strip()
            if not line: continue
            if line.lower().startswith("title") and ":" in line:
                if 'link' in current_yt:
                    final_lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{current_yt.get("logo","")}",{current_yt["title"]}')
                    final_lines.append(current_yt['link'])
                current_yt = {}
            if ':' in line:
                parts = line.split(':', 1)
                current_yt[parts[0].strip().lower()] = parts[1].strip()
        # Add last one
        if 'link' in current_yt:
            final_lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{current_yt.get("logo","")}",{current_yt["title"]}')
            final_lines.append(current_yt['link'])

    # 5. SAVE
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    print(f"\n🎉 Playlist Generated: {len(final_lines)//2} channels saved to {output_file}")

if __name__ == "__main__":
    main()