import requests
import re
import difflib

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"
reference_file = "jiotv_playlist.m3u.m3u8" # Your Local JioTV export
output_file = "playlist.m3u"

# SOURCES
local_base_url = "http://192.168.0.146:5350/live"
jstar_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# DELETE LIST (Channels to strictly REMOVE)
REMOVE_KEYWORDS = [
    "sony ten", "sonyten", "sony sports ten", 
    "star sports 1", "star sports 2" # SD versions
]

# FORCED MAPPING (Template -> JStar Backup)
# These specific HD channels will come from JStar
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

FORCE_BACKUP_GROUPS = ["Sports HD", "Infotainment HD"]
browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

# ==========================================

def clean_key(name):
    """Simplifies string for matching."""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def load_local_map(ref_file):
    """Loads ID map from local file."""
    id_map = {}
    try:
        with open(ref_file, "r", encoding="utf-8") as f:
            content = f.read()
        pattern = r'tvg-id="(\d+)".*?tvg-name="([^"]+)"'
        matches = re.findall(pattern, content)
        for ch_id, ch_name in matches:
            id_map[clean_key(ch_name)] = {"id": ch_id, "name": ch_name}
        print(f"✅ Local Server: Loaded {len(id_map)} channels.")
    except:
        print(f"❌ ERROR: Could not find {ref_file}")
    return id_map

def fetch_jstar(url):
    """Fetches JStar backup."""
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
                    if k not in map_data or "hd" in curr.lower():
                        map_data[k] = {"url": line, "name": curr}
                    curr = ""
            print(f"✅ JStar Backup: Loaded {len(map_data)} channels.")
    except:
        print("❌ Error fetching JStar.")
    return map_data

def smart_find_local(target_name, local_map):
    """Tries to find a channel in local map even if name is slightly different."""
    target_clean = clean_key(target_name)
    
    # 1. Exact Match
    if target_clean in local_map:
        return local_map[target_clean]['id']
    
    # 2. Fuzzy Contain Match (e.g. "Sun TV" found in "Sun TV HD")
    for k, v in local_map.items():
        if target_clean in k or k in target_clean:
            return v['id']
            
    return None

def update_playlist():
    local_map = load_local_map(reference_file)
    jstar_map = fetch_jstar(jstar_url)
    
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
            
            # 2. CHECK SOURCE PRIORITY
            is_backup_group = any(g in inf_line for g in FORCE_BACKUP_GROUPS)
            
            # A) Try Backup (JStar)
            if is_backup_group:
                target = BACKUP_MAPPING.get(ch_name_clean, ch_name_raw)
                k = clean_key(target)
                if k in jstar_map:
                    final_url = jstar_map[k]['url']
                # Fallback to Local if JStar fails
                elif smart_find_local(ch_name_raw, local_map):
                    tid = smart_find_local(ch_name_raw, local_map)
                    final_url = f"{local_base_url}/{tid}.m3u8"

            # B) Try Local (Primary)
            else:
                tid = smart_find_local(ch_name_raw, local_map)
                if tid:
                    final_url = f"{local_base_url}/{tid}.m3u8"
                # Fallback to JStar if Local fails
                elif ch_name_clean in jstar_map:
                    final_url = jstar_map[ch_name_clean]['url']
            
            # 3. FINAL DECISION
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
                # 4. LAST RESORT: DON'T DELETE! ADD ANYWAY!
                # We assume it might be in local with same ID as name or user will fix later
                # This ensures your count stays 151
                print(f"⚠️ Warning: No source found for {ch_name_raw} (Keeping entry)")
                final_lines.append(inf_line)
                # Guess URL: try using channel name as ID
                guess_id = ch_name_raw.replace(" ", "")
                final_lines.append(f"{local_base_url}/{guess_id}.m3u8")
                count += 1

        # 5. ADD FANCODE
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
        print(f"📊 Total Channels: ~{count} + Fancode")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_playlist()
