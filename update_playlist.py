import requests
import re

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"
youtube_file = "youtube.txt"
reference_file = "jiotv_playlist.m3u.m3u8"
output_file = "playlist.m3u"

# SOURCES
base_url = "http://192.168.0.146:5350/live" 
# Backup Source (FakeAll/Jstar)
backup_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# 1. REMOVAL LIST (Strictly delete these)
REMOVE_KEYWORDS = [
    "sony ten", "sonyten", "sony sports ten", 
    "star sports 1", "star sports 2" # SD versions
]

# 2. CHANNELS TO FORCE FROM BACKUP
FORCE_BACKUP_KEYWORDS = [
    "star", "zee", "vijay", "asianet", "suvarna", "maa", "hotstar", "sony", "set", "sab",
    "nick", "cartoon", "pogo", "disney", "hungama", "sonic", "discovery", "nat geo", 
    "history", "tlc", "animal planet", "travelxp", "bbc earth", "movies now", "mnx", "romedy", "mn+", "pix",
    "&pictures", "sports", "ten"
]

# 3. NAME OVERRIDES (Left: YOUR Template Name | Right: BACKUP Source Name)
# Updated based on your screenshots to fix "Missing" channels
NAME_OVERRIDES = {
    # --- STAR SPORTS FIXES (HD1 format) ---
    "star sports 1 hd": "Star Sports HD1",
    "star sports 2 hd": "Star Sports HD2",
    "star sports 1 hindi hd": "Star Sports HD1 Hindi",
    
    # --- REBRANDING FIXES (JioStar 2025) ---
    "star sports 2 hindi hd": "Sports18 1 HD",      # Fixes playback
    "star sports 2 tamil hd": "Star Sports 2 Tamil HD", 
    "star sports 2 telugu hd": "Star Sports 2 Telugu HD",
    "star sports 2 kannada hd": "Star Sports 2 Kannada HD",
    
    # --- STAR SPORTS SELECT ---
    "star sports select 1 hd": "Star Sports Select HD1",
    "star sports select 2 hd": "Star Sports Select HD2",
    
    # --- INFOTAINMENT & OTHERS ---
    "nat geo hd": "National Geographic HD",
    "nat geo wild hd": "Nat Geo Wild HD",
    "discovery hd world": "Discovery HD",
    "history tv18 hd": "History TV18 HD",
    "cartoon network hd+ english": "Cartoon Network HD+",
    "nick hd+": "Nick HD+",
    "star movies hd": "Star Movies HD",
    "sony pix hd": "Sony Pix HD",
    "zee tamil": "Zee Tamil HD"
}

# Browser UA
browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
# ==========================================

def clean_name_key(name):
    """Normalizes names."""
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

def get_significant_words(name):
    """Extracts core words for fuzzy matching."""
    name = name.lower()
    name = name.replace("sports18", "sports 18") 
    name = re.sub(r'\b(hd|sd|tv|channel|network|india|world|english|tamil|hindi|telugu|kannada|movies|cinema)\b', '', name)
    words = re.findall(r'[a-z0-9]+', name)
    return set(words)

def get_forbidden_words(target_name):
    """Context-aware blacklist."""
    t = target_name.lower()
    forbidden = []
    
    if "nat" in t and "wild" not in t: forbidden.append("wild")
    if "discovery" in t:
        if "kids" not in t: forbidden.append("kids")
        if "science" not in t: forbidden.append("science")
        if "turbo" not in t: forbidden.append("turbo")
    
    if "sports" in t or "ten" in t:
        for n in ["1", "2", "3", "4", "5"]:
            if n in t:
                forbidden.extend([x for x in ["1", "2", "3", "4", "5"] if x != n])
                break     
    return forbidden

def fuzzy_match_logic(target_name, map_keys):
    target_words = get_significant_words(target_name)
    if not target_words: return None
    bad_words = get_forbidden_words(target_name)
    
    for key in map_keys:
        key_lower = key.lower()
        key_norm = key_lower.replace("sports18", "sports 18")
        if any(bad in key_lower for bad in bad_words): continue
        key_words = set(re.findall(r'[a-z0-9]+', key_norm))
        
        if "national" in key_words and "geographic" in key_words:
            key_words.add("nat"); key_words.add("geo")
        if "&pictures" in key_lower:
            key_words.add("and"); key_words.add("pictures")

        if target_words.issubset(key_words):
            return key
    return None

def find_best_backup_link(original_name, backup_map):
    clean_orig = clean_name_key(original_name)
    
    # 1. Exact Match
    if clean_orig in backup_map: return backup_map[clean_orig]
        
    # 2. Mapped Match (Overrides)
    clean_mapped = None
    for k, v in NAME_OVERRIDES.items():
        if clean_name_key(k) == clean_orig:
            clean_mapped = clean_name_key(v)
            break
            
    if clean_mapped:
        if clean_mapped in backup_map: return backup_map[clean_mapped]
        # Fuzzy match the mapped name
        fuzzy_mapped = fuzzy_match_logic(NAME_OVERRIDES.get(original_name.lower(), clean_mapped), backup_map.keys())
        if fuzzy_mapped: return backup_map[fuzzy_mapped]
    
    # 3. Fuzzy Match (Original Name)
    fuzzy_key = fuzzy_match_logic(original_name, backup_map.keys())
    if fuzzy_key: return backup_map[fuzzy_key]
        
    return None

def load_local_map(ref_file):
    id_map = {}
    try:
        with open(ref_file, "r", encoding="utf-8") as f:
            content = f.read()
        pattern = r'tvg-id="(\d+)".*?tvg-name="([^"]+)"'
        matches = re.findall(pattern, content)
        for ch_id, ch_name in matches:
            key = clean_name_key(ch_name)
            id_map[key] = ch_id
        print(f"✅ Local JioTV: Found {len(id_map)} channels.")
        return id_map
    except FileNotFoundError:
        return {}

def fetch_backup_map(url):
    block_map = {}
    try:
        print("🌍 Fetching FakeAll Source...")
        response = requests.get(url, headers={"User-Agent": browser_ua}, timeout=20)
        if response.status_code == 200:
            lines = response.text.splitlines()
            current_block = []
            current_name = ""
            for line in lines:
                line = line.strip()
                if not line: continue
                if line.startswith("#EXTINF"):
                    if current_name and current_block:
                        key = clean_name_key(current_name)
                        data = [l for l in current_block if not l.startswith("#EXTINF")]
                        if data: block_map[key] = data
                        block_map[current_name] = data 
                    current_name = line.split(",")[-1].strip()
                    current_block = [line]
                else:
                    if current_block: current_block.append(line)
            if current_name and current_block:
                key = clean_name_key(current_name)
                data = [l for l in current_block if not l.startswith("#EXTINF")]
                if data: block_map[key] = data
                block_map[current_name] = data
            print(f"✅ Backup Playlist: Parsed {len(block_map)} entries.")
    except: pass
    return block_map

def should_force_backup(name):
    norm = name.lower()
    for k in FORCE_BACKUP_KEYWORDS:
        if k in norm: return True
    return False

def process_manual_link(line, link):
    if 'group-title="YouTube"' in line:
        line = line.replace('group-title="YouTube"', 'group-title="Youtube and live events"')
    if "youtube.com" in link or "youtu.be" in link:
        link = link.split('|')[0]
        vid_id = re.search(r'(?:v=|\/live\/|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', link)
        if vid_id: link = f"https://www.youtube.com/watch?v={vid_id.group(1)}&.m3u8|User-Agent={browser_ua}"
        else: link = f"{link}|User-Agent={browser_ua}"
    return [line, link]

def parse_youtube_txt():
    new_entries = []
    try:
        with open(youtube_file, "r", encoding="utf-8") as f:
            content = f.read()
        blocks = content.split('\n\n')
        for block in blocks:
            if not block.strip(): continue
            data = {}
            for row in block.splitlines():
                if ':' in row:
                    k, v = row.split(':', 1)
                    data[k.strip().lower()] = v.strip()
            title = data.get('title', 'Unknown')
            logo = data.get('logo', '')
            link = data.get('link', '')
            vpn_req = data.get('vpn required', 'no').lower()
            vpn_country = data.get('vpn country', '')
            if not link: continue
            if vpn_req == 'yes':
                title = f"{title} [VPN: {vpn_country}]" if vpn_country else f"{title} [VPN Required]"
            line = f'#EXTINF:-1 group-title="Youtube and live events" tvg-logo="{logo}",{title}'
            new_entries.extend(process_manual_link(line, link))
    except: pass
    return new_entries

def update_playlist():
    print("--- STARTING PLAYLIST UPDATE ---")
    local_map = load_local_map(reference_file)
    backup_map = fetch_backup_map(backup_url)
    final_lines = ["#EXTM3U x-tvg-url=\"http://192.168.0.146:5350/epg.xml.gz\""]
    stats = {"local": 0, "backup": 0, "missing": 0}

    try:
        with open(template_file, "r", encoding="utf-8") as f: lines = f.readlines()
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("#EXTINF"):
                url = ""
                if i + 1 < len(lines): url = lines[i+1].strip()

                original_name = line.split(",")[-1].strip()
                ch_name_clean = clean_name_key(original_name)

                # --- 1. REMOVAL LOGIC ---
                should_remove = False
                for rm in REMOVE_KEYWORDS:
                    if rm in ch_name_clean:
                        # Protect HD channels from SD removal keywords
                        if "starsports" in rm and "hd" in ch_name_clean: continue
                        should_remove = True
                        break
                if should_remove: continue
                # -------------------------

                if "http://placeholder" in url:
                    found_block = None
                    
                    # Force Backup check
                    if should_force_backup(original_name):
                        found_block = find_best_backup_link(original_name, backup_map)
                        if found_block:
                            stats["backup"] += 1
                        elif clean_name_key(original_name) in local_map:
                            # Fallback to local if backup missing
                            found_block = [f"{base_url}/{local_map[clean_name_key(original_name)]}.m3u8"]
                            stats["local"] += 1
                    
                    # Standard check
                    else:
                        if clean_name_key(original_name) in local_map:
                            found_block = [f"{base_url}/{local_map[clean_name_key(original_name)]}.m3u8"]
                            stats["local"] += 1
                        else:
                            found_block = find_best_backup_link(original_name, backup_map)
                            if found_block: stats["backup"] += 1

                    if found_block:
                        final_lines.append(line)
                        final_lines.extend(found_block)
                    else:
                        # FALLBACK: Keep entry even if missing (Points to Local Guess)
                        # This fixes the "Channel Count" dropping issue
                        print(f"⚠️ MISSING: {original_name} (Keeping entry)")
                        final_lines.append(line)
                        # Guess ID from name
                        guess_id = clean_name_key(original_name)
                        if guess_id in local_map:
                             final_lines.append(f"{base_url}/{local_map[guess_id]}.m3u8")
                        else:
                             # Last resort: just leave placeholder or guess URL
                             final_lines.append(f"{base_url}/000.m3u8")
                        stats["missing"] += 1

                elif url and not url.startswith("#"):
                    processed = process_manual_link(line, url)
                    final_lines.extend(processed)
    except FileNotFoundError: pass

    final_lines.extend(parse_youtube_txt())
    try:
        r = requests.get(fancode_url)
        if r.status_code == 200:
            flines = r.text.splitlines()
            if flines and flines[0].startswith("#EXTM3U"): flines = flines[1:]
            final_lines.append("\n" + "\n".join(flines))
            print("✅ Fancode merged.")
    except: pass

    with open(output_file, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print(f"\n🎉 SUMMARY: Local: {stats['local']} | Backup: {stats['backup']} | Missing: {stats['missing']}")

if __name__ == "__main__":
    update_playlist()
