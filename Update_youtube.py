import requests
import re
import datetime

# ==========================================
# CONFIGURATION
# ==========================================
input_file = "youtube.txt"
output_file = "youtube_playlist.m3u"  # This will contain ONLY Youtube & Live Events

# Browser Headers (Critical for bypassing YouTube "Sign In" page)
browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ==========================================
# YOUTUBE SCRAPER ENGINE
# ==========================================

def get_direct_youtube_link(youtube_url):
    """
    Connects to YouTube mimicking a real Chrome browser.
    Extracts the direct 'hlsManifestUrl' (.m3u8) to avoid redirects.
    """
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': browser_ua,
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.youtube.com/',
        })
        # The 'CONSENT' cookie is the secret key to bypass the redirect page
        session.cookies.set('CONSENT', 'YES+cb', domain='.youtube.com')

        print(f"   ...Fetching: {youtube_url}")
        resp = session.get(youtube_url, timeout=15)
        text = resp.text

        # Method 1: Search for JSON HLS Manifest (Standard Live Streams)
        match = re.search(r'"hlsManifestUrl":"(.*?)"', text)
        if match:
            return match.group(1)
        
        # Method 2: Search for raw m3u8 links (Alternative format)
        match_raw = re.search(r'(https:\/\/[^\s]+\.m3u8)', text)
        if match_raw:
            return match_raw.group(1)

        print(f"      ❌ Failed to extract stream. (Channel might be offline)")
        return None
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return None

# ==========================================
# MAIN PARSER
# ==========================================

def generate_youtube_playlist():
    print("--- STARTING YOUTUBE PLAYLIST GENERATION ---")
    
    # 1. Initialize Playlist with Header & Timestamp (FORCES UPDATE)
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    playlist_lines = [
        "#EXTM3U",
        f"# Updated on: {current_time}"
    ]
    
    count = 0

    try:
        with open(input_file, "r", encoding="utf-8") as f: content = f.read()
        
        # Split file by empty lines into blocks
        blocks = content.split('\n\n')
        
        for block in blocks:
            if not block.strip(): continue
            
            # Parse Key:Value pairs
            data = {}
            for row in block.splitlines():
                if ':' in row:
                    key, val = row.split(':', 1)
                    data[key.strip().lower()] = val.strip()
            
            # Extract Data
            title = data.get('title', 'Unknown Event')
            logo = data.get('logo', '')
            link = data.get('link', '')
            vpn_req = data.get('vpn required', 'no').lower()
            
            if not link: continue

            # 2. Handle VPN Tag
            if "yes" in vpn_req:
                title = f"{title} [VPN]"

            # 3. Process Link
            final_link = link
            
            # Case A: It is a YouTube Link -> SCRAPE IT
            if "youtube.com" in link or "youtu.be" in link:
                # Remove any existing pipe params if present
                clean_link = link.split('|')[0].strip()
                
                direct_url = get_direct_youtube_link(clean_link)
                
                if direct_url:
                    # Success: Use the extracted direct link
                    final_link = f"{direct_url}|User-Agent={browser_ua}"
                else:
                    # Failure: Fallback to original (better than deleting it)
                    final_link = link

            # Case B: It is already a direct link (.m3u8 / .mp4) -> KEEP IT
            else:
                pass # Use 'link' as is

            # 4. Write Entry with Group Name
            entry = f'#EXTINF:-1 group-title="Youtube and live events" tvg-logo="{logo}",{title}\n{final_link}'
            playlist_lines.append(entry)
            count += 1
            
    except FileNotFoundError:
        print(f"❌ Error: {input_file} not found.")

    # 5. Save File
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(playlist_lines))
        
    print(f"\n🎉 DONE: Generated {count} entries in {output_file}")

if __name__ == "__main__":
    generate_youtube_playlist()
