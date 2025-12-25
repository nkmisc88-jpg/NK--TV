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
backup_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# FORCE BACKUP LIST (General)
FORCE_BACKUP_KEYWORDS = [
    "star", "zee", "vijay", "asianet", "suvarna", "maa", "hotstar", "sony", "set", "sab",
    "nick", "cartoon", "pogo", "disney", "hungama", "sonic", "discovery", "nat geo", 
    "history", "tlc", "animal planet", "travelxp", "bbc earth", "movies now", "mnx", "romedy", "mn+", "pix",
    "&pictures", "sports", "ten"
]

browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

# ==========================================

def clean_key(name):
    """Simplifies string: 'Sports18 1 HD' -> 'sports181hd'"""
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

def load_local_map(ref_file):
    id_map = {}
    try:
        with open(ref_file, "r", encoding="utf-8") as f: content = f.read()
        pattern = r'tvg-id="(\d+)".*?tvg-name="([^"]+)"'
        matches = re.findall(pattern, content)
        for ch_id, ch_name in matches:
            id_map[clean_key(ch_name)] = ch_id
        print(f"✅ Local JioTV: Loaded {len(id_map)} channels.")
        return id_map
    except FileNotFoundError: 
        print("❌ Local source file not found!")
        return {}

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
                        key = clean_key(current_name)
                        data = [l for l in current_block if not l.startswith("#EXTINF")]
                        block_map[key] = data 
                    current_name = line.split(",")[-1].strip()
                    current_block = [line]
                else:
                    if current_block: current_block.append(line)
            if current_name and current_block:
                key = clean_key(current_name)
                data = [l for l in current_block if not l.startswith("#EXTINF")]
                block_map[key] = data
            print(f"✅ Backup Playlist: Loaded {len(block_map)} entries.")
    except: pass
    return block_map

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
        with open(youtube_file, "r", encoding="utf-8") as f: content = f.read()
        blocks = content.split('\n\n')
        for block in blocks:
            if not block.strip(): continue
            data = {}
            for row in block.splitlines():
                if ':' in row:
                    k, v = row.split(':', 1)
                    data[k.strip().lower()] = v.strip()
            title = data.get('title', 'Unknown'); logo = data.get('logo', ''); link = data.get('link', '')
            if not link: continue
            line = f'#EXTINF:-1 group-title="Youtube and live events" tvg-logo="{logo}",{title}'
            new_entries.extend(process_manual_link(line, link))
    except: pass
    return new_entries

def update_playlist():
    print("\n--- STARTING PROCESSING ---")
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
                name_lower = original_name.lower()
                clean_orig = clean_key(original_name)

                # =========================================
                # 1. HARD REMOVALS (Debug Prints Added)
                # =========================================
                
                # A. Zee Thirai
                if "zee thirai" in name_lower:
                    print(f"🗑️ DELETING: {original_name}")
                    continue
                
                # B. Star Sports 1 Kannada HD
                if "kannada" in name_lower and "star sports 1" in name_lower:
                    print(f"🗑️ DELETING: {original_name}")
                    continue
                
                # C. Generic Removals (Sony Ten / SD Sports)
                should_skip = False
                for rm in ["sony ten", "sonyten", "sony sports ten", "star sports 1", "star sports 2"]:
                    if rm in name_lower:
                        # Protect HD channels (except Kannada which is already handled above)
                        if ("star sports 1" in rm or "star sports 2" in rm) and "hd" in name_lower:
                            continue
                        should_skip = True; break
                
                if should_skip:
                    # print(f"🗑️ DELETING SD/Sony: {original_name}")
                    continue

                # =========================================
                # 2. RENAMING & SOURCE LOGIC
                # =========================================

                # CASE: Sports18 1 HD (formerly Star Sports 2 Hindi HD)
                if "star sports 2 hindi hd" in name_lower:
                    print(f"🔄 RENAMING: {original_name} -> Sports18 1 HD")
                    line = line.replace("Star Sports 2 Hindi HD", "Sports18 1 HD")
                    
                    # FORCE LOCAL SOURCE for Sports18 1 HD
                    target_key = clean_key("Sports18 1 HD")
                    if target_key in local_map:
                        final_lines.append(line)
                        final_lines.append(f"{base_url}/{local_map[target_key]}.m3u8")
                        stats["local"] += 1
                        print("   -> Found in LOCAL source.")
                    else:
                        print("   ⚠️ Not found in Local, trying backup...")
                        # Fallback to backup if local missing
                        if target_key in backup_map:
                            final_lines.append(line); final_lines.extend(backup_map[target_key])
                            stats["backup"] += 1
                    continue # Done with this channel

                # CASE: Star Sports 2 Tamil HD
                if "star sports 2 tamil hd" in name_lower:
                    print(f"🔍 PROCESSING: {original_name}")
                    target_key = clean_key("Star Sports 2 Tamil HD")
                    
                    # Try LOCAL first (as requested)
                    if target_key in local_map:
                        final_lines.append(line)
                        final_lines.append(f"{base_url}/{local_map[target_key]}.m3u8")
                        stats["local"] += 1
                        print("   -> Found in LOCAL source.")
                    
                    # Try BACKUP second
                    elif target_key in backup_map:
                        final_lines.append(line); final_lines.extend(backup_map[target_key])
                        stats["backup"] += 1
                        print("   -> Found in BACKUP source.")
                    
                    else:
                        print("   ❌ Missing in both sources.")
                        stats["missing"] += 1
                    continue # Done with this channel

                # =========================================
                # 3. STANDARD LOGIC (Everything Else)
                # =========================================
                
                if "http://placeholder" in url:
                    found_block = None
                    
                    # Should we check Backup First?
                    force_backup = False
                    for k in FORCE_BACKUP_KEYWORDS:
                        if k in name_lower: force_backup = True; break
                    
                    # Name Fixes for Backup Search
                    search_key = clean_orig
                    if "nat geo hd" in name_lower: search_key = clean_key("National Geographic HD")
                    if "zee tamil" in name_lower: search_key = clean_key("Zee Tamil HD")

                    # SEARCH LOGIC
                    if force_backup:
                        if search_key in backup_map:
                            found_block = backup_map[search_key]; stats["backup"] += 1
                        elif clean_orig in local_map:
                            found_block = [f"{base_url}/{local_map[clean_orig]}.m3u8"]; stats["local"] += 1
                    else:
                        if clean_orig in local_map:
                            found_block = [f"{base_url}/{local_map[clean_orig]}.m3u8"]; stats["local"] += 1
                        elif search_key in backup_map:
                            found_block = backup_map[search_key]; stats["backup"] += 1
                    
                    if found_block:
                        final_lines.append(line); final_lines.extend(found_block)
                    else:
                        print(f"⚠️ MISSING: {original_name}")
                        final_lines.append(line)
                        if clean_orig in local_map: final_lines.append(f"{base_url}/{local_map[clean_orig]}.m3u8")
                        else: final_lines.append(f"{base_url}/000.m3u8")
                        stats["missing"] += 1

                elif url and not url.startswith("#"):
                    processed = process_manual_link(line, url)
                    final_lines.extend(processed)

    except FileNotFoundError: print("❌ Template file not found!")

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
    print(f"\n🎉 DONE! Saved to {output_file}")
    print(f"📊 Stats: Local={stats['local']} | Backup={stats['backup']} | Missing={stats['missing']}")

if __name__ == "__main__":
    update_playlist()
