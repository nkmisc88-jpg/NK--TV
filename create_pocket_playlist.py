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

# HEADERS
# 1. Jio/Zee/Sony Channels (Mobile App Agent)
UA_JIO = "plaYtv/7.0.8 (Linux;Android 9) ExoPlayerLib/2.11.7"
# 2. Astro/General Channels (Browser Agent - Fixes Astro)
UA_BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# MASTER LIST (Priority Channels)
MASTER_CHANNELS = [
    # --- SPORTS HD ---
    ("Sports HD", "Star Sports 1 HD"), ("Sports HD", "Star Sports 2 HD"),
    ("Sports HD", "Star Sports 1 Hindi HD"), ("Sports HD", "Star Sports Select 1 HD"),
    ("Sports HD", "Star Sports Select 2 HD"), ("Sports HD", "Sony Sports Ten 1 HD"),
    ("Sports HD", "Sony Sports Ten 2 HD"), ("Sports HD", "Sony Sports Ten 3 HD"),
    ("Sports HD", "Sony Sports Ten 4 HD"), ("Sports HD", "Sony Sports Ten 5 HD"),
    ("Sports HD", "Sports18 1 HD"), ("Sports HD", "Eurosport HD"),
    ("Sports HD", "Astro Cricket"), ("Sports HD", "Willow Cricket"),
    ("Sports HD", "Sky Sports Cricket"),

    # --- TAMIL HD ---
    ("Tamil HD", "Sun TV HD"), ("Tamil HD", "KTV HD"),
    ("Tamil HD", "Star Vijay HD"), ("Tamil HD", "Zee Tamil HD"),
    ("Tamil HD", "Colors Tamil HD"), ("Tamil HD", "Jaya TV HD"),
    ("Tamil HD", "Zee Thirai HD"), ("Tamil HD", "Vijay Takkar"),
    ("Tamil HD", "Astro Vaanavil"), ("Tamil HD", "Astro Vinmeen HD"),
    ("Tamil HD", "Astro Thangathirai"), ("Tamil HD", "Astro Vellithirai"),

    # --- INFOTAINMENT HD ---
    ("Infotainment HD", "Discovery HD"), ("Infotainment HD", "Animal Planet HD"),
    ("Infotainment HD", "Nat Geo HD"), ("Infotainment HD", "Nat Geo Wild HD"),
    ("Infotainment HD", "Sony BBC Earth HD"), ("Infotainment HD", "History TV18 HD"),
    ("Infotainment HD", "TLC HD"), ("Infotainment HD", "TravelXP HD"),

    # --- ENGLISH MOVIES HD ---
    ("English Movies HD", "Star Movies HD"), ("English Movies HD", "Sony Pix HD"),
    ("English Movies HD", "Movies Now HD"), ("English Movies HD", "MN+ HD"),
    ("English Movies HD", "MNX HD"), 

    # --- HINDI MOVIES HD ---
    ("Hindi Movies HD", "Star Gold HD"), ("Hindi Movies HD", "Sony Max HD"),
    ("Hindi Movies HD", "Zee Cinema HD"), ("Hindi Movies HD", "&Pictures HD"),

    # --- TAMIL NEWS ---
    ("Tamil News", "Sun News"), ("Tamil News", "Polimer News"),
    ("Tamil News", "Puthiya Thalaimurai"), ("Tamil News", "Thanthi TV"),
    ("Tamil News", "Kalaignar Seithigal"), ("Tamil News", "News18 Tamil Nadu"),

    # --- ENGLISH AND HINDI NEWS ---
    ("English and Hindi News", "Times Now"), ("English and Hindi News", "NDTV 24x7"),
    ("English and Hindi News", "India Today"), ("English and Hindi News", "CNN News18"),
    ("English and Hindi News", "Republic TV"), ("English and Hindi News", "Aaj Tak"),

    # --- OTHERS (Entertainment/Regional) ---
    ("Others", "Star Plus HD"), ("Others", "Sony SET HD"),
    ("Others", "Sony SAB HD"), ("Others", "Zee TV HD"),
    ("Others", "Colors HD"), ("Others", "Star Bharat HD"),
    ("Others", "Asianet HD"), ("Others", "Surya TV HD"),
    ("Others", "Star Maa HD"), ("Others", "Zee Telugu HD"),
    ("Others", "Colors Kannada HD"), ("Others", "Zee Kannada HD"),
    
    # --- KIDS ---
    ("Others", "Nick"), ("Others", "Sonic"), ("Others", "Hungama"),
    ("Others", "Disney Channel"), ("Others", "Cartoon Network"),
    ("Others", "Pogo"), ("Others", "Sony Yay"), ("Others", "Discovery Kids")
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

def determine_group(name, src_group):
    """Categorizes unknown channels."""
    name = name.lower()
    src_group = src_group.lower()
    
    if "tamil" in name or "tamil" in src_group:
        if "news" in name: return "Tamil News"
        if "hd" in name: return "Tamil HD"
        return "Tamil SD"

    if "sport" in name or "cricket" in name or "sport" in src_group:
        if "hd" in name: return "Sports HD"
        return "Sports SD"

    if "news" in name or "news" in src_group: return "English and Hindi News"

    info_keys = ["discovery", "nat geo", "animal planet", "history", "tlc", "travelxp", "bbc earth"]
    if any(k in name for k in info_keys) or "documentary" in src_group:
        if "hd" in name: return "Infotainment HD"
        return "Infotainment SD"

    if "movie" in name or "cinema" in name or "film" in name or "pix" in name or "mn" in name or "gold" in name:
        if "hd" in name:
            if any(x in name for x in ["star", "zee", "set", "color"]): return "Hindi Movies HD"
            return "English Movies HD"

    return "Others"

def main():
    source_blocks = get_source_blocks()
    
    final_lines = ["#EXTM3U"]
    final_lines.append("http://0.0.0.0")

    added_ids = set() # Stores 'suntvhd', 'ktvhd'
    
    # -------------------------------------------
    # 1. MASTER LIST (Priority)
    # -------------------------------------------
    print("\n1️⃣  Processing Master List...")
    for target_group, target_name in MASTER_CHANNELS:
        target_simple = simplified_name(target_name)
        
        candidates = [b for b in source_blocks if b['simple'] == target_simple or target_simple in b['simple']]
        
        # Pick best match (prefer keys)
        best_match = None
        if candidates:
            for c in candidates:
                if c['has_keys']: best_match = c; break
            if not best_match: best_match = candidates[0]

        if best_match:
            # FIX PLAYBACK: Inject User-Agent
            new_lines = []
            for l in best_match['lines']:
                if l.startswith("#EXTINF"):
                    # Set Group
                    l = re.sub(r'group-title="[^"]*"', '', l) 
                    l = l.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{target_group}"')
                elif not l.startswith("#"):
                    # Add UA
                    if "http" in l and "|" not in l:
                        # ASTRO FIX: Use Browser Agent for Astro, Jio Agent for others
                        if "astro" in target_name.lower():
                            l += f"|User-Agent={UA_BROWSER}"
                        else:
                            l += f"|User-Agent={UA_JIO}"
                new_lines.append(l)
            
            final_lines.extend(new_lines)
            added_ids.add(best_match['simple'])
        else:
            print(f"   ⚠️ Channel Not Found: {target_name}")

    # -------------------------------------------
    # 2. ADD REMAINING (Smart HD vs SD Logic)
    # -------------------------------------------
    print("\n2️⃣  Categorizing Remaining Channels...")
    
    count = 0
    for b in source_blocks:
        # 1. Duplicate Check
        if b['simple'] in added_ids: continue
        
        # 2. HD vs SD Logic
        # If this is "suntv" (SD), check if "suntvhd" is already added.
        # If "suntvhd" is in added_ids, SKIP this SD version.
        is_sd = "hd" not in b['simple']
        if is_sd:
            potential_hd = b['simple'] + "hd"
            if potential_hd in added_ids:
                # print(f"   Skipping {b['name']} (HD version already exists)")
                continue

        # Determine Group
        final_group = determine_group(b['name'], b['group'])
        
        # Write Block
        new_lines = []
        for l in b['lines']:
            if l.startswith("#EXTINF"):
                l = re.sub(r'group-title="[^"]*"', '', l)
                l = l.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{final_group}"')
            elif not l.startswith("#"):
                 if "http" in l and "|" not in l:
                        if "astro" in b['name'].lower():
                            l += f"|User-Agent={UA_BROWSER}"
                        else:
                            l += f"|User-Agent={UA_JIO}"
            new_lines.append(l)
            
        final_lines.extend(new_lines)
        added_ids.add(b['simple'])
        count += 1
        
    print(f"   ✅ Added {count} extra channels.")

    # -------------------------------------------
    # 3. LIVE & TEMP
    # -------------------------------------------
    print("\n3️⃣  Adding Live Events & Temp...")
    
    def add_ext(url, g):
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            for l in r.text.splitlines():
                if l.startswith("#EXTINF"):
                    l = re.sub(r'group-title="[^"]*"', '', l)
                    l = re.sub(r'(#EXTINF:[-0-9]+)', f'\\1 group-title="{g}"', l)
                final_lines.append(l)
        except: pass

    add_ext(FANCODE_URL, "Live events")
    add_ext(SONY_LIVE_URL, "Live events")
    add_ext(ZEE_LIVE_URL, "Live events")

    if os.path.exists(YOUTUBE_FILE):
        with open(YOUTUBE_FILE, "r") as f:
            for l in f:
                if "title" in l.lower(): final_lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="",{l.split(":",1)[1].strip()}')
                elif l.startswith("http"): final_lines.append(l.strip())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print(f"\n✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
