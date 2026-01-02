import requests
import re
import datetime
import os

# ==========================================
# CONFIGURATION
# ==========================================
OUTPUT_FILE = "pocket_playlist.m3u"
YOUTUBE_FILE = "youtube.txt"

# SOURCES
POCKET_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/refs/heads/main/index.html"
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SONY_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
ZEE_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# MASTER LIST (Reverted to "Zee Tamil HD" to force HD selection)
MASTER_CHANNELS = [
    ("Sports HD", "Star Sports 1 HD"), ("Sports HD", "Star Sports 2 HD"),
    ("Sports HD", "Star Sports 1 Hindi HD"), ("Sports HD", "Star Sports Select 1 HD"),
    ("Sports HD", "Star Sports Select 2 HD"), ("Sports HD", "Sony Sports Ten 1 HD"),
    ("Sports HD", "Sony Sports Ten 2 HD"), ("Sports HD", "Sony Sports Ten 3 HD"),
    ("Sports HD", "Sony Sports Ten 4 HD"), ("Sports HD", "Sony Sports Ten 5 HD"),
    ("Sports HD", "Sports18 1 HD"), ("Sports HD", "Eurosport HD"),
    ("Sports HD", "Astro Cricket"), ("Sports HD", "Willow Cricket"),
    ("Sports HD", "Sky Sports Cricket"),
    ("Tamil HD", "Sun TV HD"), ("Tamil HD", "KTV HD"),
    ("Tamil HD", "Star Vijay HD"), ("Tamil HD", "Zee Tamil HD"),
    ("Tamil HD", "Colors Tamil HD"), ("Tamil HD", "Jaya TV HD"),
    ("Tamil HD", "Zee Thirai HD"), ("Tamil HD", "Vijay Takkar"),
    ("Tamil HD", "Astro Vaanavil"), ("Tamil HD", "Astro Vinmeen HD"),
    ("Tamil HD", "Astro Thangathirai"), ("Tamil HD", "Astro Vellithirai"),
    ("Tamil HD", "Rasi Palan"), ("Tamil HD", "Rasi Movies"),
    ("Infotainment", "Discovery HD"), ("Infotainment", "Animal Planet HD"),
    ("Infotainment", "Nat Geo HD"), ("Infotainment", "Nat Geo Wild HD"),
    ("Infotainment", "Sony BBC Earth HD"), ("Infotainment", "History TV18 HD"),
    ("Infotainment", "TLC HD"), ("Infotainment", "TravelXP HD"),
    ("Movies", "Star Movies HD"), ("Movies", "Sony Pix HD"),
    ("Movies", "Movies Now HD"), ("Movies", "MN+ HD"),
    ("Movies", "MNX HD"), ("Movies", "Star Gold HD"),
    ("Movies", "Sony Max HD"), ("Movies", "Zee Cinema HD"),
    ("Movies", "&Pictures HD"),
    ("Entertainment", "Star Plus HD"), ("Entertainment", "Sony SET HD"),
    ("Entertainment", "Sony SAB HD"), ("Entertainment", "Zee TV HD"),
    ("Entertainment", "Colors HD"), ("Entertainment", "Star Bharat HD")
]

# ==========================================
# LOGIC
# ==========================================

def simplified_name(name):
    if not name: return ""
    name = re.sub(r'[\(\[\{].*?[\)\]\}]', '', name.lower())
    return re.sub(r'[^a-z0-9]', '', name)

def get_source_blocks():
    print("📥 Downloading Source Playlist...")
    blocks = []
    try:
        r = requests.get(POCKET_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if r.status_code == 200:
            lines = r.text.splitlines()
            current_block = []
            
            for line in lines:
                line = line.strip()
                if not line: continue
                
                if line.startswith("#KODIPROP") or line.startswith("#EXTVLCOPT") or line.startswith("#EXTINF"):
                    current_block.append(line)
                elif not line.startswith("#"):
                    current_block.append(line)
                    
                    # BLOCK COMPLETE
                    name_line = next((l for l in current_block if l.startswith("#EXTINF")), "")
                    if name_line:
                        raw_name = name_line.split(",")[-1].strip()
                        simple = simplified_name(raw_name)
                        
                        grp_match = re.search(r'group-title="([^"]*)"', name_line)
                        grp = grp_match.group(1).lower() if grp_match else ""
                        
                        # CHECK FOR KEYS
                        has_keys = any(l.startswith("#KODIPROP") or l.startswith("#EXTVLCOPT") for l in current_block)

                        blocks.append({
                            'simple': simple,
                            'name': raw_name,
                            'group': grp,
                            'lines': current_block,
                            'has_keys': has_keys
                        })
                    current_block = []
    except Exception as e:
        print(f"   ❌ Failed to load source: {e}")
    return blocks

def main():
    source_blocks = get_source_blocks()
    
    final_lines = ["#EXTM3U"]
    final_lines.append("http://0.0.0.0")

    added_ids = set()

    # 1. MASTER LIST (Priority with Smart Selection)
    print("\n1️⃣  Processing Master List...")
    for target_group, target_name in MASTER_CHANNELS:
        target_simple = simplified_name(target_name)
        
        # FIND ALL POTENTIAL MATCHES
        candidates = []
        for b in source_blocks:
            # Exact or Fuzzy Match
            if b['simple'] == target_simple or target_simple in b['simple']:
                candidates.append(b)
        
        # SMART SELECTION: Pick the best candidate
        best_match = None
        if candidates:
            # 1. Prefer candidate with License Keys (DRM) - Usually the working HD stream
            for c in candidates:
                if c['has_keys']:
                    best_match = c
                    break
            
            # 2. If no keys found, fallback to the first match
            if not best_match:
                best_match = candidates[0]

        if best_match:
            # Modify Group Title
            new_lines = []
            for l in best_match['lines']:
                if l.startswith("#EXTINF"):
                    l = re.sub(r'group-title="[^"]*"', f'group-title="{target_group}"', l)
                new_lines.append(l)
            
            final_lines.extend(new_lines)
            added_ids.add(best_match['simple'])
        else:
            print(f"   ⚠️ Channel Not Found: {target_name}")

    # 2. ADD ALL REMAINING CHANNELS
    print("\n2️⃣  Adding All Remaining Channels...")
    SPORTS_KEYS = ["sport", "cricket", "f1", "racing", "football", "ten", "sony", "astro"]
    TAMIL_KEYS = ["tamil", "sun", "vijay", "zee", "kalaignar", "polimer", "news18 tamil", "thanthi", "puthiya", "jaya"]
    
    count = 0
    for b in source_blocks:
        if b['simple'] in added_ids: continue
        
        name = b['name'].lower()
        grp = b['group']
        
        final_group = "General Extras"
        if any(x in name for x in SPORTS_KEYS) or "sport" in grp: final_group = "Sports Extra"
        elif any(x in name for x in TAMIL_KEYS) or "tamil" in grp: final_group = "Tamil Extra"
        
        # Modify Group
        new_lines = []
        for l in b['lines']:
            if l.startswith("#EXTINF"):
                if 'group-title="' in l:
                    l = re.sub(r'group-title="[^"]*"', f'group-title="{final_group}"', l)
                else:
                    l = l.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{final_group}"')
            new_lines.append(l)
            
        final_lines.extend(new_lines)
        added_ids.add(b['simple'])
        count += 1
        
    print(f"   ✅ Added {count} extra channels.")

    # 3. LIVE & TEMP
    print("\n3️⃣  Adding Live/Temp...")
    def add_ext(url, g):
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            for l in r.text.splitlines():
                if l.startswith("#EXTINF"):
                    l = re.sub(r'group-title="[^"]*"', '', l)
                    l = re.sub(r'(#EXTINF:[-0-9]+)', f'\\1 group-title="{g}"', l)
                final_lines.append(l)
        except: pass

    add_ext(FANCODE_URL, "Live Events")
    add_ext(SONY_LIVE_URL, "Live Events")
    add_ext(ZEE_LIVE_URL, "Live Events")

    if os.path.exists(YOUTUBE_FILE):
        with open(YOUTUBE_FILE, "r") as f:
            for l in f:
                if "title" in l.lower(): final_lines.append(f'#EXTINF:-1 group-title="Temporary" tvg-logo="",{l.split(":",1)[1].strip()}')
                elif l.startswith("http"): final_lines.append(l.strip())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print(f"\n✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
