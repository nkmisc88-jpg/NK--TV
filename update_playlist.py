import requests
import re

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"
youtube_file = "youtube.txt"
reference_file = "jiotv_playlist.m3u.m3u8"
output_file = "playlist.m3u"

# BACKUP SOURCE (JStar)
backup_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"
base_url = "http://192.168.0.146:5350/live"

# 1. DELETE RULE: Remove any channel name containing these strings
DELETE_KEYWORDS = ["sony ten", "sonyten"]

# 2. FORCE BACKUP: Ensure these groups/channels always pull from JStar
FORCE_BACKUP_GROUPS = ["Sports HD", "Infotainment HD", "Hindi Movies HD"]

# 3. STRICT MAPPING: Fixes for specific channel issues
STRICT_MAPPING = {
    "zee tamil": "ZEE TAMIL HD",         # Fix: Prevent Zee News playing
    "nat geo hd": "National Geographic HD", # Fix: Ensure HD, not SD/Wild
    "dd sports hd": "DD Sports HD",      # Fix: Pull HD version
    "star sports 1 hd": "Star Sports 1 HD",
    "star sports 2 hd": "Star Sports 2 HD",
    "star sports select 1 hd": "Star Sports Select 1 HD",
    "star sports select 2 hd": "Star Sports Select 2 HD"
}

browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

# ==========================================

def fetch_backup_map(url):
    """Parses the jstar.m3u file into a dictionary."""
    block_map = {}
    try:
        print(f"🌍 Fetching JStar source...")
        response = requests.get(url, headers={"User-Agent": browser_ua}, timeout=30)
        if response.status_code == 200:
            lines = response.text.splitlines()
            current_info = ""
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    current_info = line
                elif line.startswith("http") and current_info:
                    name = current_info.split(",")[-1].strip()
                    # Store by clean name key
                    key = name.lower().replace(" ", "")
                    block_map[key] = {"info": current_info, "url": line, "raw_name": name}
                    current_info = ""
            print(f"✅ JStar Loaded: {len(block_map)} channels found.")
    except Exception as e:
        print(f"❌ Error fetching JStar: {e}")
    return block_map

def update_playlist():
    backup_map = fetch_backup_map(backup_url)
    final_lines = ["#EXTM3U x-tvg-url=\"http://192.168.0.146:5350/epg.xml.gz\""]
    
    try:
        with open(template_file, "r", encoding="utf-8") as f:
            template_content = f.read()
        
        # Split template by #EXTINF
        entries = re.split(r'(?=#EXTINF)', template_content)
        
        for entry in entries:
            if not entry.strip() or not entry.startswith("#EXTINF"):
                continue
            
            lines = entry.strip().splitlines()
            inf_line = lines[0]
            stream_url = lines[1] if len(lines) > 1 else ""
            
            # Extract channel name and group
            ch_name = inf_line.split(",")[-1].strip()
            ch_name_lower = ch_name.lower()
            group_match = re.search(r'group-title="([^"]+)"', inf_line)
            group_name = group_match.group(1) if group_match else ""

            # --- STEP 1: DELETE SONY TEN ---
            if any(k in ch_name_lower for k in DELETE_KEYWORDS):
                continue

            # --- STEP 2: HANDLE PLACEHOLDERS OR FORCED GROUPS ---
            if "http://placeholder" in stream_url or any(g in group_name for g in FORCE_BACKUP_GROUPS):
                
                # Check Strict Mapping first
                lookup_name = STRICT_MAPPING.get(ch_name_lower, ch_name_lower).replace(" ", "")
                
                # Search in JStar Map
                if lookup_name in backup_map:
                    match = backup_map[lookup_name]
                    final_lines.append(inf_line)
                    final_lines.append(match['url'])
                else:
                    # Fallback: Fuzzy search in JStar
                    found = False
                    for key, val in backup_map.items():
                        if lookup_name in key:
                            final_lines.append(inf_line)
                            final_lines.append(val['url'])
                            found = True
                            break
                    
                    if not found:
                        # If totally missing from JStar, keep placeholder or skip
                        print(f"⚠️ Not found in JStar: {ch_name}")
            else:
                # Keep local/youtube links as they are
                final_lines.append(inf_line)
                final_lines.append(stream_url)

        # Write final file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(final_lines))
        print(f"🎉 Success! {output_file} updated.")

    except FileNotFoundError:
        print("❌ template.m3u not found.")

if __name__ == "__main__":
    update_playlist()
