import requests
import re
import datetime

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================
# SOURCES (We will harvest ALL channels from these)
URL_TIGER     = "https://raw.githubusercontent.com/tiger629/m3u/refs/heads/main/joker.m3u"
URL_ARUNJUNAN = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html"
URL_FORCEGT   = "https://raw.githubusercontent.com/ForceGT/Discord-IPTV/master/playlist.m3u"

# LIVE & YOUTUBE
URL_YOUTUBE   = "https://raw.githubusercontent.com/nkmisc88-jpg/my-youtube-live-playlist/refs/heads/main/playlist.m3u"
URL_FANCODE   = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
URL_SONY      = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
URL_ZEE5      = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

FILE_TEMP     = "temp.txt"
OUTPUT_FILE   = "nktv.m3u"

# ==============================================================================
# 2. FILTER RULES (The "Master List" Logic)
# ==============================================================================
# Format: "Group Name": ["Keyword 1", "Keyword 2"]
# The script will search for these exact phrases in the harvested list.
GROUP_RULES = {
    "Tamil HD": [
        "Sun TV HD", "SunTV HD", "Star Vijay HD", "Vijay TV HD", "Zee Tamil HD", 
        "Colors Tamil HD", "KTV HD", "Sun Music HD", "Vijay Super HD", 
        "Zee Thirai HD", "Jaya TV HD"
    ],
    "Sports HD": [
        "Star Sports 1 Tamil HD", "Star Sports 1 Telugu HD", "Star Sports 1 Kannada",
        "Star Sports 1 HD", "Star Sports 2 HD", "Star Sports 1 Hindi HD",
        "Sony Sports Ten 1 HD", "Sony Ten 1 HD", 
        "Sony Sports Ten 2 HD", "Sony Ten 2 HD",
        "Sony Sports Ten 3 HD", "Sony Ten 3 HD",
        "Sony Sports Ten 4 HD", "Sony Ten 4 HD",
        "Sony Sports Ten 5 HD", "Sony Ten 5 HD",
        "Eurosport HD", "Sports18 1 HD"
    ],
    "Global Sports": [
        "Astro Cricket", "Fox Cricket", "Fox Sports", "Willow", "Sky Sports Cricket", "TNT Sports"
    ],
    "Tamil News": [
        "Polimer News", "Puthiya Thalaimurai", "Sun News", "Thanthi TV", 
        "News18 Tamil", "News7 Tamil", "Kalaignar Seithigal", "Captain News"
    ],
    "Infotainment HD": [
        "Discovery HD", "Animal Planet HD", "Nat Geo HD", "Nat Geo Wild", 
        "Sony BBC Earth", "History TV18", "Zee Zest", "TLC"
    ],
    "Tamil Others": [
        "Adithya TV", "Sirippoli", "Murasu", "Sun Life", "Kalaignar TV"
    ]
}

# ==============================================================================
# 3. HELPER FUNCTIONS
# ==============================================================================

def get_ist_time():
    utc_now = datetime.datetime.utcnow()
    ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
    return ist_now.strftime("%Y-%m-%d %H:%M:%S IST")

def clean_line(line):
    # Remove HTML tags and whitespace
    return re.sub(r'<[^>]+>', '', line).strip()

def fix_url(url):
    """Applies the playback fix (User-Agent)"""
    url = url.strip()
    if "|" not in url and "googlevideo" not in url:
        return f"{url}|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    return url

def harvest_all_channels(urls):
    """Downloads EVERYTHING from all sources into a list of dicts"""
    harvested = []
    
    for url in urls:
        print(f"Harvesting: {url} ... ", end="")
        try:
            resp = requests.get(url, timeout=30)
            lines = resp.text.splitlines()
            
            name = ""
            logo = ""
            group = ""
            
            for line in lines:
                line = clean_line(line)
                if not line: continue
                
                if line.startswith("#EXTINF"):
                    # Extract Name
                    if "," in line:
                        name = line.split(",")[-1].strip()
                    # Extract Logo (Optional)
                    if 'tvg-logo="' in line:
                        logo = line.split('tvg-logo="')[1].split('"')[0]
                    # Extract existing group (Optional)
                    if 'group-title="' in line:
                        group = line.split('group-title="')[1].split('"')[0]
                        
                elif line.startswith("http") and name:
                    harvested.append({
                        'name': name,
                        'logo': logo,
                        'url': line, # Keep original URL for now
                        'orig_group': group
                    })
                    name = "" # Reset
                    logo = ""
            print(f"Got {len(lines)} lines")
            
        except Exception as e:
            print(f"Error: {e}")
            
    print(f"Total Harvested Channels: {len(harvested)}")
    return harvested

def parse_temp_file(filename):
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
                    entries.append({'name': name, 'logo': logo, 'url': link, 'group': 'Temporary'})
    except: pass
    return entries

# ==============================================================================
# 4. MAIN LOGIC
# ==============================================================================

def main():
    final_lines = [
        '#EXTM3U x-tvg-url="https://avkb.short.gy/tsepg.xml.gz"',
        f'#EXTINF:-1 group-title="System" tvg-logo="", Playlist Updated: {get_ist_time()}',
        'http://localhost/timestamp'
    ]
    
    # 1. HARVEST EVERYTHING
    all_channels = harvest_all_channels([URL_TIGER, URL_ARUNJUNAN, URL_FORCEGT])
    
    # 2. FILTER & GROUP (The "Master List" Step)
    print("\n--- Filtering Channels ---")
    
    # Keep track of added URLs to avoid duplicates in the same group
    added_urls = set()
    
    for target_group, keywords in GROUP_RULES.items():
        count = 0
        for keyword in keywords:
            # Search our harvested pile
            for ch in all_channels:
                # Case-insensitive check: does channel name contain keyword?
                # e.g. "Sun TV HD (Backup)" contains "Sun TV HD"
                if keyword.lower() in ch['name'].lower():
                    
                    # Fix URL for playback
                    playable_url = fix_url(ch['url'])
                    
                    # Avoid exact duplicates
                    if playable_url in added_urls:
                        continue
                        
                    # Add to playlist
                    final_lines.append(f'#EXTINF:-1 group-title="{target_group}" tvg-logo="{ch["logo"]}", {ch["name"]}')
                    final_lines.append(playable_url)
                    
                    added_urls.add(playable_url)
                    count += 1
        print(f"Group '{target_group}': Added {count} channels")

    # 3. ADD LIVE EVENTS (Pass-Through)
    print("\n--- Adding Live Events ---")
    live_sources = [URL_FANCODE, URL_SONY, URL_ZEE5]
    for url in live_sources:
        ch_list = harvest_all_channels([url])
        for ch in ch_list:
            final_lines.append(f'#EXTINF:-1 group-title="Live Events" tvg-logo="{ch["logo"]}", {ch["name"]}')
            final_lines.append(ch["url"]) # No fix needed usually for these, or add if needed

    # 4. ADD YOUTUBE
    print("\n--- Adding YouTube ---")
    yt_list = harvest_all_channels([URL_YOUTUBE])
    for ch in yt_list:
        final_lines.append(f'#EXTINF:-1 group-title="YouTube" tvg-logo="https://i.imgur.com/MbCpK4X.png", {ch["name"]}')
        final_lines.append(ch["url"])

    # 5. ADD TEMP
    print("\n--- Adding Temp ---")
    temp_list = parse_temp_file(FILE_TEMP)
    for ch in temp_list:
        final_lines.append(f'#EXTINF:-1 group-title="Temporary" tvg-logo="{ch["logo"]}", {ch["name"]}')
        final_lines.append(fix_url(ch["url"]))

    # 6. WRITE FILE
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print(f"\nSUCCESS: Playlist generated with {len(final_lines)//2} channels.")

if __name__ == "__main__":
    main()
