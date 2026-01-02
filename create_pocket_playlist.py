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

# BROWSER HEADER (Required for playback)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 1. YOUR MASTER LIST (Priority Channels)
# We will look for these EXACT channels first.
MASTER_CHANNELS = [
    ("Sports HD", "Star Sports 1 HD"), ("Sports HD", "Star Sports 2 HD"),
    ("Sports HD", "Star Sports 1 Hindi HD"), ("Sports HD", "Star Sports Select 1 HD"),
    ("Sports HD", "Star Sports Select 2 HD"), ("Sports HD", "Sony Sports Ten 1 HD"),
    ("Sports HD", "Sony Sports Ten 2 HD"), ("Sports HD", "Sony Sports Ten 3 HD"),
    ("Sports HD", "Sony Sports Ten 4 HD"), ("Sports HD", "Sony Sports Ten 5 HD"),
    ("Sports HD", "Sports18 1 HD"), ("Sports HD", "Eurosport HD"),
    ("Sports HD", "Astro Cricket"), ("Sports HD", "Willow Cricket"),
    ("Sports HD", "Sky Sports Cricket"),
    ("Tamil HD", "Sun TV HD"), ("Tamil HD", "KTV HD"),
    ("Tamil HD", "Star Vijay HD"), ("Tamil HD", "Zee Tamil HD"),
    ("Tamil HD", "Colors Tamil HD"), ("Tamil HD", "Jaya TV HD"),
    ("Tamil HD", "Zee Thirai HD"), ("Tamil HD", "Vijay Takkar"),
    ("Tamil HD", "Astro Vaanavil"), ("Tamil HD", "Astro Vinmeen HD"),
    ("Tamil HD", "Astro Thangathirai"), ("Tamil HD", "Astro Vellithirai"),
    ("Tamil HD", "Rasi Palan"), ("Tamil HD", "Rasi Movies"),
    ("Infotainment", "Discovery HD"), ("Infotainment", "Animal Planet HD"),
    ("Infotainment", "Nat Geo HD"), ("Infotainment", "Nat Geo Wild HD"),
    ("Infotainment", "Sony BBC Earth HD"), ("Infotainment", "History TV18 HD"),
    ("Infotainment", "TLC HD"), ("Infotainment", "TravelXP HD"),
    ("Movies", "Star Movies HD"), ("Movies", "Sony Pix HD"),
    ("Movies", "Movies Now HD"), ("Movies", "MN+ HD"),
    ("Movies", "MNX HD"), ("Movies", "Star Gold HD"),
    ("Movies", "Sony Max HD"), ("Movies", "Zee Cinema HD"),
    ("Movies", "&Pictures HD"),
    ("Entertainment", "Star Plus HD"), ("Entertainment", "Sony SET HD"),
    ("Entertainment", "Sony SAB HD"), ("Entertainment", "Zee TV HD"),
    ("Entertainment", "Colors HD"), ("Entertainment", "Star Bharat HD"),
    ("Kids", "Nick"), ("Kids", "Sonic"), ("Kids", "Hungama"),
    ("Kids", "Disney Channel"), ("Kids", "Cartoon Network"),
    ("Kids", "Pogo"), ("Kids", "Sony Yay"), ("Kids", "Discovery Kids"),
    ("News", "Times Now"), ("News", "NDTV 24x7"), ("News", "India Today"),
    ("News", "CNN News18"), ("News", "Sun News"), ("News", "Polimer News"),
    ("News", "Puthiya Thalaimurai"), ("News", "Thanthi TV")
]

# ==========================================
# LOGIC
# ==========================================

def simplified_name(name):
    """
    Aggressive cleaner.
    'Star Sports 1 HD (Backup)' -> 'starsports1hd'
    'Zee Tamil' -> 'zeetamil'
    """
    if not name: return ""
    # Remove everything in brackets
    name = re.sub(r'[\(\[\{].*?[\)\]\}]', '', name.lower())
    # Remove all symbols and spaces
    return re.sub(r'[^a-z0-9]', '', name)

def get_source_channels():
    """Downloads the source playlist and returns a searchable list."""
    print("📥 Downloading Source Playlist...")
    channels = []
    try:
        r = requests.get(POCKET_URL, headers={"User-Agent": USER_AGENT}, timeout=20)
        if r.status_code == 200:
            lines = r.text.splitlines()
            for i in range(len(lines)):
                line = lines[i].strip()
                if line.startswith("#EXTINF"):
                    # Parse Name
                    raw_name = line.split(",")[-1].strip()
                    simple = simplified_name(raw_name)
                    
                    # Parse Logo
                    logo = ""
                    m_logo = re.search(r'tvg-logo="([^"]*)"', line)
                    if m_logo: logo = m_logo.group(1)
                    
                    # Parse Group
                    group = ""
                    m_grp = re.search(r'group-title="([^"]*)"', line)
                    if m_grp: group = m_grp.group(1)
                    
                    # Parse Link
                    link = ""
                    if i + 1 < len(lines):
                        pot_link = lines[i+1].strip()
                        if pot_link and not pot_link.startswith("#"):
                            link = pot_link
                            # FIX: Force User-Agent on ALL links
                            if "http" in link and "|" not in link:
                                link += f"|User-Agent={USER_AGENT}"
                    
                    if link and simple:
                        channels.append({
                            'name': raw_name,
                            'simple': simple,
                            'link': link,
                            'logo': logo,
                            'group': group
                        })
        print(f"   ✅ Source loaded: {len(channels)} channels found.")
    except Exception as e:
        print(f"   ❌ Failed to load source: {e}")
    return channels

def main():
    # 1. Get Source Data
    source_channels = get_source_channels()
    
    # Init Playlist
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines = ["#EXTM3U"]
    final_lines.append(f'#EXTINF:-1 group-title="Update Info" tvg-logo="https://i.imgur.com/7Xj4G6d.png",🟡 Updated: {ist_now.strftime("%d-%m-%Y %H:%M")}')
    final_lines.append("http://0.0.0.0")

    # Track added channels to prevent duplicates
    added_ids = set()

    # ---------------------------------------------------------
    # PART 1: ADD MASTER LIST (The specific channels you want)
    # ---------------------------------------------------------
    print("\n1️⃣  Processing Master List...")
    for target_group, target_name in MASTER_CHANNELS:
        target_simple = simplified_name(target_name)
        
        # Search in source
        match = None
        
        # Try 1: Exact Match (zeetamilhd == zeetamilhd)
        for ch in source_channels:
            if ch['simple'] == target_simple:
                match = ch; break
        
        # Try 2: Containment Match (zeetamil in zeetamilhd)
        if not match:
            for ch in source_channels:
                if target_simple in ch['simple']:
                    match = ch; break

        if match:
            final_lines.append(f'#EXTINF:-1 group-title="{target_group}" tvg-logo="{match["logo"]}",{target_name}')
            final_lines.append(match['link'])
            added_ids.add(match['simple'])
        else:
            print(f"   ⚠️ Missing: {target_name}")
            # Add offline placeholder so you know it's missing
            final_lines.append(f'#EXTINF:-1 group-title="{target_group}" tvg-logo="",⚠️ Offline: {target_name}')
            final_lines.append("http://0.0.0.0")

    # ---------------------------------------------------------
    # PART 2: ADD EXTRAS (All Sports & All Tamil)
    # ---------------------------------------------------------
    print("\n2️⃣  Adding Extras (Sports + Tamil)...")
    
    # Keywords to identifying content regardless of group name
    SPORTS_KEYWORDS = ["sport", "cricket", "f1", "racing", "football", "ten", "sony", "astro"]
    TAMIL_KEYWORDS = ["tamil", "sun", "vijay", "zee", "kalaignar", "polimer", "news18 tamil", "thanthi", "puthiya", "jaya"]
    
    count_extras = 0
    
    for ch in source_channels:
        # Skip if already added
        if ch['simple'] in added_ids: continue
        
        grp = ch['group'].lower()
        name = ch['name'].lower()
        final_group = None

        # CHECK 1: Is it in a Sports Group?
        if "sport" in grp:
            final_group = "Sports Extra"
        
        # CHECK 2: Is it in a Tamil Group?
        elif "tamil" in grp:
            final_group = "Tamil Extra"
            
        # CHECK 3: Does the name look like Sports? (Fallback)
        elif any(x in name for x in SPORTS_KEYWORDS) and "sport" in name:
             final_group = "Sports Extra"
             
        # CHECK 4: Does the name look like Tamil? (Fallback)
        elif any(x in name for x in TAMIL_KEYWORDS) and "tamil" in name:
             final_group = "Tamil Extra"

        # Add if matched
        if final_group:
            final_lines.append(f'#EXTINF:-1 group-title="{final_group}" tvg-logo="{ch["logo"]}",{ch["name"]}')
            final_lines.append(ch['link'])
            added_ids.add(ch['simple'])
            count_extras += 1

    print(f"   ✅ Added {count_extras} extra channels.")

    # ---------------------------------------------------------
    # PART 3: LIVE EVENTS & TEMP
    # ---------------------------------------------------------
    print("\n3️⃣  Adding Live Events & Temp...")
    
    def add_external(url, grp_name):
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
            lines = r.text.splitlines()
            for l in lines:
                if l.startswith("#EXTINF"):
                    l = re.sub(r'group-title="[^"]*"', '', l)
                    l = re.sub(r'(#EXTINF:[-0-9]+)', f'\\1 group-title="{grp_name}"', l)
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

    # SAVE
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    print(f"\n🎉 DONE. Playlist saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
