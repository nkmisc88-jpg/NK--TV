import requests
import re
import datetime
import os

# ==========================================
# CONFIGURATION
# ==========================================
input_file = "youtube.txt"
playlist_file = "playlist.m3u"  # TARGET THE MAIN FILE

# Browser Headers (Critical for bypassing YouTube "Sign In" page)
browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ==========================================
# YOUTUBE SCRAPER ENGINE
# ==========================================

def get_direct_youtube_link(youtube_url):
    """
    Connects to YouTube mimicking a real Chrome browser.
    Extracts the direct 'hlsManifestUrl' (.m3u8).
    """
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': browser_ua,
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.youtube.com/',
        })
        session.cookies.set('CONSENT', 'YES+cb', domain='.youtube.com')

        print(f"   ...Fetching: {youtube_url}")
        resp = session.get(youtube_url, timeout=15)
        text = resp.text

        match = re.search(r'"hlsManifestUrl":"(.*?)"', text)
        if match:
            return match.group(1)
        
        match_raw = re.search(r'(https:\/\/[^\s]+\.m3u8)', text)
        if match_raw:
            return match_raw.group(1)

        print(f"      ❌ Failed to extract stream. (Channel might be offline)")
        return None
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return None

# ==========================================
# MAIN LOGIC
# ==========================================

def update_youtube_in_playlist():
    print("--- STARTING YOUTUBE UPDATE IN MAIN PLAYLIST ---")
    
    # 1. READ EXISTING PLAYLIST
    existing_lines = []
    if os.path.exists(playlist_file):
        with open(playlist_file, "r", encoding="utf-8") as f:
            existing_lines = f.read().splitlines()
    else:
        print(f"⚠️ {playlist_file} not found. Creating new.")
        existing_lines = ["#EXTM3U"]

    # 2. FILTER OUT OLD YOUTUBE ENTRIES
    # We keep everything that is NOT 'Youtube and live events'
    clean_lines = []
    skip_next = False
    
    for i, line in enumerate(existing_lines):
        if skip_next:
            skip_next = False
            continue
            
        # Update the timestamp if found
        if line.startswith("# Updated on:"):
            continue # We will add a fresh one later
            
        if 'group-title="Youtube and live events"' in line:
            # Found a YouTube entry header, skip this line AND the next line (the URL)
            skip_next = True
            continue
        
        clean_lines.append(line)

    # 3. GENERATE NEW YOUTUBE ENTRIES
    new_youtube_entries = []
    
    try:
        with open(input_file, "r", encoding="utf-8") as f: content = f.read()
        blocks = content.split('\n\n')
        
        for block in blocks:
            if not block.strip(): continue
            
            data = {}
            for row in block.splitlines():
                if ':' in row:
                    key, val = row.split(':', 1)
                    data[key.strip().lower()] = val.strip()
            
            title = data.get('title', 'Unknown Event')
            logo = data.get('logo', '')
            link = data.get('link', '')
            vpn_req = data.get('vpn required', 'no').lower()
            
            if not link: continue

            if "yes" in vpn_req:
                title = f"{title} [VPN]"

            final_link = link
            
            # Scrape if it's YouTube
            if "youtube.com" in link or "youtu.be" in link:
                clean_link = link.split('|')[0].strip()
                direct_url = get_direct_youtube_link(clean_link)
                if direct_url:
                    final_link = f"{direct_url}|User-Agent={browser_ua}"
                else:
                    final_link = link # Fallback

            entry = f'#EXTINF:-1 group-title="Youtube and live events" tvg-logo="{logo}",{title}\n{final_link}'
            new_youtube_entries.append(entry)
            
    except FileNotFoundError:
        print(f"❌ Error: {input_file} not found.")

    # 4. MERGE & SAVE
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Insert Timestamp after #EXTM3U
    if clean_lines and clean_lines[0].startswith("#EXTM3U"):
        clean_lines.insert(1, f"# Updated on: {current_time}")
    else:
        clean_lines.insert(0, "#EXTM3U")
        clean_lines.insert(1, f"# Updated on: {current_time}")

    # Combine: [Existing Cleaned] + [Spacer] + [New YouTube]
    final_content = "\n".join(clean_lines)
    if new_youtube_entries:
        final_content += "\n\n" + "\n".join(new_youtube_entries)

    with open(playlist_file, "w", encoding="utf-8") as f:
        f.write(final_content)
        
    print(f"\n🎉 DONE: Updated {playlist_file} with {len(new_youtube_entries)} YouTube entries.")

if __name__ == "__main__":
    update_youtube_in_playlist()
