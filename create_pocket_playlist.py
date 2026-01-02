import requests
import re
import datetime
import os

# ==========================================
# CONFIGURATION
# ==========================================
OUTPUT_FILE = "pocket_playlist.m3u"
YOUTUBE_FILE = "youtube.txt"

# SOURCES
POCKET_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/refs/heads/main/index.html"
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SONY_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
ZEE_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# HEADER FOR PLAYBACK
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"

# MASTER LIST (Cleaned: Removed Kannada/Regional groups)
MASTER_CHANNELS = [
    # --- SPORTS HD ---
    ("Sports HD", "Star Sports 1 HD"), ("Sports HD", "Star Sports 2 HD"),
    ("Sports HD", "Star Sports 1 Hindi HD"), ("Sports HD", "Star Sports Select 1 HD"),
    ("Sports HD", "Star Sports Select 2 HD"), ("Sports HD", "Sony Sports Ten 1 HD"),
    ("Sports HD", "Sony Sports Ten 2 HD"), ("Sports HD", "Sony Sports Ten 3 HD"),
    ("Sports HD", "Sony Sports Ten 4 HD"), ("Sports HD", "Sony Sports Ten 5 HD"),
    ("Sports HD", "Sports18 1 HD"), ("Sports HD", "Eurosport HD"),
    ("Sports HD", "Astro Cricket"), ("Sports HD", "Willow Cricket"),
    ("Sports HD", "Sky Sports Cricket"),

    # --- TAMIL HD ---
    ("Tamil HD", "Sun TV HD"), ("Tamil HD", "KTV HD"),
    ("Tamil HD", "Star Vijay HD"), ("Tamil HD", "Zee Tamil HD"),
    ("Tamil HD", "Colors Tamil HD"), ("Tamil HD", "Jaya TV HD"),
    ("Tamil HD", "Zee Thirai HD"), ("Tamil HD", "Vijay Takkar"),
    ("Tamil HD", "Astro Vaanavil"), ("Tamil HD", "Astro Vinmeen HD"),
    ("Tamil HD", "Astro Thangathirai"), ("Tamil HD", "Astro Vellithirai"),
    ("Tamil HD", "Rasi Palan"), ("Tamil HD", "Rasi Movies"),
    
    # --- INFOTAINMENT HD ---
    ("Infotainment", "Discovery HD"), ("Infotainment", "Animal Planet HD"),
    ("Infotainment", "Nat Geo HD"), ("Infotainment", "Nat Geo Wild HD"),
    ("Infotainment", "Sony BBC Earth HD"), ("Infotainment", "History TV18 HD"),
    ("Infotainment", "TLC HD"), ("Infotainment", "TravelXP HD"),

    # --- MOVIES HD ---
    ("Movies", "Star Movies HD"), ("Movies", "Sony Pix HD"),
    ("Movies", "Movies Now HD"), ("Movies", "MN+ HD"),
    ("Movies", "MNX HD"), ("Movies", "Star Gold HD"),
    ("Movies", "Sony Max HD"), ("Movies", "Zee Cinema HD"),
    ("Movies", "&Pictures HD"),

    # --- ENTERTAINMENT HD ---
    ("Entertainment", "Star Plus HD"), ("Entertainment", "Sony SET HD"),
    ("Entertainment", "Sony SAB HD"), ("Entertainment", "Zee TV HD"),
    ("Entertainment", "Colors HD"), ("Entertainment", "Star Bharat HD")
]

# ==========================================
# LOGIC
# ==========================================
def clean_name(name):
    """'Star Sports 1 HD' -> 'starsports1hd'"""
    if not name: return ""
    name = re.sub(r'[\(\[\{].*?[\)\]\}]', '', name.lower())
    return re.sub(r'[^a-z0-9]', '', name)

def get_pocket_data():
    """Loads ALL channels from Pocket TV into a list of dicts."""
    print(f"📥 Loading Pocket TV...")
    channels = []
    try:
        r = requests.get(POCKET_URL, headers={"User-Agent": USER_AGENT}, timeout=15)
        if r.status_code == 200:
            lines = r.text.splitlines()
            for i in range(len(lines)):
                line = lines[i].strip()
                if line.startswith("#EXTINF"):
                    # Extract Name
                    raw_name = line.split(",")[-1].strip()
                    clean = clean_name(raw_name)
                    
                    # Extract Logo
                    logo = ""
                    m = re.search(r'tvg-logo="([^"]*)"', line)
                    if m: logo = m.group(1)
                    
                    # Extract Group
                    grp = ""
                    m_grp = re.search(r'group-title="([^"]*)"', line)
                    if m_grp: grp = m_grp.group(1)

                    # Extract Link
                    link = ""
                    if i + 1 < len(lines):
                        pot_link = lines[i+1].strip()
                        if pot_link and not pot_link.startswith("#"):
                            link = pot_link
                            # FORCE PLAYBACK HEADER
                            if "http" in link and "|" not in link:
                                link += f"|User-Agent={USER_AGENT}"
                    
                    if link:
                        channels.append({
                            'name': raw_name,
                            'clean': clean,
                            'link': link,
                            'logo': logo,
                            'group': grp
                        })
        print(f"   ✅ Loaded {len(channels)} channels.")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    return channels

def main():
    print("--- BUILDING POCKET PLAYLIST ---")
    
    # 1. Load Source Data
    all_pocket_channels = get_pocket_data()
    
    # Time
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    current_time = ist_now.strftime("%d-%m-%Y %I:%M %p")
    
    final_lines = ["#EXTM3U"]
    final_lines.append(f'#EXTINF:-1 group-title="Update Info" tvg-logo="https://i.imgur.com/7Xj4G6d.png",🟡 Updated: {current_time}')
    final_lines.append("http://0.0.0.0")
    
    # Keep track of added channels
    added_keys = set()
    
    # 2. Add MASTER CHANNELS (Priority)
    print("\n1️⃣  Adding Master Channels...")
    for group, name in MASTER_CHANNELS:
        target_clean = clean_name(name)
        
        # Find match
        match = None
        for ch in all_pocket_channels:
            # Exact Match OR Fuzzy Match
            if target_clean == ch['clean'] or target_clean in ch['clean']:
                match = ch
                break
        
        if match:
            final_lines.append(f'#EXTINF:-1 group-title="{group}" tvg-logo="{match["logo"]}",{name}')
            final_lines.append(match['link'])
            added_keys.add(match['clean'])
        else:
            print(f"   ⚠️ Missing: {name}")
            final_lines.append(f'#EXTINF:-1 group-title="{group}" tvg-logo="",⚠️ Offline: {name}')
            final_lines.append("http://0.0.0.0")

    # 3. Add EXTRAS (Strictly Sports & Tamil ONLY)
    print("\n2️⃣  Adding Extras (Sports & Tamil)...")
    
    for ch in all_pocket_channels:
        # Skip if already added
        if ch['clean'] in added_keys:
            continue
            
        grp_lower = ch['group'].lower()
        
        target_group = None
        
        # STRICT GROUP CHECKING
        # If the source group contains "sport", put in Sports Extra
        if "sport" in grp_lower:
            target_group = "Sports Extra"
        # If the source group contains "tamil", put in Tamil Extra
        elif "tamil" in grp_lower:
            target_group = "Tamil Extra"
        
        # IGNORE ALL OTHER GROUPS (Kannada, Malayalam, Hindi, etc.)
            
        if target_group:
            final_lines.append(f'#EXTINF:-1 group-title="{target_group}" tvg-logo="{ch["logo"]}",{ch["name"]}')
            final_lines.append(ch['link'])
            added_keys.add(ch['clean'])

    # 4. Live Events & Temp
    print("\n3️⃣  Adding Live Events & Temp...")
    
    def add_external(url, grp):
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT})
            lines = r.text.splitlines()
            for l in lines:
                if l.startswith("#EXTINF"):
                    l = re.sub(r'group-title="[^"]*"', '', l)
                    l = re.sub(r'(#EXTINF:[-0-9]+)', f'\\1 group-title="{grp}"', l)
                    final_lines.append(l)
                elif l.startswith("http"):
                    final_lines.append(l)
        except: pass

    add_external(FANCODE_URL, "Live Events")
    add_external(SONY_LIVE_URL, "Live Events")
    add_external(ZEE_LIVE_URL, "Live Events")

    if os.path.exists(YOUTUBE_FILE):
        with open(YOUTUBE_FILE, "r") as f:
            for l in f:
                if "title" in l.lower():
                     final_lines.append(f'#EXTINF:-1 group-title="Temporary" tvg-logo="",{l.split(":",1)[1].strip()}')
                elif l.startswith("http"):
                     final_lines.append(l.strip())

    # 5. Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    print(f"\n✅ DONE! Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
