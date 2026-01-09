import requests
import re
import difflib
import datetime

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================
# MAIN SOURCE (HTML Format accepted now)
URL_ARUNJUNAN = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html"
URL_FORCEGT   = "https://raw.githubusercontent.com/ForceGT/Discord-IPTV/master/playlist.m3u"

# Pass-Through Sources
URL_YOUTUBE   = "https://raw.githubusercontent.com/nkmisc88-jpg/my-youtube-live-playlist/refs/heads/main/playlist.m3u"
URL_FANCODE   = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
URL_SONY      = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
URL_ZEE5      = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

FILE_TEMP     = "temp.txt"
OUTPUT_FILE   = "nktv.m3u"

# ==============================================================================
# 2. MASTER SKELETON
# ==============================================================================
MASTER_SKELETON = {
    "Tamil HD": [
        ("Sun TV HD", "ts1503", "https://jiotvimages.cdn.jio.com/dare_images/images/Sun_TV_HD.png"),
        ("Star Vijay HD", "ts1506", "https://jiotvimages.cdn.jio.com/dare_images/images/Star_Vijay_HD.png"),
        ("Zee Tamil HD", "ts1509", "https://jiotvimages.cdn.jio.com/dare_images/images/Zee_Tamil_HD.png"),
        ("Colors Tamil HD", "ts1515", "https://jiotvimages.cdn.jio.com/dare_images/images/Colors_Tamil_HD.png"),
        ("KTV HD", "ts1517", "https://jiotvimages.cdn.jio.com/dare_images/images/KTV_HD.png"),
        ("Sun Music HD", "ts1527", "https://jiotvimages.cdn.jio.com/dare_images/images/Sun_Music_HD.png"),
        ("Vijay Super HD", "ts1513", "https://jiotvimages.cdn.jio.com/dare_images/images/Vijay_Super_HD.png"),
        ("Zee Thirai HD", "ts1545", "https://bit.ly/3Xj5QzL"),
        ("Jaya TV HD", "ts1505", "https://jiotvimages.cdn.jio.com/dare_images/images/Jaya_TV_HD.png"),
    ],
    "Sports HD": [
        ("Star Sports 1 Tamil HD", "ts1550", "https://jiotvimages.cdn.jio.com/dare_images/images/Star_Sports_1_Tamil_HD.png"),
        ("Star Sports 2 Tamil HD", "ts1551", "https://bit.ly/4dKjL2M"),
        ("Star Sports 1 Telugu HD", "ts1445", "https://jiotvimages.cdn.jio.com/dare_images/images/Star_Sports_1_Telugu_HD.png"),
        ("Star Sports 2 Telugu HD", "ts1446", "https://bit.ly/3Xk1L2M"),
        ("Star Sports 1 HD", "ts454", "https://jiotvimages.cdn.jio.com/dare_images/images/Star_Sports_1_HD.png"),
        ("Star Sports 2 HD", "ts456", "https://jiotvimages.cdn.jio.com/dare_images/images/Star_Sports_2_HD.png"),
        ("Star Sports 1 Hindi HD", "ts459", "https://jiotvimages.cdn.jio.com/dare_images/images/Star_Sports_1_Hindi_HD.png"),
        ("Star Sports 2 Hindi HD", "ts461", "https://bit.ly/4eM2P1K"),
        ("Sony Sports Ten 1 HD", "ts470", "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_Sports_Ten_1_HD.png"),
        ("Sony Sports Ten 2 HD", "ts473", "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_Sports_Ten_2_HD.png"),
        ("Sony Sports Ten 3 HD", "ts476", "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_Sports_Ten_3_HD.png"),
        ("Sony Sports Ten 4 HD", "ts1552", "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_Sports_Ten_4_HD.png"),
        ("Sony Sports Ten 5 HD", "ts483", "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_Sports_Ten_5_HD.png"),
        ("Eurosport HD", "ts494", "https://jiotvimages.cdn.jio.com/dare_images/images/Eurosport_HD.png"),
    ],
    "Global Sports": [
        ("Astro Cricket", "", "https://i.imgur.com/OpM4n4m.png"),
        ("Fox Cricket 501", "", "https://i.imgur.com/712345.png"),
        ("Fox Sports 505", "", "https://i.imgur.com/712346.png"),
        ("Willow Sports", "", "https://i.imgur.com/willow1.png"),
        ("Willow Sports Extra", "", "https://i.imgur.com/willow2.png"),
        ("Sky Sports Cricket", "", "https://i.imgur.com/skycricket.png"),
        ("TNT Sports 1", "", "https://i.imgur.com/tnt1.png"),
        ("TNT Sports 2", "", "https://i.imgur.com/tnt2.png"),
    ],
    "Tamil News": [
        ("Polimer News", "ts1562", "https://jiotvimages.cdn.jio.com/dare_images/images/Polimer_News.png"),
        ("Puthiya Thalaimurai", "ts1558", "https://jiotvimages.cdn.jio.com/dare_images/images/Puthiya_Thalaimurai.png"),
        ("Sun News", "ts1556", "https://jiotvimages.cdn.jio.com/dare_images/images/Sun_News.png"),
        ("Thanthi TV", "ts1560", "https://jiotvimages.cdn.jio.com/dare_images/images/Thanthi_TV.png"),
        ("News18 Tamil Nadu", "ts1557", "https://jiotvimages.cdn.jio.com/dare_images/images/News18_Tamil_Nadu.png"),
    ],
    "Infotainment HD": [
        ("Discovery HD", "ts713", "https://jiotvimages.cdn.jio.com/dare_images/images/Discovery_HD_World.png"),
        ("Animal Planet HD", "ts718", "https://jiotvimages.cdn.jio.com/dare_images/images/Animal_Planet_HD_World.png"),
        ("Nat Geo HD", "ts724", "https://jiotvimages.cdn.jio.com/dare_images/images/Nat_Geo_HD.png"),
        ("Sony BBC Earth HD", "ts733", "https://jiotvimages.cdn.jio.com/dare_images/images/Sony_BBC_Earth_HD.png"),
        ("History TV18 HD", "ts728", "https://jiotvimages.cdn.jio.com/dare_images/images/History_TV18_HD.png"),
        ("Zee Zest HD", "ts748", "https://jiotvimages.cdn.jio.com/dare_images/images/Zee_Zest_HD.png"),
        ("TLC HD", "ts743", "https://jiotvimages.cdn.jio.com/dare_images/images/TLC_HD.png"),
    ]
}

# ==============================================================================
# 3. HELPER FUNCTIONS
# ==============================================================================

def get_ist_time():
    """Returns current IST time"""
    utc_now = datetime.datetime.utcnow()
    ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
    return ist_now.strftime("%Y-%m-%d %H:%M:%S IST")

def normalize(text):
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

def clean_html_line(line):
    """Removes HTML tags like <br>, <pre> from a line"""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', line)
    return clean.strip()

def fetch_content(url):
    """Fetches content, handling both HTML and M3U"""
    print(f"Fetching: {url} ... ", end="")
    entries = []
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        
        # Split by lines
        lines = resp.text.splitlines()
        
        name = ""
        for line in lines:
            line = clean_html_line(line)
            
            if not line: continue
            
            if line.startswith("#EXTINF"):
                if "," in line:
                    name = line.split(",")[-1].strip()
            # Check for HTTP link (basic check)
            elif line.startswith("http") and name:
                entries.append({'name': name, 'url': line})
                name = "" # Reset
        
        print(f"Success ({len(entries)} channels)")
        return entries
        
    except Exception as e:
        print(f"Error: {e}")
        return []

def get_mapped_streams(urls):
    mapped = {}
    source_names = []
    
    for url in urls:
        items = fetch_content(url)
        for item in items:
            key = normalize(item['name'])
            if key not in mapped:
                mapped[key] = []
                source_names.append(item['name'])
            if item['url'] not in mapped[key]:
                mapped[key].append(item['url'])
                
    return mapped, source_names

def find_best_match(target, options):
    target_clean = normalize(target)
    for opt in options:
        if normalize(opt) == target_clean: return normalize(opt)
    
    matches = [opt for opt in options if target_clean in normalize(opt)]
    if matches: return normalize(min(matches, key=len))
    
    matches = difflib.get_close_matches(target, options, n=1, cutoff=0.5)
    if matches: return normalize(matches[0])
    return None

def parse_temp_file(filename):
    channels = []
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
                    if line.startswith("Logo"):
                        logo = line.split(":", 1)[1].strip()
                    if line.startswith("Link"):
                        link = line.split(":", 1)[1].strip()
                        
                if name and link:
                    channels.append({'name': name, 'logo': logo, 'url': link})
    except FileNotFoundError:
        print(f"Warning: {filename} not found.")
    return channels

# ==============================================================================
# 4. MAIN LOGIC
# ==============================================================================

def main():
    ist_time = get_ist_time()
    final_lines = [
        '#EXTM3U x-tvg-url="https://avkb.short.gy/tsepg.xml.gz"',
        f'#EXTINF:-1 group-title="System" tvg-logo="", Playlist Updated: {ist_time}',
        'http://localhost/timestamp'
    ]
    
    # --- PART A: MASTER CHANNELS ---
    print("\n--- Processing Master Channels ---")
    all_streams, source_names = get_mapped_streams([URL_ARUNJUNAN, URL_FORCEGT])
    
    backup_lines = []
    
    for group, channels in MASTER_SKELETON.items():
        for name, tvg_id, logo in channels:
            key = find_best_match(name, source_names)
            
            if key and key in all_streams:
                urls = all_streams[key]
                final_lines.append(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{logo}" group-title="{group}", {name}\n{urls[0]}')
                
                for idx, url in enumerate(urls[1:], 1):
                    backup_lines.append(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{logo}" group-title="Backups", {name} [Backup {idx}]\n{url}')
                print(f"[OK] {name}")
            else:
                print(f"[MISSING] {name}")
    
    # --- PART B: LIVE EVENTS ---
    print("\n--- Processing Live Events ---")
    live_sources = [URL_FANCODE, URL_SONY, URL_ZEE5]
    for source in live_sources:
        items = fetch_content(source)
        for item in items:
            final_lines.append(f'#EXTINF:-1 group-title="Live Events" tvg-logo="", {item["name"]}\n{item["url"]}')
            
    # --- PART C: YOUTUBE ---
    print("\n--- Processing YouTube ---")
    yt_items = fetch_content(URL_YOUTUBE)
    for item in yt_items:
         final_lines.append(f'#EXTINF:-1 group-title="YouTube" tvg-logo="https://i.imgur.com/MbCpK4X.png", {item["name"]}\n{item["url"]}')
         
    # --- PART D: TEMPORARY CHANNELS ---
    print("\n--- Processing Temporary Channels ---")
    temp_items = parse_temp_file(FILE_TEMP)
    for item in temp_items:
        final_lines.append(f'#EXTINF:-1 group-title="Temporary" tvg-logo="{item["logo"]}", {item["name"]}\n{item["url"]}')

    # --- WRITE FILE ---
    final_lines.extend(backup_lines)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
        
    print(f"\nSUCCESS: Generated {OUTPUT_FILE} with {len(final_lines)} entries.")

if __name__ == "__main__":
    main()
