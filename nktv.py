import requests
import os
import re
import datetime

# ==========================================
# 1. CONFIGURATION & SOURCES
# ==========================================
OUTPUT_FILE = "nktv.m3u"
TEMP_CHANNELS_FILE = "temporary_channels.txt"
JIOTV_REF_FILE = "jiotv_playlist.m3u" # Must exist in repo for Priority 3

# Source URLs
SRC_ARUNJUNAN = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html"
SRC_FAKEALL = "https://raw.githubusercontent.com/ForceGT/Discord-IPTV/master/playlist.m3u" # Standard Fakeall/Discord Source
SRC_YOUTUBE_PLAYLIST = "https://raw.githubusercontent.com/nkmisc88-jpg/my-youtube-live-playlist/refs/heads/main/playlist.m3u"

# Live Event Sources
SRC_FANCODE = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SRC_SONY = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
SRC_ZEE = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# Headers
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# ==========================================
# 2. MASTER CHANNEL LIST (The "Brain")
# ==========================================
# Format: "Clean Name": ("Display Name", "Group")
# We use a Dictionary for O(1) lookups and strict enforcement.
MASTER_CHANNELS = {
    # 1. TAMIL HD
    "suntvhd": ("Sun TV HD", "Tamil HD"),
    "ktvhd": ("KTV HD", "Tamil HD"),
    "sunmusichd": ("Sun Music HD", "Tamil HD"),
    "starvijayhd": ("Star Vijay HD", "Tamil HD"),
    "vijaysuperhd": ("Vijay Super HD", "Tamil HD"),
    "zeetamilhd": ("Zee Tamil HD", "Tamil HD"),
    "zeethiraihd": ("Zee Thirai HD", "Tamil HD"),
    "colorstamilhd": ("Colors Tamil HD", "Tamil HD"),
    "jayatvhd": ("Jaya TV HD", "Tamil HD"),

    # 2. TAMIL SD (Others)
    "suntv": ("Sun TV", "Tamil - Others"),
    "ktv": ("KTV", "Tamil - Others"),
    "sunmusic": ("Sun Music", "Tamil - Others"),
    "starvijay": ("Star Vijay", "Tamil - Others"),
    "vijaysuper": ("Vijay Super", "Tamil - Others"),
    "vijaytakkar": ("Vijay Takkar", "Tamil - Others"),
    "zeetamil": ("Zee Tamil", "Tamil - Others"),
    "zeethirai": ("Zee Thirai", "Tamil - Others"),
    "colorstamil": ("Colors Tamil", "Tamil - Others"),
    "jayatv": ("Jaya TV", "Tamil - Others"),
    "jmovies": ("J Movies", "Tamil - Others"),
    "jayamax": ("Jaya Max", "Tamil - Others"),
    "adithyatv": ("Adithya TV", "Tamil - Others"),
    "chuttitv": ("Chutti TV", "Tamil - Others"),
    "sunlife": ("Sun Life", "Tamil - Others"),
    "rajtv": ("Raj TV", "Tamil - Others"),
    "rajdigitalplus": ("Raj Digital Plus", "Tamil - Others"),
    "rajmusix": ("Raj Musix", "Tamil - Others"),
    "kalaignartv": ("Kalaignar TV", "Tamil - Others"),
    "murasutv": ("Murasu TV", "Tamil - Others"),
    "isaiaruvi": ("Isaiaruvi", "Tamil - Others"),
    "sirippoli": ("Sirippoli", "Tamil - Others"),
    "polimertv": ("Polimer TV", "Tamil - Others"),
    "vasanthtv": ("Vasanth TV", "Tamil - Others"),
    "megatv": ("Mega TV", "Tamil - Others"),
    "makkaltv": ("Makkal TV", "Tamil - Others"),
    "vendhartv": ("Vendhar TV", "Tamil - Others"),
    "captaintv": ("Captain TV", "Tamil - Others"),
    "mktv": ("MKTV", "Tamil - Others"),
    "pepperstv": ("Peppers TV", "Tamil - Others"),
    "blacksheeptv": ("Blacksheep TV", "Tamil - Others"),
    "ddpodhigai": ("DD Podhigai", "Tamil - Others"),

    # 3. TAMIL NEWS
    "sunnews": ("Sun News", "Tamil News"),
    "polimernews": ("Polimer News", "Tamil News"),
    "puthiyathalaimurai": ("Puthiya Thalaimurai", "Tamil News"),
    "news7tamil": ("News7 Tamil", "Tamil News"),
    "thanthitv": ("Thanthi TV", "Tamil News"),
    "news18tamilnadu": ("News18 Tamil Nadu", "Tamil News"),
    "kalaignarseithigal": ("Kalaignar Seithigal", "Tamil News"),
    "jayaplus": ("Jaya Plus", "Tamil News"),
    "newsj": ("News J", "Tamil News"),
    "sathiyamtv": ("Sathiyam TV", "Tamil News"),
    "rajnews24x7": ("Raj News 24x7", "Tamil News"),
    "captainnews": ("Captain News", "Tamil News"),
    "malaimurasuseithigal": ("Malai Murasu Seithigal", "Tamil News"),
    "newstamil24x7": ("News Tamil 24x7", "Tamil News"),
    "lotusnews": ("Lotus News", "Tamil News"),

    # 4. SPORTS HD
    "starsports1tamilhd": ("Star Sports 1 Tamil HD", "Sports HD"),
    "starsports2tamilhd": ("Star Sports 2 Tamil HD", "Sports HD"),
    "starsports1hindihd": ("Star Sports 1 Hindi HD", "Sports HD"),
    "starsports2hindihd": ("Star Sports 2 Hindi HD", "Sports HD"),
    "starsports1hd": ("Star Sports 1 HD", "Sports HD"),
    "starsports2hd": ("Star Sports 2 HD", "Sports HD"),
    "starsportsselect1hd": ("Star Sports Select 1 HD", "Sports HD"),
    "starsportsselect2hd": ("Star Sports Select 2 HD", "Sports HD"),
    "sonysportsten1hd": ("Sony Sports Ten 1 HD", "Sports HD"),
    "sonysportsten2hd": ("Sony Sports Ten 2 HD", "Sports HD"),
    "sonysportsten3hd": ("Sony Sports Ten 3 HD", "Sports HD"),
    "sonysportsten4hd": ("Sony Sports Ten 4 HD", "Sports HD"),
    "sonysportsten5hd": ("Sony Sports Ten 5 HD", "Sports HD"),
    "sports181hd": ("Sports18 1 HD", "Sports HD"),
    "eurosporthd": ("Eurosport HD", "Sports HD"),

    # 5. SPORTS SD
    "starsports1tamil": ("Star Sports 1 Tamil", "Sports - Others"),
    "starsports2tamil": ("Star Sports 2 Tamil", "Sports - Others"),
    "starsports1hindi": ("Star Sports 1 Hindi", "Sports - Others"),
    "starsports2hindi": ("Star Sports 2 Hindi", "Sports - Others"),
    "starsports1kannada": ("Star Sports 1 Kannada", "Sports - Others"),
    "starsports1telugu": ("Star Sports 1 Telugu", "Sports - Others"),
    "starsports2telugu": ("Star Sports 2 Telugu", "Sports - Others"),
    "starsports1": ("Star Sports 1", "Sports - Others"),
    "starsports2": ("Star Sports 2", "Sports - Others"),
    "starsports3": ("Star Sports 3", "Sports - Others"),
    "starsportsfirst": ("Star Sports First", "Sports - Others"),
    "starsportskhel": ("Star Sports Khel", "Sports - Others"),
    "ddsports": ("DD Sports", "Sports - Others"),

    # 6. GLOBAL SPORTS (NEW)
    "astrocricket": ("Astro Cricket", "Global Sports"),
    "foxcricket501": ("Fox Cricket 501", "Global Sports"),
    "fox501": ("Fox Cricket 501", "Global Sports"), # Alias
    "foxsports505": ("Fox Sports 505", "Global Sports"),
    "fox505": ("Fox Sports 505", "Global Sports"), # Alias
    "willowsports": ("Willow Sports", "Global Sports"),
    "willowxtra": ("Willow Xtra", "Global Sports"),
    "willowsportsextra": ("Willow Xtra", "Global Sports"), # Alias
    "skysportscricket": ("Sky Sports Cricket", "Global Sports"),
    "tntsports1": ("TNT Sports 1", "Global Sports"),
    "tntsports2": ("TNT Sports 2", "Global Sports"),
    "tntsports3": ("TNT Sports 3", "Global Sports"),
    "tntsports4": ("TNT Sports 4", "Global Sports"),
    "tntsportsultimate": ("TNT Sports Ultimate", "Global Sports"),

    # 7. INFOTAINMENT HD
    "discoveryhd": ("Discovery HD", "Infotainment HD"),
    "animalplanethd": ("Animal Planet HD", "Infotainment HD"),
    "tlchd": ("TLC HD", "Infotainment HD"),
    "natgeohd": ("Nat Geo HD", "Infotainment HD"),
    "natgeowildhd": ("Nat Geo Wild HD", "Infotainment HD"),
    "sonybbcearthhd": ("Sony BBC Earth HD", "Infotainment HD"),
    "historytv18hd": ("History TV18 HD", "Infotainment HD"),
    "zeezesthd": ("Zee Zest HD", "Infotainment HD"),

    # 8. INFOTAINMENT SD
    "discoveryscience": ("Discovery Science", "Infotainment SD"),
    "discoveryturbo": ("Discovery Turbo", "Infotainment SD"),
    "dtamil": ("DTamil", "Infotainment SD"),
    "foxlife": ("Fox Life", "Infotainment SD"),
    "travelxp": ("TravelXP", "Infotainment SD"),
    "foodfood": ("Food Food", "Infotainment SD"),
    "goodtimes": ("Good Times", "Infotainment SD"),

    # 9. NEWS (ENG/HIN)
    "ndtv24x7": ("NDTV 24x7", "English and Hindi News"),
    "republictv": ("Republic TV", "English and Hindi News"),
    "timesnow": ("Times Now", "English and Hindi News"),
    "indiatoday": ("India Today", "English and Hindi News"),
    "cnnnews18": ("CNN News18", "English and Hindi News"),
    "wion": ("WION", "English and Hindi News"),
    "mirrornow": ("Mirror Now", "English and Hindi News"),
    "aajtak": ("Aaj Tak", "English and Hindi News"),
    "zeenews": ("Zee News", "English and Hindi News"),
    "abpnews": ("ABP News", "English and Hindi News"),
    "indiatv": ("India TV", "English and Hindi News"),
    "news18india": ("News18 India", "English and Hindi News"),
    "tv9bharatvarsh": ("TV9 Bharatvarsh", "English and Hindi News"),
    "republicbharat": ("Republic Bharat", "English and Hindi News"),
    "ddnews": ("DD News", "English and Hindi News"),

    # 10. OTHERS
    "starmaahd": ("Star Maa HD", "Others"),
    "geminitvhd": ("Gemini TV HD", "Others"),
    "etvhd": ("ETV HD", "Others"),
    "zeeteluguhd": ("Zee Telugu HD", "Others"),
    "asianethd": ("Asianet HD", "Others"),
    "suryatvhd": ("Surya TV HD", "Others"),
    "zeekeralamhd": ("Zee Keralam HD", "Others"),
    "mazhavilmanoramahd": ("Mazhavil Manorama HD", "Others"),
    "colorskannadahd": ("Colors Kannada HD", "Others"),
    "zeekannadahd": ("Zee Kannada HD", "Others"),
    "starsuvarnahd": ("Star Suvarna HD", "Others"),
    "udayatvhd": ("Udaya TV HD", "Others"),
    "starplushd": ("Star Plus HD", "Others"),
    "sonytvhd": ("Sony TV HD", "Others"),
    "zeetvhd": ("Zee TV HD", "Others"),
    "colorshd": ("Colors HD", "Others"),
    "stargoldhd": ("Star Gold HD", "Others"),
    "zeecinemahd": ("Zee Cinema HD", "Others"),
    "sonymaxhd": ("Sony Max HD", "Others"),
    "starmovieshd": ("Star Movies HD", "Others"),
    "sonypixhd": ("Sony PIX HD", "Others"),
    "ddnational": ("DD National", "Others"),
    "ddmalayalam": ("DD Malayalam", "Others"),
    "ddchandana": ("DD Chandana", "Others"),
    "ddyadagiri": ("DD Yadagiri", "Others"),
    "ddsaptagiri": ("DD Saptagiri", "Others")
}

# ==========================================
# 3. CORE LOGIC
# ==========================================

def clean_name(name):
    """Normalize name: lowercase, remove spaces, remove symbols"""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def fetch_m3u_entries(url):
    """Download and parse M3U into a list of dicts"""
    print(f"   Downloading: {url}...")
    entries = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200: return []
        
        lines = r.text.splitlines()
        current_entry = {}
        
        for line in lines:
            line = line.strip()
            if not line: continue
            if line.startswith("#EXTINF"):
                # Extract Logo
                logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                logo = logo_match.group(1) if logo_match else ""
                
                # Extract Name (last part after comma)
                name = line.split(",")[-1].strip()
                
                current_entry = {"name": name, "logo": logo, "raw_meta": line}
            elif not line.startswith("#") and current_entry:
                current_entry["url"] = line
                entries.append(current_entry)
                current_entry = {}
    except Exception as e:
        print(f"   ❌ Error: {e}")
    return entries

def get_jiotv_fallback(clean_id):
    """Priority 3: Look in local reference file and generate 192.168 link"""
    if not os.path.exists(JIOTV_REF_FILE): return None
    
    # We parse the local file manually to find the ID
    try:
        with open(JIOTV_REF_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "channel-id=" in line or "tvg-id=" in line:
                     # This requires advanced parsing of your specific jiotv file format.
                     # For now, we assume standard M3U structure.
                     pass
    except: pass
    return None 

def fetch_extra_group(url, group_name):
    """Fetches a playlist and forces a specific Group Name"""
    entries = fetch_m3u_entries(url)
    lines = []
    for e in entries:
        # Replace Group Title
        meta = re.sub(r'group-title="[^"]*"', '', e['raw_meta'])
        meta = meta.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group_name}"')
        lines.append(meta)
        lines.append(e['url'])
    return lines

def parse_txt_file(filename, group_name):
    """Reads simple txt file (Title: ... Link: ...)"""
    if not os.path.exists(filename): return []
    lines = []
    with open(filename, "r") as f:
        content = f.readlines()
    
    title = "Unknown"
    logo = ""
    for line in content:
        line = line.strip()
        if line.lower().startswith("title:"): title = line.split(":", 1)[1].strip()
        elif line.lower().startswith("logo:"): logo = line.split(":", 1)[1].strip()
        elif line.lower().startswith("link:") or line.startswith("http"):
            url = line.split("link:", 1)[1].strip() if "link:" in line.lower() else line
            lines.append(f'#EXTINF:-1 group-title="{group_name}" tvg-logo="{logo}",{title}')
            lines.append(url)
            title = "Unknown"; logo = ""
    return lines

# ==========================================
# 4. MAIN EXECUTION
# ==========================================
def main():
    print("🚀 Starting NKTV Playlist Generation...")
    
    # 1. Fetch Sources
    src1_data = fetch_m3u_entries(SRC_ARUNJUNAN)
    src2_data = fetch_m3u_entries(SRC_FAKEALL)
    # src3_data = [Read local file logic here if implemented]

    # Create Lookup Dictionaries for Speed
    # Key = Clean Name, Value = Entry Object
    db_src1 = {clean_name(x['name']): x for x in src1_data}
    db_src2 = {clean_name(x['name']): x for x in src2_data}
    
    final_lines = ["#EXTM3U"]
    
    # 2. Iterate Master List (Strict Order)
    print("   Processing Master List...")
    for clean_id, (display_name, group) in MASTER_CHANNELS.items():
        entry = None
        
        # Priority 1: Arunjunan
        if clean_id in db_src1:
            entry = db_src1[clean_id]
        
        # Priority 2: Fakeall
        elif clean_id in db_src2:
            entry = db_src2[clean_id]
            
        # Priority 3: JioTV (Placeholder for logic)
        # elif clean_id in db_jiotv: ...

        if entry:
            # Construct New Metadata with Correct Group & Display Name
            # Use original logo if available
            logo = entry['logo']
            meta = f'#EXTINF:-1 group-title="{group}" tvg-logo="{logo}",{display_name}'
            final_lines.append(meta)
            final_lines.append(entry['url'])
        else:
            print(f"   ⚠️ Missing Channel: {display_name}")

    # 3. Add Extra Groups
    print("   Adding Global Sports...") 
    # (Global sports are already in Master List, so they are processed above if found in sources)
    
    print("   Adding Live Events...")
    final_lines.extend(fetch_extra_group(SRC_FANCODE, "Live Events"))
    final_lines.extend(fetch_extra_group(SRC_SONY, "Live Events"))
    final_lines.extend(fetch_extra_group(SRC_ZEE, "Live Events"))

    print("   Adding YouTube Playlist...")
    final_lines.extend(fetch_extra_group(SRC_YOUTUBE_PLAYLIST, "YouTube"))

    print("   Adding Temporary Channels...")
    final_lines.extend(parse_txt_file(TEMP_CHANNELS_FILE, "Temporary Channels"))

    # 4. Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    print(f"✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
