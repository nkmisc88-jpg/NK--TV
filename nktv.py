import requests
import re
import datetime

# ==============================================================================
# 1. SOURCES
# ==============================================================================
URL_TIGER     = "https://raw.githubusercontent.com/tiger629/m3u/refs/heads/main/joker.m3u"
URL_ARUNJUNAN = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html"
URL_FORCEGT   = "https://raw.githubusercontent.com/ForceGT/Discord-IPTV/master/playlist.m3u"

URL_YOUTUBE   = "https://raw.githubusercontent.com/nkmisc88-jpg/my-youtube-live-playlist/refs/heads/main/playlist.m3u"
URL_FANCODE   = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
URL_SONY      = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
URL_ZEE5      = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

FILE_TEMP     = "temp.txt"
OUTPUT_FILE   = "nktv.m3u"

# ==============================================================================
# 2. MASTER LIST (The Filter)
# ==============================================================================
# The script will only keep channels that contain these names.
# It will assign them to the Group listed here.

MASTER_FILTER = {
    "Tamil HD": [
        "Sun TV HD", "SunTV HD", "Star Vijay HD", "Vijay TV HD", "Zee Tamil HD", 
        "Colors Tamil HD", "KTV HD", "Sun Music HD", "Vijay Super HD", 
        "Zee Thirai HD", "Jaya TV HD"
    ],
    "Tamil News": [
        "Polimer News", "Puthiya Thalaimurai", "Sun News", "Thanthi TV", 
        "News18 Tamil", "News7 Tamil", "Kalaignar Seithigal", "Captain News"
    ],
    "Tamil Others": [
        "Adithya TV", "Sirippoli", "Murasu", "Sun Life", "Kalaignar TV", "Jaya Max", "J Movies"
    ],
    "Sports HD": [
        "Star Sports 1 Tamil", "Star Sports 1 Telugu", "Star Sports 1 Kannada",
        "Star Sports 1 HD", "Star Sports 2 HD", "Star Sports 1 Hindi",
        "Sony Sports Ten 1", "Sony Ten 1 HD", 
        "Sony Sports Ten 2", "Sony Ten 2 HD",
        "Sony Sports Ten 3", "Sony Ten 3 HD",
        "Sony Sports Ten 4", "Sony Ten 4 HD",
        "Sony Sports Ten 5", "Sony Ten 5 HD",
        "Eurosport", "Sports18 1"
    ],
    "Global Sports": [
        "Astro Cricket", "Fox Cricket", "Fox Sports", "Willow", "Sky Sports", "TNT Sports"
    ],
    "Infotainment HD": [
        "Discovery HD", "Animal Planet HD", "Nat Geo HD", "Nat Geo Wild", 
        "Sony BBC", "History TV18", "Zee Zest", "TLC"
    ]
}

# ==============================================================================
# 3. CORE LOGIC
# ==============================================================================

def get_ist_time():
    utc_now = datetime.datetime.utcnow()
    ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
    return ist_now.strftime("%Y-%m-%d %H:%M:%S IST")

def clean_html(text):
    """Removes HTML tags from Arunjunan source"""
    return re.sub(r'<[^>]+>', '', text).strip()

def fix_playback_link(url):
    """Adds User-Agent to ensure playback works"""
    url = url.strip()
    if "|" not in url and "googlevideo" not in url:
        return f"{url}|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    return url

def fetch_all_channels(urls):
    """Downloads EVERYTHING from given URLs into a raw list"""
    pool = []
    for url in urls:
        print(f"Harvesting: {url} ... ", end="")
        try:
            resp = requests.get(url, timeout=30)
            lines = resp.text.splitlines()
            
            name = ""
            logo = ""
            for line in lines:
                line = clean_html(line)
                if not line: continue
                
                if line.startswith("#EXTINF"):
                    # Extract Name
                    if "," in line:
                        name = line.split(",")[-1].strip()
                    # Extract Logo
                    if 'tvg-logo="' in line:
                        parts = line.split('tvg-logo="')
                        if len(parts) > 1:
                            logo = parts[1].split('"')[0]
                
                elif line.startswith("http") and name:
                    pool.append({'name': name, 'logo': logo, 'url': line})
                    name = ""
                    logo = ""
            print(f"Found {len(pool)} total channels so far.")
        except Exception as e:
            print(f"Error: {e}")
    return pool

def parse_temp_file(filename):
    """Parses your temp.txt file"""
    entries = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            blocks = re.split(r'Title\s*:', content)
            for block in blocks:
                if not block.strip(): continue
                lines = block.split('\n')
                name = lines[0].strip()
                logo = ""
                link = ""
                for line in lines:
                    if line.startswith("Logo"): logo = line.split(":", 1)[1].strip()
                    if line.startswith("Link"): link = line.split(":", 1)[1].strip()
                
                if name and link:
                    entries.append({'name': name, 'logo': logo, 'url': link})
    except: pass
    return entries

# ==============================================================================
# 4. MAIN RUN
# ==============================================================================

def main():
    final_playlist = [
        '#EXTM3U x-tvg-url="https://avkb.short.gy/tsepg.xml.gz"',
        f'#EXTINF:-1 group-title="System" tvg-logo="", Playlist Updated: {get_ist_time()}',
        'http://localhost/timestamp'
    ]

    # --- STEP 1: HARVEST MAIN SOURCES ---
    print("\n1. Harvesting Sources...")
    raw_channels = fetch_all_channels([URL_TIGER, URL_ARUNJUNAN, URL_FORCEGT])
    
    # --- STEP 2: FILTER & GROUP ---
    print("\n2. Filtering & Grouping...")
    added_links = set()
    
    for group_name, keywords in MASTER_FILTER.items():
        count = 0
        for keyword in keywords:
            for ch in raw_channels:
                # Check if keyword matches channel name (Case Insensitive)
                if keyword.lower() in ch['name'].lower():
                    
                    # Fix Link
                    link = fix_playback_link(ch['url'])
                    
                    # Avoid duplicates
                    if link in added_links: continue
                    
                    # Add to Final
                    final_playlist.append(f'#EXTINF:-1 group-title="{group_name}" tvg-logo="{ch["logo"]}", {ch["name"]}')
                    final_playlist.append(link)
                    
                    added_links.add(link)
                    count += 1
        print(f"   -> {group_name}: Added {count} channels")

    # --- STEP 3: LIVE EVENTS ---
    print("\n3. Adding Live Events...")
    live_channels = fetch_all_channels([URL_FANCODE, URL_SONY, URL_ZEE5])
    for ch in live_channels:
        final_playlist.append(f'#EXTINF:-1 group-title="Live Events" tvg-logo="{ch["logo"]}", {ch["name"]}')
        final_playlist.append(ch['url'])

    # --- STEP 4: YOUTUBE ---
    print("\n4. Adding YouTube...")
    yt_channels = fetch_all_channels([URL_YOUTUBE])
    for ch in yt_channels:
        final_playlist.append(f'#EXTINF:-1 group-title="YouTube" tvg-logo="https://i.imgur.com/MbCpK4X.png", {ch["name"]}')
        final_playlist.append(ch['url'])

    # --- STEP 5: TEMP ---
    print("\n5. Adding Temp...")
    temp_channels = parse_temp_file(FILE_TEMP)
    for ch in temp_channels:
        link = fix_playback_link(ch['url'])
        final_playlist.append(f'#EXTINF:-1 group-title="Temporary" tvg-logo="{ch["logo"]}", {ch["name"]}')
        final_playlist.append(link)

    # --- STEP 6: SAVE ---
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_playlist))
    
    print(f"\nDONE! Playlist generated with {len(final_playlist)//2} entries.")

if __name__ == "__main__":
    main()