import requests
import datetime
import os
import re

# ==========================================
# 1. SETUP SOURCES
# ==========================================
OUTPUT_FILE = "pocket_playlist.m3u"
YOUTUBE_FILE = "youtube.txt"

# Main Source
MAIN_SOURCE_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html"

# Live Event Sources
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SONY_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
ZEE_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# Headers to mimic a browser
UA_HEADER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def fetch_content(url):
    print(f"   Downloading: {url}...")
    try:
        r = requests.get(url, headers={"User-Agent": UA_HEADER}, timeout=15)
        if r.status_code == 200:
            return r.text.splitlines()
    except Exception as e:
        print(f"   ❌ Error fetching {url}: {e}")
    return []

def extract_live_events(url):
    """Fetches a playlist and forces all channels into the 'Live Events' group."""
    raw_lines = fetch_content(url)
    cleaned_lines = []
    for line in raw_lines:
        line = line.strip()
        if not line or line.startswith("#EXTM3U"): continue
        
        if line.startswith("#EXTINF"):
            # Remove existing group info and force 'Live Events'
            line = re.sub(r'group-title="[^"]*"', '', line)
            line = re.sub(r'(#EXTINF:[-0-9]+)', r'\1 group-title="Live Events"', line)
            cleaned_lines.append(line)
        elif not line.startswith("#"):
            cleaned_lines.append(line)
    return cleaned_lines

def parse_youtube_txt():
    """Reads youtube.txt and converts it to M3U format."""
    print("   Reading youtube.txt...")
    lines = []
    if not os.path.exists(YOUTUBE_FILE): return []
    
    try:
        with open(YOUTUBE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            content = f.readlines()
        
        # Default values
        title = "Unknown Channel"
        logo = "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Globe_icon.svg/1200px-Globe_icon.svg.png"
        
        for line in content:
            line = line.strip()
            if not line: continue
            
            # Simple Key:Value parser
            if line.lower().startswith("title:"):
                title = line.split(":", 1)[1].strip()
            elif line.lower().startswith("link:"):
                url = line.split("link:", 1)[1].strip() # Fix: Handle "Link:" case insensitive
                # Add entry
                lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{logo}",{title}')
                # Add UA if missing
                if "|" not in url and "http" in url: url += f"|User-Agent={UA_HEADER}"
                lines.append(url)
                # Reset defaults
                title = "Unknown Channel"
            elif line.lower().startswith("http"): # Handle raw links if any
                 # Fallback if someone pasted just a link
                 pass 
    except Exception as e:
        print(f"   ❌ Error reading youtube.txt: {e}")
    return lines

# ==========================================
# 3. MAIN SCRIPT
# ==========================================
def main():
    print("🚀 Starting Fresh Playlist Generation...")
    
    # 1. Start the Playlist
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines = ["#EXTM3U", f"# Updated on: {ist_now.strftime('%Y-%m-%d %H:%M:%S IST')}"]

    # 2. Process Main Source (Arunjunan20)
    source_lines = fetch_content(MAIN_SOURCE_URL)
    
    # Define Tamil HD Channels for grouping fix (Case Insensitive)
    TAMIL_HD_LIST = ["sun tv hd", "ktv hd", "sun music hd", "star vijay hd", "vijay super hd", "zee tamil hd", "zee thirai hd", "colors tamil hd", "jaya tv hd"]

    print("   Processing main channels...")
    i = 0
    while i < len(source_lines):
        line = source_lines[i].strip()
        
        if line.startswith("#EXTINF"):
            # Get the URL line immediately
            if i + 1 < len(source_lines):
                url_line = source_lines[i+1].strip()
            else:
                break # End of file

            # --- LOGIC START ---
            # 1. Check Name
            name_match = line.split(",")[-1].strip()
            name_lower = name_match.lower()
            
            # 2. Fix Tamil HD Grouping
            # (If name contains any of our Tamil HD list, force group to 'Tamil HD')
            is_tamil_hd = False
            for thd in TAMIL_HD_LIST:
                if thd in name_lower:
                    is_tamil_hd = True
                    break
            
            if is_tamil_hd:
                # Force replace group-title logic
                if 'group-title="' in line:
                    line = re.sub(r'group-title="[^"]*"', 'group-title="Tamil HD"', line)
                else:
                    line = line.replace("#EXTINF:-1", '#EXTINF:-1 group-title="Tamil HD"')

            # 3. Add to List (We keep EVERYTHING else as is)
            final_lines.append(line)
            final_lines.append(url_line)
            
            i += 2 # Move past metadata & url
        else:
            i += 1 # Skip random text

    # 3. Append Extra Content
    print("   Appending Live Events...")
    final_lines.extend(extract_live_events(FANCODE_URL))
    final_lines.extend(extract_live_events(SONY_LIVE_URL))
    final_lines.extend(extract_live_events(ZEE_LIVE_URL))
    
    print("   Appending Temporary Channels...")
    final_lines.extend(parse_youtube_txt())

    # 4. Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print(f"✅ DONE! Playlist saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
