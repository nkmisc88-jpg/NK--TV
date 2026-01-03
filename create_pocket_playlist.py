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
UA_BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# EXCLUSION LIST (Now includes 'apac')
BAD_KEYWORDS = [
    "hits", "tata play", "tataplay", "local", "fm", "radio", 
    "pluto", "yupp", "usa", "overseas", "cinemania", "cinema", "apac",
    "kannada", "malayalam", "telugu", "bengali", "marathi", 
    "gujarati", "odia", "punjabi", "urdu", "nepali"
]

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
    
    # MOVED ITEMS
    ("Sports HD", "Star Sports 1 Tamil HD"), ("Sports HD", "Star Sports 2 Tamil HD"),

    # --- TAMIL HD ---
    ("Tamil HD", "Sun TV HD"), ("Tamil HD", "KTV HD"),
    ("Tamil HD", "Star Vijay HD"), ("Tamil HD", "Zee Tamil HD"),
    ("Tamil HD", "Colors Tamil HD"), ("Tamil HD", "Jaya TV HD"),
    ("Tamil HD", "Zee Thirai HD"), 
    ("Tamil HD", "Astro Vaanavil"), ("Tamil HD", "Astro Vinmeen HD"),
    ("Tamil HD", "Astro Thangathirai"), ("Tamil HD", "Astro Vellithirai"),

    # --- TAMIL SD ---
    ("Tamil SD", "Vijay Takkar"),

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

    # --- OTHERS ---
    ("Others", "Star Plus HD"), ("Others", "Sony SET HD"),
    ("Others", "Sony SAB HD"), ("Others", "Zee TV HD"),
    ("Others", "Colors HD"), ("Others", "Star Bharat HD"),
    
    # --- KIDS ---
    ("Kids", "CN HD+ Tamil"),
    ("Kids", "Nick"), ("Kids", "Sonic"), ("Kids", "Hungama"),
    ("Kids", "Disney Channel"), ("Kids", "Cartoon Network"),
    ("Kids", "Pogo"), ("Kids", "Sony Yay"), ("Kids", "Discovery Kids")
]

# ==========================================
# LOGIC
# ==========================================

def simplified_name(name):
    if not name: return ""
    name = re.sub(r'[\(\[\{].*?[\)\]\}]', '', name.lower())
    return re.sub(r'[^a-z0-9]', '', name)

def get_source_data():
    print("📥 Downloading Source Playlist...")
    items = []
    try:
        r = requests.get(POCKET_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if r.status_code == 200:
            lines = r.text.splitlines()
            current_props = []
            
            for i in range(len(lines)):
                line = lines[i].strip()
                if not line: continue
                
                if line.startswith("#KODIPROP") or line.startswith("#EXTVLCOPT"):
                    current_props.append(line)
                    continue

                if line.startswith("#EXTINF"):
                    raw_name = line.split(",")[-1].strip()
                    simple = simplified_name(raw_name)
                    
                    logo = ""
                    m_logo = re.search(r'tvg-logo="([^"]*)"', line)
                    if m_logo: logo = m_logo.group(1)
                    
                    grp = ""
                    m_grp = re.search(r'group-title="([^"]*)"', line)
                    if m_grp: grp = m_grp.group(1).lower()

                    link = ""
                    if i + 1 < len(lines):
                        pot_link = lines[i+1].strip()
                        if pot_link and not pot_link.startswith("#"):
                            link = pot_link

                    if link:
                        items.append({
                            'name': raw_name,
                            'simple': simple,
                            'logo': logo,
                            'group_src': grp,
                            'link': link,
                            'props': current_props
                        })
                    
                    current_props = []
    except Exception as e:
        print(f"   ❌ Failed to load source: {e}")
    return items

def determine_group(name, src_group):
    """Categorizes unknown channels."""
    name = name.lower()
    src_group = src_group.lower()

    if "vijay takkar" in name: return "Tamil SD"
    if "cn hd+" in name and "tamil" in name: return "Kids"
    if "star sports" in name and "tamil" in name: return "Sports HD"

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

    if any(k in name for k in ["cartoon", "pogo", "nick", "disney", "sonic", "hungama", "kids"]):
        return "Kids"

    return "Others"

def main():
    source_items = get_source_data()
    
    final_lines = ["#EXTM3U"]
    final_lines.append("http://0.0.0.0")

    added_ids = set() 
    
    print("\n1️⃣  Processing Master List...")
    for target_group, target_name in MASTER_CHANNELS:
        target_simple = simplified_name(target_name)
        
        candidates = [i for i in source_items if i['simple'] == target_simple or target_simple in i['simple']]
        
        best_match = None
        if candidates:
            for c in candidates:
                if c['props']: best_match = c; break
            if not best_match: best_match = candidates[0]

        if best_match:
            final_lines.extend(best_match['props'])
            
            line = f'#EXTINF:-1 group-title="{target_group}" tvg-logo="{best_match["logo"]}",{target_name}'
            final_lines.append(line)
            
            lnk = best_match['link']
            if "astro" in target_name.lower() and "http" in lnk:
                if "|" in lnk: lnk = lnk.split("|")[0]
                lnk += f"|User-Agent={UA_BROWSER}"
            final_lines.append(lnk)
            
            added_ids.add(best_match['simple'])
        else:
            print(f"   ⚠️ Channel Not Found: {target_name}")

    print("\n2️⃣  Cleaning & Sorting Extras...")
    count = 0
    for item in source_items:
        if item['simple'] in added_ids: continue
        
        name_lower = item['name'].lower()
        grp_lower = item['group_src'].lower()

        # REMOVAL FILTERS (Added 'apac')
        if any(bad in name_lower for bad in BAD_KEYWORDS) or any(bad in grp_lower for bad in BAD_KEYWORDS):
            if "rasi" in name_lower: pass 
            else: continue 

        is_sd = "hd" not in item['simple']
        if is_sd:
            potential_hd = item['simple'] + "hd"
            if potential_hd in added_ids: continue

        final_group = determine_group(item['name'], item['group_src'])
        
        final_lines.extend(item['props'])
        
        line = f'#EXTINF:-1 group-title="{final_group}" tvg-logo="{item["logo"]}",{item["name"]}'
        final_lines.append(line)
        
        lnk = item['link']
        if not item['props'] and "http" in lnk:
             if "|" in lnk: lnk = lnk.split("|")[0]
             lnk += f"|User-Agent={UA_BROWSER}"
        final_lines.append(lnk)
            
        added_ids.add(item['simple'])
        count += 1
        
    print(f"   ✅ Added {count} extra channels.")

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
                if "title" in l.lower(): 
                    parts = l.split(":", 1)
                    if len(parts) > 1:
                        final_lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="",{parts[1].strip()}')
                elif l.startswith("http"): final_lines.append(l.strip())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f: f.write("\n".join(final_lines))
    print(f"\n✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()