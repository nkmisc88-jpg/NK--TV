import requests
import re
import datetime

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================
# SOURCES (Tiger/Joker First for best Zee links)
URL_TIGER     = "https://raw.githubusercontent.com/tiger629/m3u/refs/heads/main/joker.m3u"
URL_ARUNJUNAN = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html"
URL_FORCEGT   = "https://raw.githubusercontent.com/ForceGT/Discord-IPTV/master/playlist.m3u"

# LIVE & YOUTUBE SOURCES
URL_YOUTUBE   = "https://raw.githubusercontent.com/nkmisc88-jpg/my-youtube-live-playlist/refs/heads/main/playlist.m3u"
URL_FANCODE   = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
URL_SONY      = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
URL_ZEE5      = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

FILE_TEMP     = "temp.txt"
OUTPUT_FILE   = "nktv.m3u"

# ==============================================================================
# 2. KEYWORDS TO SEARCH
# ==============================================================================
# We only grab channels containing these words. Add more if needed.
SEARCH_KEYWORDS = [
    # Tamil HD
    "Sun TV HD", "Star Vijay HD", "Zee Tamil HD", "Colors Tamil HD", "KTV HD", 
    "Sun Music HD", "Vijay Super HD", "Zee Thirai HD", "Jaya TV HD",
    # Sports
    "Star Sports", "Sony Sports", "Eurosport", "Willow", "Astro Cricket", "Fox Cricket", "TNT Sports",
    # Tamil News
    "Polimer News", "Puthiya Thalaimurai", "Sun News", "Thanthi TV", "News18 Tamil",
    # Infotainment
    "Discovery", "Animal Planet", "Nat Geo", "Sony BBC", "History TV18", "Zee Zest", "TLC"
]

# ==============================================================================
# 3. HELPER FUNCTIONS
# ==============================================================================

def get_ist_time():
    utc_now = datetime.datetime.utcnow()
    ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
    return ist_now.strftime("%Y-%m-%d %H:%M:%S IST")

def clean_html_line(line):
    return re.sub(r'<[^>]+>', '', line).strip()

def fetch_and_filter(url):
    print(f"Scanning: {url} ... ", end="")
    entries = []
    try:
        resp = requests.get(url, timeout=30)
        lines = resp.text.splitlines()
        
        current_info = ""
        for line in lines:
            line = clean_html_line(line)
            if not line: continue
            
            if line.startswith("#EXTINF"):
                current_info = line
            elif line.startswith("http") and current_info:
                # CHECK: Does this channel match our keywords?
                # We normalize to lowercase for search
                channel_name_lower = current_info.lower()
                
                if any(keyword.lower() in channel_name_lower for keyword in SEARCH_KEYWORDS):
                    # === PLAYBACK FIX: Force User-Agent ===
                    final_url = line.strip()
                    if "|" not in final_url and "googlevideo" not in final_url:
                        final_url = f"{final_url}|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    
                    entries.append(f"{current_info}\n{final_url}")
                
                current_info = "" # Reset
        
        print(f"Found {len(entries)} matching channels")
        return entries
    except Exception as e:
        print(f"Error: {e}")
        return []

def fetch_pass_through(url, forced_group=None):
    """Fetches everything from a source, optionally overriding group name"""
    print(f"Fetching: {url} ... ", end="")
    entries = []
    try:
        resp = requests.get(url, timeout=30)
        lines = resp.text.splitlines()
        
        current_info = ""
        for line in lines:
            line = clean_html_line(line)
            if not line: continue
            
            if line.startswith("#EXTINF"):
                if forced_group:
                    # Replace existing group-title with forced one
                    if 'group-title="' in line:
                        line = re.sub(r'group-title="[^"]*"', f'group-title="{forced_group}"', line)
                    else:
                        line = line.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{forced_group}"')
                current_info = line
            elif line.startswith("http") and current_info:
                entries.append(f"{current_info}\n{line}")
                current_info = ""
        
        print(f"Added {len(entries)} items")
        return entries
    except Exception as e:
        print(f"Error: {e}")
        return []

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
                    if "|" not in link:
                         link = f"{link}|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    entries.append(f'#EXTINF:-1 group-title="Temporary" tvg-logo="{logo}", {name}\n{link}')
    except:
        pass
    return entries

# ==============================================================================
# 4. MAIN LOGIC
# ==============================================================================

def main():
    final_lines = [
        '#EXTM3U',
        f'#EXTINF:-1 group-title="System", Playlist Updated: {get_ist_time()}',
        'http://localhost/timestamp'
    ]
    
    # 1. Main TV Channels (Filtered by Keyword)
    print("\n--- Searching for TV Channels ---")
    # Tiger first, then others
    tv_entries = []
    tv_entries.extend(fetch_and_filter(URL_TIGER))
    tv_entries.extend(fetch_and_filter(URL_ARUNJUNAN))
    tv_entries.extend(fetch_and_filter(URL_FORCEGT))
    
    # Add to final list
    final_lines.extend(tv_entries)
    
    # 2. Live Events (Copy All)
    print("\n--- Fetching Live Events ---")
    final_lines.extend(fetch_pass_through(URL_FANCODE, "Live Events"))
    final_lines.extend(fetch_pass_through(URL_SONY, "Live Events"))
    final_lines.extend(fetch_pass_through(URL_ZEE5, "Live Events"))
    
    # 3. YouTube (Copy All)
    print("\n--- Fetching YouTube ---")
    final_lines.extend(fetch_pass_through(URL_YOUTUBE, "YouTube"))
    
    # 4. Temporary
    print("\n--- Fetching Temp ---")
    final_lines.extend(parse_temp_file(FILE_TEMP))
    
    # Write File
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
        
    print(f"\nSUCCESS: Total {len(final_lines)} entries generated.")

if __name__ == "__main__":
    main()