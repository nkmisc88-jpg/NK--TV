import requests
import re

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"
output_file = "playlist.m3u"

# SOURCE 1: JStar (Backup for Star/Zee/Sony)
jstar_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"

# SOURCE 2: Fancode (Updated Link)
# Trying a new source since the old one stopped working
fancode_url = "https://raw.githubusercontent.com/drm-live/fancode-live-events/main/fancode.m3u"

# 1. DELETE LIST: Strictly remove these
REMOVE_KEYWORDS = [
    "sony ten", "sonyten", "sony sports ten", # Remove ALL Sony Ten
    "star sports 1", "star sports 2" # Remove SD versions
]

# 2. EXACT MAPPING (Template Name -> Source Name from your Screenshots)
STRICT_MAPPING = {
    # --- STAR SPORTS MAIN (Fixing "1 HD" vs "HD1") ---
    "star sports 1 hd": "Star Sports HD1",
    "star sports 2 hd": "Star Sports HD2",
    "star sports 1 hindi hd": "Star Sports HD1 Hindi",
    
    # --- STAR SPORTS SELECT (Fixing "1 HD" vs "HD1") ---
    "star sports select 1 hd": "Star Sports Select HD1",
    "star sports select 2 hd": "Star Sports Select HD2",

    # --- REGIONAL (Direct Match based on your screenshots) ---
    "star sports 1 tamil hd": "Star Sports 1 Tamil HD",
    "star sports 2 tamil hd": "Star Sports 2 Tamil HD",
    "star sports 1 telugu hd": "Star Sports 1 Telugu HD",
    "star sports 2 telugu hd": "Star Sports 2 Telugu HD",
    "star sports 1 kannada hd": "Star Sports 1 Kannada HD",
    "star sports 2 kannada hd": "Star Sports 2 Kannada HD",

    # --- INFOTAINMENT & OTHERS ---
    "discovery hd world": "Discovery HD",
    "animal planet hd world": "Animal Planet HD",
    "tlc hd world": "TLC HD",
    "nat geo hd": "National Geographic HD",
    "zee tamil": "Zee Tamil HD"
}

browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

# ==========================================

def clean_key(name):
    """Standardizes name for comparison (remove spaces, lowercase)."""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def fetch_playlist(url):
    """Fetches a remote M3U and returns a dict {clean_name: url}."""
    playlist_data = {}
    try:
        print(f"🌍 Fetching {url}...")
        response = requests.get(url, headers={"User-Agent": browser_ua}, timeout=30)
        if response.status_code == 200:
            lines = response.text.splitlines()
            current_name = ""
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    current_name = line.split(",")[-1].strip()
                elif line.startswith("http") and current_name:
                    # Save by Clean Key for easier matching
                    k = clean_key(current_name)
                    # Priority: Prefer HD links if duplicates exist
                    if k not in playlist_data or ("hd" in current_name.lower() and "hd" not in playlist_data[k]['name'].lower()):
                        playlist_data[k] = {"url": line, "name": current_name, "raw": line}
                    current_name = ""
            print(f"✅ Loaded {len(playlist_data)} channels.")
        else:
            print(f"❌ Failed to load. Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    return playlist_data

def update_playlist():
    jstar_map = fetch_playlist(jstar_url)
    
    final_lines = ["#EXTM3U x-tvg-url=\"http://192.168.0.146:5350/epg.xml.gz\""]
    
    try:
        with open(template_file, "r", encoding="utf-8") as f:
            template_content = f.read()
        
        # Split by #EXTINF to process blocks
        entries = re.split(r'(?=#EXTINF)', template_content)
        
        for entry in entries:
            if not entry.strip() or not entry.startswith("#EXTINF"):
                continue
            
            lines = entry.strip().splitlines()
            inf_line = lines[0]
            stream_url = lines[1] if len(lines) > 1 else ""
            
            # Extract Name
            ch_name_raw = inf_line.split(",")[-1].strip()
            ch_name_lower = ch_name_raw.lower()

            # --- 1. REMOVAL LOGIC (Sony Ten / SD) ---
            # Checks if the name contains any "Sony Ten" variant
            should_remove = False
            for rm in REMOVE_KEYWORDS:
                if rm in ch_name_lower:
                    # Special check: Don't remove HD if we only wanted SD, 
                    # BUT user said "Sony Ten all channels can be removed", so we remove everything matching.
                    if "star sports" in rm and "hd" in ch_name_lower:
                        continue # Don't remove Star Sports HD when cleaning SD
                    should_remove = True
                    break
            
            if should_remove:
                continue

            # --- 2. MAPPING LOGIC ---
            # Check if we have a strict map for this channel
            target_name = STRICT_MAPPING.get(ch_name_lower, ch_name_lower)
            search_key = clean_key(target_name)
            
            # If current URL is a placeholder or broken, try JStar
            if "http://placeholder" in stream_url or "youtube" in stream_url:
                if search_key in jstar_map:
                    # Found in JStar!
                    final_lines.append(inf_line)
                    final_lines.append(jstar_map[search_key]['url'])
                else:
                    # Not found, keep original (or placeholder)
                    final_lines.append(inf_line)
                    final_lines.append(stream_url)
                    print(f"⚠️ Missing in JStar: {ch_name_raw} (Looked for: {target_name})")
            else:
                # Keep existing valid links
                final_lines.append(inf_line)
                final_lines.append(stream_url)

        # --- 3. ADD FANCODE AT THE END ---
        print("⚽ Adding Fancode...")
        try:
            fc_resp = requests.get(fancode_url, headers={"User-Agent": browser_ua}, timeout=30)
            if fc_resp.status_code == 200:
                fc_lines = fc_resp.text.splitlines()
                # Skip the #EXTM3U header from fancode file
                if fc_lines and "#EXTM3U" in fc_lines[0]:
                    fc_lines = fc_lines[1:]
                final_lines.append("\n" + "\n".join(fc_lines))
                print("✅ Fancode added successfully.")
            else:
                print("❌ Fancode link is down.")
        except:
            print("❌ Could not fetch Fancode.")

        # Write Output
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(final_lines))
        
        print(f"Playlist saved to: {output_file}")

    except FileNotFoundError:
        print("❌ Error: template.m3u file not found.")

if __name__ == "__main__":
    update_playlist()
