import requests
import re
import datetime

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"
youtube_file = "youtube.txt"
reference_file = "jiotv_playlist.m3u.m3u8"
output_file = "playlist.m3u"

# SOURCES
base_url = "http://192.168.0.146:5350/live" 
backup_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# 1. REMOVE LIST
REMOVE_KEYWORDS = [
    "sony ten", "sonyten", "sony sports ten", 
    "star sports 1", "star sports 2",
    "zee thirai",                
    "star sports 1 kannada hd"   
]

# 2. FORCE BACKUP LIST
FORCE_BACKUP_KEYWORDS = [
    "star", "zee", "vijay", "asianet", "suvarna", "maa", "hotstar", "sony", "set", "sab",
    "nick", "cartoon", "pogo", "disney", "hungama", "sonic", "discovery", "nat geo", 
    "history", "tlc", "animal planet", "travelxp", "bbc earth", "movies now", "mnx", "romedy", "mn+", "pix",
    "&pictures", "sports", "ten"
]

# 3. MAPPING (Name Overrides)
NAME_OVERRIDES = {
    "star sports 2 hindi hd": "Sports18 1 HD",
    "star sports 2 tamil hd": "Star Sports 2 Tamil HD",
    "zee tamil": "Zee Tamil HD",
    "nat geo hd": "National Geographic HD",
    "star sports 1 hd": "Star Sports HD1",
    "star sports 2 hd": "Star Sports HD2",
    "star sports 1 hindi hd": "Star Sports HD1 Hindi",
    "sony sports ten 1 hd": "sony ten 1",
    "sony sports ten 2 hd": "sony ten 2",
    "sony sports ten 3 hd": "sony ten 3",
    "sony sports ten 4 hd": "sony ten 4",
    "sony sports ten 5 hd": "sony ten 5",
    "nat geo wild hd": "nat geo wild",
    "discovery hd world": "discovery channel",
    "history tv18 hd": "history",
    "cartoon network hd+ english": "cartoon network",
    "nick hd+": "nick",
    "star movies hd": "star movies",
    "sony pix hd": "sony pix",
}

# Standard Browser User Agent
browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ==========================================
# CORE FUNCTIONS
# ==========================================

def clean_name_key(name):
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

def get_significant_words(name):
    name = name.lower().replace("sports18", "sports 18") 
    name = re.sub(r'\b(hd|sd|tv|channel|network|india|world|english|tamil|hindi|telugu|kannada|movies|cinema)\b', '', name)
    words = re.findall(r'[a-z0-9]+', name)
    return set(words)

def fuzzy_match_logic(target_name, map_keys):
    target_words = get_significant_words(target_name)
    if not target_words: return None
    for key in map_keys:
        key_lower = key.lower().replace("sports18", "sports 18")
        key_words = set(re.findall(r'[a-z0-9]+', key_lower))
        if target_words.issubset(key_words): return key
    return None

def find_best_backup_link(original_name, backup_map):
    if "star sports 2 tamil hd" in original_name.lower():
        for k in backup_map:
            if "star sports 2 tamil hd" in k.lower(): return backup_map[k]

    clean_orig = clean_name_key(original_name)
    if clean_orig in backup_map: return backup_map[clean_orig]
    
    clean_mapped = None
    for k, v in NAME_OVERRIDES.items():
        if clean_name_key(k) == clean_orig:
            clean_mapped = clean_name_key(v); break
    if clean_mapped:
        if clean_mapped in backup_map: return backup_map[clean_mapped]
        fuzzy_mapped = fuzzy_match_logic(NAME_OVERRIDES.get(original_name.lower(), clean_mapped), backup_map.keys())
        if fuzzy_mapped: return backup_map[fuzzy_mapped]
    
    fuzzy_key = fuzzy_match_logic(original_name, backup_map.keys())
    if fuzzy_key: return backup_map[fuzzy_key]
    return None

def load_local_map(ref_file):
    id_map = {}
    try:
        with open(ref_file, "r", encoding="utf-8") as f: content = f.read()
        pattern = r'tvg-id="(\d+)".*?tvg-name="([^"]+)"'
        matches = re.findall(pattern, content)
        for ch_id, ch_name in matches:
            id_map[clean_name_key(ch_name)] = ch_id
        print(f"✅ Local JioTV: Found {len(id_map)} channels.")
        return id_map
    except FileNotFoundError: return {}

def fetch_backup_map(url):
    block_map = {}
    try:
        print("🌍 Fetching Backup Source...")
        response = requests.get(url, headers={"User-Agent": browser_ua}, timeout=20)
        if response.status_code == 200:
            lines = response.text.splitlines()
            current_block = []; current_name = ""
            for line in lines:
                line = line.strip()
                if not line: continue
                if line.startswith("#EXTINF"):
                    if current_name and current_block:
                        key = clean_name_key(current_name)
                        data = [l for l in current_block if not l.startswith("#EXTINF")]
                        block_map[key] = data; block_map[current_name] = data 
                    current_name = line.split(",")[-1].strip()
                    current_block = [line]
                else:
                    if current_block: current_block.append(line)
            if current_name and current_block:
                key = clean_name_key(current_name)
                data = [l for l in current_block if not l.startswith("#EXTINF")]
                block_map[key] = data; block_map[current_name] = data
            print(f"✅ Backup Playlist: Parsed {len(block_map)} entries.")
    except: pass
    return block_map

def should_force_backup(name):
    norm = name.lower()
    if "star sports 2 hindi hd" in norm: return False
    for k in FORCE_BACKUP_KEYWORDS:
        if k in norm: return True
    return False

# ==========================================
# NEW YOUTUBE & MEDIA PROCESSOR
# ==========================================

def get_direct_youtube_link(youtube_url):
    """
    Attempts to bypass YouTube consent page and extract HLS Manifest.
    """
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': browser_ua,
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.youtube.com/',
        })
        # Important: Cookie to bypass 'Before you continue'
        session.cookies.set('CONSENT', 'YES+cb', domain='.youtube.com')

        resp = session.get(youtube_url, timeout=10)
        
        # Look for the m3u8 manifest in the page source
        if "hlsManifestUrl" in resp.text:
            url = re.search(r'"hlsManifestUrl":"(.*?)"', resp.text).group(1)
            return url
            
        return None
    except:
        return None

def parse_youtube_txt():
    """
    Reads youtube.txt and converts it to M3U format.
    Handles YouTube extraction + standard media links.
    """
    new_entries = []
    try:
        with open(youtube_file, "r", encoding="utf-8") as f: content = f.read()
        
        # Split by double newlines to separate blocks
        blocks = content.split('\n\n')
        
        for block in blocks:
            if not block.strip(): continue
            
            # Parse key-value pairs
            data = {}
            for row in block.splitlines():
                if ':' in row:
                    key, val = row.split(':', 1)
                    data[key.strip().lower()] = val.strip()
            
            # Extract fields
            title = data.get('title', 'Unknown Channel')
            logo = data.get('logo', '')
            link = data.get('link', '')
            vpn_req = data.get('vpn required', 'no').lower()
            
            if not link: continue

            # Add VPN tag to title if needed
            if vpn_req == "yes":
                title = f"{title} [VPN]"

            final_link = link
            
            # Logic: Is this YouTube or Direct Media?
            if "youtube.com" in link or "youtu.be" in link:
                print(f"   ...Processing YouTube: {title}")
                extracted = get_direct_youtube_link(link)
                if extracted:
                    final_link = f"{extracted}|User-Agent={browser_ua}"
                else:
                    # Fallback: Use original link (Player might handle it)
                    print(f"      -> Live stream not found. Keeping original.")
                    final_link = link
            else:
                # It's an m3u8 / mp4 / other link
                final_link = link

            # Construct M3U Entry
            entry = f'#EXTINF:-1 group-title="Youtube and live events" tvg-logo="{logo}",{title}\n{final_link}'
            new_entries.append(entry)
            
    except Exception as e:
        print(f"Error parsing youtube.txt: {e}")
        
    return new_entries

# ==========================================
# MAIN UPDATE LOGIC
# ==========================================

def update_playlist():
    print("--- STARTING UPDATE ---")
    local_map = load_local_map(reference_file)
    backup_map = fetch_backup_map(backup_url)
    
    # 1. GENERATE TIMESTAMP (Forces GitHub Update)
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_lines = [
        "#EXTM3U x-tvg-url=\"http://192.168.0.146:5350/epg.xml.gz\"",
        f"# Updated on: {current_time}"
    ]
    
    stats = {"local": 0, "backup": 0, "missing": 0}

    try:
        with open(template_file, "r", encoding="utf-8") as f: lines = f.readlines()
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("#EXTINF"):
                url = ""
                if i + 1 < len(lines): url = lines[i+1].strip()
                
                original_name = line.split(",")[-1].strip()
                ch_name_lower = original_name.lower()

                # --- REMOVALS ---
                if "zee thirai" in ch_name_lower: continue
                if "kannada" in ch_name_lower and "star sports 1" in ch_name_lower: continue

                should_remove = False
                for rm in REMOVE_KEYWORDS:
                    if rm in ch_name_lower:
                        if "star sports 1" in rm or "star sports 2" in rm:
                            if "hd" in ch_name_lower and "kannada" not in ch_name_lower: 
                                continue 
                        should_remove = True; break
                if should_remove: continue

                # RENAME VISUAL
                if "star sports 2 hindi hd" in ch_name_lower:
                    line = line.replace("Star Sports 2 Hindi HD", "Sports18 1 HD")

                if "http://placeholder" in url:
                    clean_local_key = clean_name_key(original_name)
                    found_block = None
                    
                    if should_force_backup(original_name):
                        found_block = find_best_backup_link(original_name, backup_map)
                        if found_block: stats["backup"] += 1
                        elif clean_name_key(NAME_OVERRIDES.get(ch_name_lower, "")) in local_map:
                             found_block = [f"{base_url}/{local_map[clean_name_key(NAME_OVERRIDES[ch_name_lower])]}.m3u8"]
                             stats["local"] += 1
                        elif clean_local_key in local_map:
                            found_block = [f"{base_url}/{local_map[clean_local_key]}.m3u8"]
                            stats["local"] += 1
                    else:
                        mapped_key = clean_name_key(NAME_OVERRIDES.get(ch_name_lower, ""))
                        if clean_local_key in local_map:
                            found_block = [f"{base_url}/{local_map[clean_local_key]}.m3u8"]
                            stats["local"] += 1
                        elif mapped_key and mapped_key in local_map:
                            found_block = [f"{base_url}/{local_map[mapped_key]}.m3u8"]
                            stats["local"] += 1
                        else:
                            found_block = find_best_backup_link(original_name, backup_map)
                            if found_block: stats["backup"] += 1

                    if found_block:
                        final_lines.append(line); final_lines.extend(found_block)
                    else:
                        print(f"⚠️ MISSING: {original_name}")
                        final_lines.append(line)
                        if clean_local_key in local_map: final_lines.append(f"{base_url}/{local_map[clean_local_key]}.m3u8")
                        else: final_lines.append(f"{base_url}/000.m3u8")
                        stats["missing"] += 1

                elif url and not url.startswith("#"):
                    # Pass through manual links found in template
                    final_lines.append(line)
                    final_lines.append(url)
    except FileNotFoundError: pass

    # --- PROCESS YOUTUBE.TXT ---
    print("🎥 Processing youtube.txt...")
    youtube_entries = parse_youtube_txt()
    if youtube_entries:
        final_lines.append("") # Spacer
        final_lines.extend(youtube_entries)
    
    # --- FANCODE ---
    try:
        r = requests.get(fancode_url)
        if r.status_code == 200:
            flines = r.text.splitlines()
            if flines and flines[0].startswith("#EXTM3U"): flines = flines[1:]
            final_lines.append("\n" + "\n".join(flines))
            print("✅ Fancode merged.")
    except: pass

    # SAVE
    with open(output_file, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print(f"\n🎉 DONE: Local: {stats['local']} | Backup: {stats['backup']} | Missing: {stats['missing']}")

if __name__ == "__main__":
    update_playlist()
