import requests
import re

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"
reference_file = "jiotv_playlist.m3u.m3u8" # Your working local playlist
output_file = "playlist.m3u"

# SOURCES
jstar_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# DELETE LIST
REMOVE_KEYWORDS = [
    "sony ten", "sonyten", "sony sports ten", 
    "star sports 1", "star sports 2" # SD versions
]

# FORCED MAPPING (Template Name -> JStar Name)
# These specific HD channels will be pulled from JStar
BACKUP_MAPPING = {
    "star sports 1 hd": "Star Sports HD1",
    "star sports 2 hd": "Star Sports HD2",
    "star sports 1 hindi hd": "Star Sports HD1 Hindi",
    "star sports 2 hindi hd": "Sports18 1 HD",
    "star sports 2 tamil hd": "Star Sports 2 Tamil HD",
    "star sports 2 telugu hd": "Star Sports 2 Telugu HD",
    "star sports 2 kannada hd": "Star Sports 2 Kannada HD",
    "star sports select 1 hd": "Star Sports Select HD1",
    "star sports select 2 hd": "Star Sports Select HD2",
    "discovery hd world": "Discovery HD",
    "nat geo hd": "National Geographic HD",
    "zee tamil": "Zee Tamil HD"
}

# Groups to check in JStar
FORCE_BACKUP_GROUPS = ["Sports HD", "Infotainment HD"]

browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

# ==========================================

def clean_key(name):
    """Standardizes string for matching (removes spaces, case, special chars)."""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def load_local_map(ref_file):
    """Reads the reference file and maps Name -> FULL URL."""
    url_map = {}
    try:
        with open(ref_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        current_name = ""
        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF"):
                # Extract name
                current_name = line.split(",")[-1].strip()
            elif line.startswith("http") and current_name:
                # Store the EXACT working URL keyed by cleaned name
                k = clean_key(current_name)
                url_map[k] = line
                current_name = ""
        print(f"✅ Local Reference: Loaded {len(url_map)} working links.")
    except FileNotFoundError:
        print(f"❌ ERROR: Could not find {ref_file}. Make sure it's in the same folder!")
    return url_map

def fetch_jstar(url):
    """Fetches JStar backup and maps Name -> URL."""
    map_data = {}
    try:
        resp = requests.get(url, headers={"User-Agent": browser_ua}, timeout=30)
        if resp.status_code == 200:
            lines = resp.text.splitlines()
            curr = ""
            for line in lines:
                if line.startswith("#EXTINF"):
                    curr = line.split(",")[-1].strip()
                elif line.startswith("http") and curr:
                    k = clean_key(curr)
                    # Priority: Prefer HD
                    if k not in map_data or "hd" in curr.lower():
                        map_data[k] = line
                    curr = ""
            print(f"✅ JStar Backup: Loaded {len(map_data)} channels.")
    except:
        print("❌ Error fetching JStar.")
    return map_data

def update_playlist():
    # 1. Load Sources
    local_urls = load_local_map(reference_file)
    jstar_urls = fetch_jstar(jstar_url)
    
    final_lines = ["#EXTM3U x-tvg-url=\"http://192.168.0.146:5350/epg.xml.gz\""]
    count = 0
    
    try:
        with open(template_file, "r", encoding="utf-8") as f:
            template_content = f.read()
        
        entries = re.split(r'(?=#EXTINF)', template_content)
        
        for entry in entries:
            if not entry.strip() or not entry.startswith("#EXTINF"): continue
            
            lines = entry.strip().splitlines()
            inf_line = lines[0]
            stream_url = lines[1] if len(lines) > 1 else ""
            
            ch_name_raw = inf_line.split(",")[-1].strip()
            ch_name_clean = clean_key(ch_name_raw)
            
            # 1. CHECK REMOVALS
            should_remove = False
            for rm in REMOVE_KEYWORDS:
                if rm in ch_name_clean:
                    if "starsports" in rm and "hd" in ch_name_clean: continue
                    should_remove = True
                    break
            if should_remove: continue

            final_url = ""
            
            # 2. DECIDE SOURCE
            is_backup_group = any(g in inf_line for g in FORCE_BACKUP_GROUPS)
            
            # CASE A: FORCE FROM JSTAR (Sports HD)
            if is_backup_group:
                # Try specific mapping first
                target = BACKUP_MAPPING.get(ch_name_clean, ch_name_raw)
                k = clean_key(target)
                if k in jstar_urls:
                    final_url = jstar_urls[k]
                # Fallback to Local URL if JStar fails
                elif ch_name_clean in local_urls:
                    final_url = local_urls[ch_name_clean]

            # CASE B: EVERYTHING ELSE (Sun TV, News, etc.) -> USE LOCAL
            else:
                if ch_name_clean in local_urls:
                    final_url = local_urls[ch_name_clean]
                # Fallback to JStar if missing locally
                elif ch_name_clean in jstar_urls:
                    final_url = jstar_urls[ch_name_clean]
            
            # 3. WRITE RESULT
            if final_url:
                final_lines.append(inf_line)
                final_lines.append(final_url)
                count += 1
            elif "http" in stream_url and "placeholder" not in stream_url:
                # Keep original hardcoded links (YouTube etc)
                final_lines.append(inf_line)
                final_lines.append(stream_url)
                count += 1
            else:
                # If truly missing, keep it but warn. 
                # (Ideally this shouldn't happen if Reference File is complete)
                print(f"⚠️ Link Missing: {ch_name_raw}")
                final_lines.append(inf_line)
                final_lines.append(stream_url) # Keep placeholder so user sees it in list

        # 4. ADD FANCODE
        try:
            fc_resp = requests.get(fancode_url, headers={"User-Agent": browser_ua}, timeout=30)
            if fc_resp.status_code == 200:
                fc = fc_resp.text.splitlines()
                if fc and "#EXTM3U" in fc[0]: fc = fc[1:]
                final_lines.append("\n" + "\n".join(fc))
                print("✅ Fancode added.")
        except: pass

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(final_lines))
        print(f"\n🎉 Playlist Generated: {output_file}")
        print(f"📊 Total Channels: {count} + Fancode")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_playlist()
