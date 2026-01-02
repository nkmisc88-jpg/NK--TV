import requests
import re
import datetime

# ==========================================
# CONFIGURATION
# ==========================================
# 1. THE REFERENCE SOURCE (Pocket TV)
POCKET_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/refs/heads/main/index.html"

# 2. OUTPUT FILE NAME
OUTPUT_FILE = "pocket_playlist.m3u"

# 3. YOUR MASTER CHANNEL LIST (Hardcoded to avoid errors)
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
    # Remove things in brackets
    name = re.sub(r'[\(\[\{].*?[\)\]\}]', '', name.lower())
    # Remove ALL non-alphanumeric chars (including spaces)
    return re.sub(r'[^a-z0-9]', '', name)

def fetch_pocket_map():
    """
    Downloads Pocket TV playlist and builds a map:
    {'zeetamilhd': {'link': 'http...', 'logo': 'http...'}}
    """
    print(f"📥 Loading Pocket TV Reference...")
    data_map = {}
    try:
        # Browser Header is CRITICAL for some channels to load
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
        r = requests.get(POCKET_URL, headers={"User-Agent": ua}, timeout=15)
        
        if r.status_code == 200:
            lines = r.text.splitlines()
            for i in range(len(lines)):
                line = lines[i].strip()
                if line.startswith("#EXTINF"):
                    # Extract Name
                    raw_name = line.split(",")[-1].strip()
                    key = clean_name(raw_name)
                    
                    # Extract Logo
                    logo = ""
                    m = re.search(r'tvg-logo="([^"]*)"', line)
                    if m: logo = m.group(1)
                    
                    # Extract Link
                    link = ""
                    if i + 1 < len(lines):
                        pot_link = lines[i+1].strip()
                        if pot_link and not pot_link.startswith("#"):
                            link = pot_link
                            # APPEND USER AGENT TO LINK FOR PLAYBACK
                            if "http" in link and "|" not in link:
                                link += f"|User-Agent={ua}"
                    
                    if key and link:
                        # Store both exact key and tokens for flexible matching if needed
                        data_map[key] = {'link': link, 'logo': logo, 'raw_name': raw_name}
                        
            print(f"   ✅ Loaded {len(data_map)} channels from Pocket TV.")
    except Exception as e:
        print(f"   ❌ Error loading Pocket TV: {e}")
    return data_map

def find_channel(target_name, data_map):
    target_clean = clean_name(target_name)
    
    # 1. Exact Clean Match (zeetamilhd == zeetamilhd)
    if target_clean in data_map:
        return data_map[target_clean]
    
    # 2. Fuzzy Containment (target 'zeetamil' inside source 'zeetamilbackup')
    for key, data in data_map.items():
        if target_clean in key:
            return data
            
    return None

def main():
    print("--- GENERATING POCKET PLAYLIST ---")
    
    # 1. Get the Map
    pocket_map = fetch_pocket_map()
    
    # 2. Start Building Playlist
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_lines = ["#EXTM3U", f"# Updated on: {current_time}"]
    
    found_count = 0
    missing_count = 0
    
    # 3. Loop through Master List
    for group, channel_name in MASTER_CHANNELS:
        match = find_channel(channel_name, pocket_map)
        
        if match:
            # Use source logo if available
            logo = match['logo']
            link = match['link']
            
            final_lines.append(f'#EXTINF:-1 group-title="{group}" tvg-logo="{logo}",{channel_name}')
            final_lines.append(link)
            found_count += 1
        else:
            print(f"   ⚠️ Missing: {channel_name}")
            final_lines.append(f'#EXTINF:-1 group-title="{group}" tvg-logo="",⚠️ Offline: {channel_name}')
            final_lines.append("http://0.0.0.0")
            missing_count += 1

    # 4. Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
        
    print(f"\n🎉 DONE! Saved to {OUTPUT_FILE}")
    print(f"   ✅ Found: {found_count}")
    print(f"   ❌ Missing: {missing_count}")

if __name__ == "__main__":
    main()
