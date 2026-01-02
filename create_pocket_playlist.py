import requests
import re
import datetime
import os

# ==========================================
# CONFIGURATION
# ==========================================
OUTPUT_FILE = "pocket_playlist.m3u"
YOUTUBE_FILE = "youtube.txt"

# 1. MAIN SOURCE (Pocket TV)
POCKET_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/refs/heads/main/index.html"

# 2. LIVE EVENT SOURCES
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SONY_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
ZEE_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# 3. MASTER CHANNEL LIST (Hardcoded Preference)
# Format: ("Group Name", "Channel Name")
MASTER_CHANNELS = [
    # --- SPORTS HD ---
    ("Sports HD", "Star Sports 1 HD"),
    ("Sports HD", "Star Sports 2 HD"),
    ("Sports HD", "Star Sports 1 Hindi HD"),
    ("Sports HD", "Star Sports Select 1 HD"),
    ("Sports HD", "Star Sports Select 2 HD"),
    ("Sports HD", "Sony Sports Ten 1 HD"),
    ("Sports HD", "Sony Sports Ten 2 HD"),
    ("Sports HD", "Sony Sports Ten 3 HD"),
    ("Sports HD", "Sony Sports Ten 4 HD"),
    ("Sports HD", "Sony Sports Ten 5 HD"),
    ("Sports HD", "Sports18 1 HD"),
    ("Sports HD", "Eurosport HD"),
    ("Sports HD", "Astro Cricket"),
    ("Sports HD", "Willow Cricket"),
    ("Sports HD", "Sky Sports Cricket"),

    # --- TAMIL HD ---
    ("Tamil HD", "Sun TV HD"),
    ("Tamil HD", "KTV HD"),
    ("Tamil HD", "Star Vijay HD"),
    ("Tamil HD", "Zee Tamil HD"),
    ("Tamil HD", "Colors Tamil HD"),
    ("Tamil HD", "Jaya TV HD"),
    ("Tamil HD", "Zee Thirai HD"),
    ("Tamil HD", "Vijay Takkar"),
    ("Tamil HD", "Astro Vaanavil"),
    ("Tamil HD", "Astro Vinmeen HD"),
    ("Tamil HD", "Astro Thangathirai"),
    ("Tamil HD", "Astro Vellithirai"),
    ("Tamil HD", "Rasi Palan"),
    ("Tamil HD", "Rasi Movies"),
    
    # --- INFOTAINMENT HD ---
    ("Infotainment", "Discovery HD"),
    ("Infotainment", "Animal Planet HD"),
    ("Infotainment", "Nat Geo HD"),
    ("Infotainment", "Nat Geo Wild HD"),
    ("Infotainment", "Sony BBC Earth HD"),
    ("Infotainment", "History TV18 HD"),
    ("Infotainment", "TLC HD"),
    ("Infotainment", "TravelXP HD"),

    # --- MOVIES HD ---
    ("Movies", "Star Movies HD"),
    ("Movies", "Sony Pix HD"),
    ("Movies", "Movies Now HD"),
    ("Movies", "MN+ HD"),
    ("Movies", "MNX HD"),
    ("Movies", "Star Gold HD"),
    ("Movies", "Sony Max HD"),
    ("Movies", "Zee Cinema HD"),
    ("Movies", "&Pictures HD"),

    # --- ENTERTAINMENT HD ---
    ("Entertainment", "Star Plus HD"),
    ("Entertainment", "Sony SET HD"),
    ("Entertainment", "Sony SAB HD"),
    ("Entertainment", "Zee TV HD"),
    ("Entertainment", "Colors HD"),
    ("Entertainment", "Star Bharat HD"),

    # --- REGIONAL HD ---
    ("Malayalam", "Asianet HD"),
    ("Malayalam", "Surya TV HD"),
    ("Malayalam", "Mazhavil Manorama HD"),
    ("Telugu", "Star Maa HD"),
    ("Telugu", "Zee Telugu HD"),
    ("Telugu", "Gemini TV HD"),
    ("Kannada", "Colors Kannada HD"),
    ("Kannada", "Star Suvarna HD"),
    ("Kannada", "Zee Kannada HD"),
    ("Kannada", "Udaya TV HD"),

    # --- KIDS ---
    ("Kids", "Nick"),
    ("Kids", "Sonic"),
    ("Kids", "Hungama"),
    ("Kids", "Disney Channel"),
    ("Kids", "Cartoon Network"),
    ("Kids", "Pogo"),
    ("Kids", "Sony Yay"),
    ("Kids", "Discovery Kids"),

    # --- NEWS ---
    ("News", "Times Now"),
    ("News", "NDTV 24x7"),
    ("News", "India Today"),
    ("News", "CNN News18"),
    ("News", "Sun News"),
    ("News", "Polimer News"),
    ("News", "Puthiya Thalaimurai"),
    ("News", "Thanthi TV")
]

# ==========================================
# LOGIC
# ==========================================

def clean_name(name):
    """
    Removes spaces and symbols for matching.
    'Zee Tamil HD' -> 'zeetamilhd'
    """
    if not name: return ""
    name = re.sub(r'[\(\[\{].*?[\)\]\}]', '', name.lower())
    return re.sub(r'[^a-z0-9]', '', name)

def fetch_pocket_map():
    """Downloads Pocket TV playlist and builds a map."""
    print(f"📥 Loading Pocket TV Reference...")
    data_map = {}
    try:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
        r = requests.get(POCKET_URL, headers={"User-Agent": ua}, timeout=15)
        
        if r.status_code == 200:
            lines = r.text.splitlines()
            for i in range(len(lines)):
                line = lines[i].strip()
                if line.startswith("#EXTINF"):
                    raw_name = line.split(",")[-1].strip()
                    key = clean_name(raw_name)
                    
                    logo = ""
                    m = re.search(r'tvg-logo="([^"]*)"', line)
                    if m: logo = m.group(1)
                    
                    link = ""
                    if i + 1 < len(lines):
                        pot_link = lines[i+1].strip()
                        if pot_link and not pot_link.startswith("#"):
                            link = pot_link
                            # Append User-Agent for playback
                            if "http" in link and "|" not in link:
                                link += f"|User-Agent={ua}"
                    
                    if key and link:
                        data_map[key] = {'link': link, 'logo': logo}
                        
            print(f"   ✅ Loaded {len(data_map)} channels from Pocket TV.")
    except Exception as e:
        print(f"   ❌ Error loading Pocket TV: {e}")
    return data_map

def parse_youtube_txt():
    """Reads youtube.txt for temporary channels."""
    entries = []
    if not os.path.exists(YOUTUBE_FILE): return []
    try:
        with open(YOUTUBE_FILE, "r", encoding="utf-8") as f: lines = f.readlines()
        current = {}
        for line in lines:
            line = line.strip()
            if line.lower().startswith("title") and ":" in line:
                if 'link' in current: 
                    entries.append(f'#EXTINF:-1 group-title="Temporary" tvg-logo="{current.get("logo","")}",{current["title"]}\n{current["link"]}')
                current = {}
            if ':' in line:
                p = line.split(':', 1)
                current[p[0].strip().lower()] = p[1].strip()
        if 'link' in current:
             entries.append(f'#EXTINF:-1 group-title="Temporary" tvg-logo="{current.get("logo","")}",{current["title"]}\n{current["link"]}')
    except: pass
    return entries

def fetch_live_events(url, group_name):
    """Fetches Fancode/Sony/Zee live events."""
    entries = []
    try:
        ua = "Mozilla/5.0"
        r = requests.get(url, headers={"User-Agent": ua}, timeout=15)
        if r.status_code == 200:
            lines = r.text.splitlines()
            for line in lines:
                if line.startswith("#EXTINF"):
                    line = re.sub(r'group-title="[^"]*"', '', line)
                    line = re.sub(r'(#EXTINF:[-0-9]+)', f'\\1 group-title="{group_name}"', line)
                    entries.append(line)
                elif line.startswith("http"):
                    entries.append(line)
    except: pass
    return entries

def main():
    print("--- GENERATING POCKET PLAYLIST ---")
    
    # 1. Get the Reference Map
    pocket_map = fetch_pocket_map()
    
    # 2. Start Building Playlist
    # Time logic (IST)
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    current_time = ist_now.strftime("%d-%m-%Y %I:%M %p")
    
    final_lines = ["#EXTM3U"]
    final_lines.append(f'#EXTINF:-1 group-title="Update Info" tvg-logo="https://i.imgur.com/7Xj4G6d.png",🟡 Updated: {current_time}')
    final_lines.append("http://0.0.0.0")
    
    # 3. Process Hardcoded Master List
    print("\n🔨 Building Master List...")
    for group, channel_name in MASTER_CHANNELS:
        target_key = clean_name(channel_name)
        
        # FIND MATCH (Exact or Fuzzy Containment)
        match = None
        if target_key in pocket_map:
            match = pocket_map[target_key]
        else:
            # Fuzzy: Is 'zeetamil' inside 'zeetamilhd'?
            for key, data in pocket_map.items():
                if target_key in key:
                    match = data
                    break
        
        if match:
            final_lines.append(f'#EXTINF:-1 group-title="{group}" tvg-logo="{match["logo"]}",{channel_name}')
            final_lines.append(match['link'])
        else:
            print(f"   ⚠️ Missing: {channel_name}")
            final_lines.append(f'#EXTINF:-1 group-title="{group}" tvg-logo="",⚠️ Offline: {channel_name}')
            final_lines.append("http://0.0.0.0")

    # 4. Add Live Events
    print("\n🎥 Adding Live Events...")
    final_lines.extend(fetch_live_events(FANCODE_URL, "Live Events"))
    final_lines.extend(fetch_live_events(SONY_LIVE_URL, "Live Events"))
    final_lines.extend(fetch_live_events(ZEE_LIVE_URL, "Live Events"))

    # 5. Add Temporary Channels
    print("\n🎥 Adding Temporary Channels...")
    final_lines.extend(parse_youtube_txt())

    # 6. Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
        
    print(f"\n🎉 DONE! Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()