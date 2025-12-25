import requests
import re

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"
# This file MUST exist in the same folder (your local JioTV Go export)
reference_file = "jiotv_playlist.m3u.m3u8" 
output_file = "playlist.m3u"

# SOURCES
# 1. Local Server (Primary for most channels)
local_base_url = "http://192.168.0.146:5350/live"

# 2. Remote Source (For Sports HD only)
jstar_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"

# 3. Fancode (Jitendra)
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# DELETE LIST: Remove these completely
REMOVE_KEYWORDS = [
    "sony ten", "sonyten", "sony sports ten", 
    "star sports 1", "star sports 2" # SD versions
]

# STRICT MAPPING (Template Name -> JStar Name)
# Only needed for channels we force from JStar
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
    "animal planet hd world": "Animal Planet HD",
    "tlc hd world": "TLC HD",
    "nat geo hd": "National Geographic HD",
}

# GROUPS TO FORCE FROM BACKUP (JStar)
FORCE_BACKUP_GROUPS = ["Sports HD", "Infotainment HD"]

browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

# ==========================================

def clean_key(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())

def load_local_map(ref_file):
    """Loads IDs from your local JioTV Go file."""
    id_map = {}
    try:
        with open(ref_file, "r", encoding="utf-8") as f:
            content = f.read()
        # Regex to find tvg-id="123" and tvg-name="Channel Name"
        pattern = r'tvg-id="(\d+)".*?tvg-name="([^"]+)"'
        matches = re.findall(pattern, content)
        for ch_id, ch_name in matches:
            k = clean_key(ch_name)
            id_map[k] = ch_id
        print(f"✅ Local JioTV: Loaded {len(id_map)} channels.")
    except FileNotFoundError:
        print(f"❌ ERROR: Local file '{ref_file}' not found. Make sure it is in the folder!")
    return id_map

def fetch_jstar(url):
    """Fetches remote backup map."""
    map_data = {}
    try:
        resp = requests.get(url, headers={"User-Agent": browser_ua}, timeout=30)
        if resp.status_code == 200:
            lines = resp.text.splitlines()
            curr_name = ""
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    curr_name = line.split(",")[-1].strip()
                elif line.startswith("http") and curr_name:
                    k = clean_key(curr_name)
                    # Priority logic
                    if k not in map_data or ("hd" in curr_name.lower() and "hd" not in map_data[k]['name'].lower()):
                        map_data[k] = {"url": line, "name": curr_name}
                    curr_name = ""
            print(f"✅ JStar Backup: Loaded {len(map_data)} channels.")
    except:
        print("❌ Error fetching JStar.")
    return map_data

def update_playlist():
    # 1. Load Sources
    local_map = load_local_map(reference_file)
    jstar_map = fetch_jstar(jstar_url)
    
    final_lines = ["#EXTM3U x-tvg-url=\"http://192.168.0.146:5350/epg.xml.gz\""]
    
    try:
        with open(template_file, "r", encoding="utf-8") as f:
            template_content = f.read()
            
        entries = re.split(r'(?=#EXTINF)', template_content)
        
        for entry in entries:
            if not entry.strip() or not entry.startswith("#EXTINF"): continue
            
            lines = entry.strip().splitlines()
            inf_line = lines[0]
            stream_url = lines[1] if len(lines) > 1 else ""
            
            # Extract info
            ch_name_raw = inf_line.split(",")[-1].strip()
            ch_name_lower = ch_name_raw.lower()
            group_match = re.search(r'group-title="([^"]+)"', inf_line)
            group_name = group_match.group(1) if group_match else ""

            # --- REMOVE LOGIC ---
            should_remove = False
            for rm in REMOVE_KEYWORDS:
                if rm in ch_name_lower:
                    if "star sports" in rm and "hd" in ch_name_lower: continue 
                    should_remove = True
                    break
            if should_remove: continue

            # --- DECIDE SOURCE ---
            final_url = ""
            
            # Condition A: Force Backup (Sports HD / Infotainment HD)
            if any(g in group_name for g in FORCE_BACKUP_GROUPS):
                # Try Mapping First
                target = BACKUP_MAPPING.get(ch_name_lower, ch_name_lower)
                k = clean_key(target)
                
                if k in jstar_map:
                    final_url = jstar_map[k]['url']
                # Fallback to local if missing in backup
                elif clean_key(ch_name_raw) in local_map:
                    tid = local_map[clean_key(ch_name_raw)]
                    final_url = f"{local_base_url}/{tid}.m3u8"
            
            # Condition B: Standard Channel (Sun TV, News, etc.) -> Use Local
            else:
                k_local = clean_key(ch_name_raw)
                if k_local in local_map:
                    tid = local_map[k_local]
                    final_url = f"{local_base_url}/{tid}.m3u8"
                # Fallback to Backup if missing locally
                elif k_local in jstar_map:
                    final_url = jstar_map[k_local]['url']

            # --- WRITE RESULT ---
            if final_url:
                final_lines.append(inf_line)
                final_lines.append(final_url)
            elif "http" in stream_url and "placeholder" not in stream_url:
                # Keep existing valid hardcoded links (YouTube etc)
                final_lines.append(inf_line)
                final_lines.append(stream_url)
            else:
                print(f"⚠️ Missing everywhere: {ch_name_raw}")

        # --- ADD FANCODE ---
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
        print(f"Playlist saved: {output_file}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_playlist()
