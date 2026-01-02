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

# HEADERS (Standard for Jio playback)
USER_AGENT = "plaYtv/7.0.8 (Linux;Android 9) ExoPlayerLib/2.11.7"

# MASTER LIST
# Note: Changed "Zee Tamil HD" -> "Zee Tamil" to match broader source names
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
    ("Tamil HD", "Star Vijay HD"), ("Tamil HD", "Zee Tamil"),
    ("Tamil HD", "Colors Tamil HD"), ("Tamil HD", "Jaya TV HD"),
    ("Tamil HD", "Zee Thirai"), ("Tamil HD", "Vijay Takkar"),
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
    if not name: return ""
    name = re.sub(r'[\(\[\{].*?[\)\]\}]', '', name.lower())
    return re.sub(r'[^a-z0-9]', '', name)

def get_source_channels():
    print("📥 Downloading Source Playlist...")
    channels = []
    try:
        r = requests.get(POCKET_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if r.status_code == 200:
            lines = r.text.splitlines()
            current_props = [] 
            
            for i in range(len(lines)):
                line = lines[i].strip()
                
                # 1. COPY LICENSE KEYS
                if line.startswith("#KODIPROP") or line.startswith("#EXTVLCOPT"):
                    current_props.append(line)
                    continue

                # 2. Process Channel Info
                if line.startswith("#EXTINF"):
                    raw_name = line.split(",")[-1].strip()
                    simple = simplified_name(raw_name)
                    
                    logo = ""
                    m_logo = re.search(r'tvg-logo="([^"]*)"', line)
                    if m_logo: logo = m_logo.group(1)
                    
                    link = ""
                    if i + 1 < len(lines):
                        pot_link = lines[i+1].strip()
                        if pot_link and not pot_link.startswith("#"):
                            link = pot_link
                            # Append Headers
                            if "http" in link and "|" not in link:
                                link += f"|User-Agent={USER_AGENT}"
                    
                    if link and simple:
                        channels.append({
                            'name': raw_name,
                            'simple': simple,
                            'link': link,
                            'logo': logo,
                            'props': current_props,
                            'group_src': line # Store original line for group checking later
                        })
                    
                    current_props = []
                    
    except Exception as e:
        print(f"   ❌ Failed to load source: {e}")
    return channels

def main():
    source_channels = get_source_channels()
    
    # Init Playlist (No Update Info line)
    final_lines = ["#EXTM3U"]
    final_lines.append("http://0.0.0.0")

    added_ids = set()

    # 1. MASTER LIST
    print("\n1️⃣  Processing Master List...")
    for target_group, target_name in MASTER_CHANNELS:
        target_simple = simplified_name(target_name)
        match = None
        
        # Priority: Exact Match -> Fuzzy Match
        for ch in source_channels:
            if ch['simple'] == target_simple:
                match = ch; break
        if not match:
            for ch in source_channels:
                if target_simple in ch['simple']:
                    match = ch; break

        if match:
            # Write Props (DRM Keys)
            if match['props']: final_lines.extend(match['props'])
            
            final_lines.append(f'#EXTINF:-1 group-title="{target_group}" tvg-logo="{match["logo"]}",{target_name}')
            final_lines.append(match['link'])
            added_ids.add(match['simple'])
        else:
            # DO NOT ADD TO PLAYLIST if missing
            print(f"   ⚠️ Skipping Missing Channel: {target_name}")

    # 2. EXTRAS (Sports + Tamil)
    print("\n2️⃣  Adding Extras...")
    SPORTS_KEYS = ["sport", "cricket", "f1", "racing", "football", "ten", "sony", "astro"]
    TAMIL_KEYS = ["tamil", "sun", "vijay", "zee", "kalaignar", "polimer", "news18 tamil", "thanthi", "puthiya", "jaya"]
    
    for ch in source_channels:
        if ch['simple'] in added_ids: continue
        
        name = ch['name'].lower()
        # Parse Group from original line for better accuracy
        grp_match = re.search(r'group-title="([^"]*)"', ch['group_src'])
        grp = grp_match.group(1).lower() if grp_match else ""

        final_group = None
        if "sport" in grp: final_group = "Sports Extra"
        elif "tamil" in grp: final_group = "Tamil Extra"
        elif any(x in name for x in SPORTS_KEYS) and "sport" in name: final_group = "Sports Extra"
        elif any(x in name for x in TAMIL_KEYS) and "tamil" in name: final_group = "Tamil Extra"

        if final_group:
            if ch['props']: final_lines.extend(ch['props'])
            final_lines.append(f'#EXTINF:-1 group-title="{final_group}" tvg-logo="{ch["logo"]}",{ch["name"]}')
            final_lines.append(ch['link'])
            added_ids.add(ch['simple'])

    # 3. LIVE & TEMP
    print("\n3️⃣  Adding Live/Temp...")
    def add_ext(url, g):
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            for l in r.text.splitlines():
                if l.startswith("#EXTINF"):
                    l = re.sub(r'group-title="[^"]*"', '', l)
                    l = re.sub(r'(#EXTINF:[-0-9]+)', f'\\1 group-title="{g}"', l)
                    final_lines.append(l)
                elif l.startswith("#KODIPROP") or l.startswith("#EXTVLCOPT"):
                    final_lines.append(l)
                elif l.startswith("http"): final_lines.append(l)
        except: pass

    add_ext(FANCODE_URL, "Live Events")
    add_ext(SONY_LIVE_URL, "Live Events")
    add_ext(ZEE_LIVE_URL, "Live Events")

    if os.path.exists(YOUTUBE_FILE):
        with open(YOUTUBE_FILE, "r") as f:
            for l in f:
                if "title" in l.lower(): final_lines.append(f'#EXTINF:-1 group-title="Temporary" tvg-logo="",{l.split(":",1)[1].strip()}')
                elif l.startswith("http"): final_lines.append(l.strip())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print(f"\n✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
