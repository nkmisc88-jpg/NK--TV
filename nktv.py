import requests
import os
import re
import datetime

# ==========================================
# 1. CONFIGURATION
# ==========================================
OUTPUT_FILE = "nktv.m3u"
TEMP_CHANNELS_FILE = "temporary_channels.txt"

# SOURCES (Priority Swapped for better playback stability)
# Priority 1: Fakeall (Usually Raw Links, easier to play)
SRC_FAKEALL = "https://raw.githubusercontent.com/ForceGT/Discord-IPTV/master/playlist.m3u"
# Priority 2: Arunjunan (High quality but sometimes complex headers)
SRC_ARUNJUNAN = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html"

# Extra Groups
SRC_YOUTUBE_PLAYLIST = "https://raw.githubusercontent.com/nkmisc88-jpg/my-youtube-live-playlist/refs/heads/main/playlist.m3u"
SRC_FANCODE = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SRC_SONY = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
SRC_ZEE = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# HEADERS
# Standard Browser Header (Works best for Fakeall/ForceGT)
STD_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DL_HEADERS = {"User-Agent": STD_USER_AGENT}

# ==========================================
# 2. MASTER CHANNEL LIST (With ALIASES)
# ==========================================
# Format: "UniqueKey": (["Alias1", "Alias2", "Alias3"], "Display Name", "Group")
MASTER_CHANNELS = {
    # --- TAMIL HD ---
    "suntvhd": (["sun tv hd", "suntv hd", "sun tv hd in"], "Sun TV HD", "Tamil HD"),
    "ktvhd": (["ktv hd", "ktv hd in"], "KTV HD", "Tamil HD"),
    "sunmusichd": (["sun music hd", "sunmusic hd"], "Sun Music HD", "Tamil HD"),
    "starvijayhd": (["star vijay hd", "vijay hd"], "Star Vijay HD", "Tamil HD"),
    "vijaysuperhd": (["vijay super hd", "super hd"], "Vijay Super HD", "Tamil HD"),
    "zeetamilhd": (["zee tamil hd", "zeetamil hd"], "Zee Tamil HD", "Tamil HD"),
    "zeethiraihd": (["zee thirai hd", "zeethirai hd"], "Zee Thirai HD", "Tamil HD"),
    "colorstamilhd": (["colors tamil hd", "colorstamil hd"], "Colors Tamil HD", "Tamil HD"),
    "jayatvhd": (["jaya tv hd", "jayatv hd"], "Jaya TV HD", "Tamil HD"),

    # --- TAMIL SD (Ensure we don't match HD) ---
    "suntv": (["sun tv", "suntv"], "Sun TV", "Tamil - Others"),
    "ktv": (["ktv", "ktv sd"], "KTV", "Tamil - Others"),
    "sunmusic": (["sun music", "sunmusic"], "Sun Music", "Tamil - Others"),
    "starvijay": (["star vijay", "vijay tv"], "Star Vijay", "Tamil - Others"),
    "vijaysuper": (["vijay super", "vijaysuper"], "Vijay Super", "Tamil - Others"),
    "vijaytakkar": (["vijay takkar", "takkar"], "Vijay Takkar", "Tamil - Others"),
    "zeetamil": (["zee tamil", "zeetamil"], "Zee Tamil", "Tamil - Others"),
    "zeethirai": (["zee thirai", "zeethirai"], "Zee Thirai", "Tamil - Others"),
    "colorstamil": (["colors tamil", "colorstamil"], "Colors Tamil", "Tamil - Others"),
    "jayatv": (["jaya tv", "jayatv"], "Jaya TV", "Tamil - Others"),
    "jmovies": (["j movies", "jmovies"], "J Movies", "Tamil - Others"),
    "jayamax": (["jaya max", "jayamax"], "Jaya Max", "Tamil - Others"),
    "adithya": (["adithya", "adithyatv"], "Adithya TV", "Tamil - Others"),
    "chutti": (["chutti", "chuttitv"], "Chutti TV", "Tamil - Others"),
    "sunlife": (["sun life", "sunlife"], "Sun Life", "Tamil - Others"),
    "rajtv": (["raj tv", "rajtv"], "Raj TV", "Tamil - Others"),
    "rajdigital": (["raj digital", "rajdigitalplus"], "Raj Digital Plus", "Tamil - Others"),
    "rajmusix": (["raj musix", "rajmusix"], "Raj Musix", "Tamil - Others"),
    "kalaignar": (["kalaignar", "kalaignartv"], "Kalaignar TV", "Tamil - Others"),
    "murasu": (["murasu", "murasutv"], "Murasu TV", "Tamil - Others"),
    "isaiaruvi": (["isaiaruvi"], "Isaiaruvi", "Tamil - Others"),
    "sirippoli": (["sirippoli"], "Sirippoli", "Tamil - Others"),
    "polimer": (["polimer tv", "polimertv"], "Polimer TV", "Tamil - Others"),
    "vasanth": (["vasanth", "vasanthtv"], "Vasanth TV", "Tamil - Others"),
    "mega": (["mega tv", "megatv"], "Mega TV", "Tamil - Others"),
    "makkal": (["makkal", "makkaltv"], "Makkal TV", "Tamil - Others"),
    "vendhar": (["vendhar", "vendhartv"], "Vendhar TV", "Tamil - Others"),
    "captain": (["captain tv", "captaintv"], "Captain TV", "Tamil - Others"),
    "mktv": (["mktv"], "MKTV", "Tamil - Others"),
    "peppers": (["peppers"], "Peppers TV", "Tamil - Others"),
    "blacksheep": (["blacksheep"], "Blacksheep TV", "Tamil - Others"),
    "podhigai": (["podhigai", "dd podhigai"], "DD Podhigai", "Tamil - Others"),

    # --- TAMIL NEWS ---
    "sunnews": (["sun news", "sunnews"], "Sun News", "Tamil News"),
    "polimernews": (["polimer news", "polimernews"], "Polimer News", "Tamil News"),
    "puthiya": (["puthiya", "puthiyathalaimurai"], "Puthiya Thalaimurai", "Tamil News"),
    "news7": (["news7", "news 7"], "News7 Tamil", "Tamil News"),
    "thanthi": (["thanthi", "thanthitv"], "Thanthi TV", "Tamil News"),
    "news18tamil": (["news18 tamil", "news18 tamilnadu"], "News18 Tamil Nadu", "Tamil News"),
    "kalaignarnews": (["kalaignar seithigal", "kalaignar news"], "Kalaignar Seithigal", "Tamil News"),
    "jayaplus": (["jaya plus", "jayaplus"], "Jaya Plus", "Tamil News"),
    "newsj": (["news j", "newsj"], "News J", "Tamil News"),
    "sathiyam": (["sathiyam"], "Sathiyam TV", "Tamil News"),
    "rajnews": (["raj news", "rajnews"], "Raj News 24x7", "Tamil News"),
    "captainnews": (["captain news"], "Captain News", "Tamil News"),
    "malaimurasu": (["malai murasu"], "Malai Murasu Seithigal", "Tamil News"),
    "newstamil24": (["news tamil 24"], "News Tamil 24x7", "Tamil News"),
    "lotus": (["lotus"], "Lotus News", "Tamil News"),

    # --- SPORTS HD ---
    "ss1tamilhd": (["star sports 1 tamil hd", "ss1 tamil hd"], "Star Sports 1 Tamil HD", "Sports HD"),
    "ss2tamilhd": (["star sports 2 tamil hd", "ss2 tamil hd"], "Star Sports 2 Tamil HD", "Sports HD"),
    "ss1hindihd": (["star sports 1 hindi hd", "ss1 hindi hd"], "Star Sports 1 Hindi HD", "Sports HD"),
    "ss2hindihd": (["star sports 2 hindi hd", "ss2 hindi hd"], "Star Sports 2 Hindi HD", "Sports HD"),
    "ss1hd": (["star sports 1 hd", "ss1 hd"], "Star Sports 1 HD", "Sports HD"),
    "ss2hd": (["star sports 2 hd", "ss2 hd"], "Star Sports 2 HD", "Sports HD"),
    "select1hd": (["select 1 hd", "select1 hd"], "Star Sports Select 1 HD", "Sports HD"),
    "select2hd": (["select 2 hd", "select2 hd"], "Star Sports Select 2 HD", "Sports HD"),
    "ten1hd": (["ten 1 hd", "ten1 hd"], "Sony Sports Ten 1 HD", "Sports HD"),
    "ten2hd": (["ten 2 hd", "ten2 hd"], "Sony Sports Ten 2 HD", "Sports HD"),
    "ten3hd": (["ten 3 hd", "ten3 hd"], "Sony Sports Ten 3 HD", "Sports HD"),
    "ten4hd": (["ten 4 hd", "ten4 hd"], "Sony Sports Ten 4 HD", "Sports HD"),
    "ten5hd": (["ten 5 hd", "ten5 hd"], "Sony Sports Ten 5 HD", "Sports HD"),
    "sports181hd": (["sports18 1 hd"], "Sports18 1 HD", "Sports HD"),
    "eurosport": (["eurosport hd"], "Eurosport HD", "Sports HD"),

    # --- SPORTS SD ---
    "ss1tamil": (["star sports 1 tamil", "ss1 tamil"], "Star Sports 1 Tamil", "Sports - Others"),
    "ss2tamil": (["star sports 2 tamil", "ss2 tamil"], "Star Sports 2 Tamil", "Sports - Others"),
    "ss1hindi": (["star sports 1 hindi", "ss1 hindi"], "Star Sports 1 Hindi", "Sports - Others"),
    "ss2hindi": (["star sports 2 hindi", "ss2 hindi"], "Star Sports 2 Hindi", "Sports - Others"),
    "ss1kannada": (["star sports 1 kannada", "ss1 kannada"], "Star Sports 1 Kannada", "Sports - Others"),
    "ss1telugu": (["star sports 1 telugu", "ss1 telugu"], "Star Sports 1 Telugu", "Sports - Others"),
    "ss2telugu": (["star sports 2 telugu", "ss2 telugu"], "Star Sports 2 Telugu", "Sports - Others"),
    "ss1": (["star sports 1", "ss1"], "Star Sports 1", "Sports - Others"),
    "ss2": (["star sports 2", "ss2"], "Star Sports 2", "Sports - Others"),
    "ss3": (["star sports 3", "ss3"], "Star Sports 3", "Sports - Others"),
    "ssfirst": (["star sports first"], "Star Sports First", "Sports - Others"),
    "sskhel": (["star sports khel"], "Star Sports Khel", "Sports - Others"),
    "ddsports": (["dd sports"], "DD Sports", "Sports - Others"),

    # --- GLOBAL ---
    "astro": (["astro cricket"], "Astro Cricket", "Global Sports"),
    "fox501": (["fox cricket", "fox 501"], "Fox Cricket 501", "Global Sports"),
    "fox505": (["fox sports 505", "fox 505"], "Fox Sports 505", "Global Sports"),
    "willow": (["willow"], "Willow Sports", "Global Sports"),
    "skycricket": (["sky sports cricket"], "Sky Sports Cricket", "Global Sports"),
    "tnt1": (["tnt sports 1"], "TNT Sports 1", "Global Sports"),
    "tnt2": (["tnt sports 2"], "TNT Sports 2", "Global Sports"),
    "tnt3": (["tnt sports 3"], "TNT Sports 3", "Global Sports"),
    "tnt4": (["tnt sports 4"], "TNT Sports 4", "Global Sports"),
    "tntult": (["tnt sports ultimate"], "TNT Sports Ultimate", "Global Sports"),

    # --- INFOTAINMENT HD ---
    "dischd": (["discovery hd"], "Discovery HD", "Infotainment HD"),
    "animhd": (["animal planet hd"], "Animal Planet HD", "Infotainment HD"),
    "tlchd": (["tlc hd"], "TLC HD", "Infotainment HD"),
    "natgeohd": (["nat geo hd", "nat geo hd"], "Nat Geo HD", "Infotainment HD"),
    "natwildhd": (["nat geo wild hd"], "Nat Geo Wild HD", "Infotainment HD"),
    "bbcearthhd": (["bbc earth hd"], "Sony BBC Earth HD", "Infotainment HD"),
    "historyhd": (["history tv18 hd"], "History TV18 HD", "Infotainment HD"),
    "zesthd": (["zee zest hd"], "Zee Zest HD", "Infotainment HD"),

    # --- INFOTAINMENT SD ---
    "discsci": (["discovery science"], "Discovery Science", "Infotainment SD"),
    "discturbo": (["discovery turbo"], "Discovery Turbo", "Infotainment SD"),
    "dtamil": (["dtamil"], "DTamil", "Infotainment SD"),
    "foxlife": (["fox life"], "Fox Life", "Infotainment SD"),
    "travelxp": (["travelxp"], "TravelXP", "Infotainment SD"),
    "foodfood": (["food food"], "Food Food", "Infotainment SD"),
    "goodtimes": (["good times"], "Good Times", "Infotainment SD"),

    # --- NEWS ---
    "ndtv247": (["ndtv 24x7"], "NDTV 24x7", "English and Hindi News"),
    "republic": (["republic tv"], "Republic TV", "English and Hindi News"),
    "timesnow": (["times now"], "Times Now", "English and Hindi News"),
    "indiatoday": (["india today"], "India Today", "English and Hindi News"),
    "cnn18": (["cnn news18"], "CNN News18", "English and Hindi News"),
    "wion": (["wion"], "WION", "English and Hindi News"),
    "mirror": (["mirror now"], "Mirror Now", "English and Hindi News"),
    "aajtak": (["aaj tak"], "Aaj Tak", "English and Hindi News"),
    "zeenews": (["zee news"], "Zee News", "English and Hindi News"),
    "abp": (["abp news"], "ABP News", "English and Hindi News"),
    "indiatv": (["india tv"], "India TV", "English and Hindi News"),
    "news18in": (["news18 india"], "News18 India", "English and Hindi News"),
    "tv9": (["tv9 bharatvarsh"], "TV9 Bharatvarsh", "English and Hindi News"),
    "repbharat": (["republic bharat"], "Republic Bharat", "English and Hindi News"),
    "ddnews": (["dd news"], "DD News", "English and Hindi News"),

    # --- OTHERS ---
    "starmaahd": (["star maa hd"], "Star Maa HD", "Others"),
    "geminihd": (["gemini tv hd"], "Gemini TV HD", "Others"),
    "etvhd": (["etv hd"], "ETV HD", "Others"),
    "zeeteluguhd": (["zee telugu hd"], "Zee Telugu HD", "Others"),
    "asianethd": (["asianet hd"], "Asianet HD", "Others"),
    "suryahd": (["surya tv hd"], "Surya TV HD", "Others"),
    "zeekeralamhd": (["zee keralam hd"], "Zee Keralam HD", "Others"),
    "manoramahd": (["mazhavil manorama hd"], "Mazhavil Manorama HD", "Others"),
    "colkannadahd": (["colors kannada hd"], "Colors Kannada HD", "Others"),
    "zeekannadahd": (["zee kannada hd"], "Zee Kannada HD", "Others"),
    "suvarnahd": (["star suvarna hd"], "Star Suvarna HD", "Others"),
    "udayahd": (["udaya tv hd"], "Udaya TV HD", "Others"),
    "starplushd": (["star plus hd"], "Star Plus HD", "Others"),
    "sonytvhd": (["sony tv hd"], "Sony TV HD", "Others"),
    "zeetvhd": (["zee tv hd"], "Zee TV HD", "Others"),
    "colorshd": (["colors hd"], "Colors HD", "Others"),
    "stargoldhd": (["star gold hd"], "Star Gold HD", "Others"),
    "zeecinemahd": (["zee cinema hd"], "Zee Cinema HD", "Others"),
    "sonymaxhd": (["sony max hd"], "Sony Max HD", "Others"),
    "starmovieshd": (["star movies hd"], "Star Movies HD", "Others"),
    "sonypixhd": (["sony pix hd"], "Sony PIX HD", "Others"),
    "ddnat": (["dd national"], "DD National", "Others"),
    "ddmal": (["dd malayalam"], "DD Malayalam", "Others"),
    "ddchan": (["dd chandana"], "DD Chandana", "Others"),
    "ddyad": (["dd yadagiri"], "DD Yadagiri", "Others"),
    "ddsapt": (["dd saptagiri"], "DD Saptagiri", "Others")
}

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================

def clean_name(name):
    """Normalize name for comparison"""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def fetch_m3u_entries(url):
    print(f"   Downloading: {url}...")
    entries = []
    try:
        r = requests.get(url, headers=DL_HEADERS, timeout=15)
        if r.status_code != 200: return []
        
        lines = r.text.splitlines()
        current_entry = {}
        
        for line in lines:
            line = line.strip()
            if not line: continue
            if line.startswith("#EXTINF"):
                logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                logo = logo_match.group(1) if logo_match else ""
                name = line.split(",")[-1].strip()
                current_entry = {"name": name, "logo": logo, "raw_meta": line}
            elif not line.startswith("#") and current_entry:
                current_entry["url"] = line
                entries.append(current_entry)
                current_entry = {}
    except Exception as e:
        print(f"   ❌ Error: {e}")
    return entries

def search_source(alias_list, source_data, is_sd_search=False):
    """
    Checks if ANY alias matches the source name.
    """
    for entry in source_data:
        entry_clean = clean_name(entry['name'])
        
        for alias in alias_list:
            alias_clean = clean_name(alias)
            
            # Match Condition: Alias is inside Source Name
            if alias_clean in entry_clean:
                # Extra protection for SD channels (avoid matching "Sun TV HD" when looking for "Sun TV")
                if is_sd_search and "hd" in entry_clean and "hd" not in alias_clean:
                    continue 
                return entry
    return None

def fetch_extra_group(url, group_name):
    entries = fetch_m3u_entries(url)
    lines = []
    for e in entries:
        meta = re.sub(r'group-title="[^"]*"', '', e['raw_meta'])
        meta = meta.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group_name}"')
        url = e['url']
        if "http" in url and "|" not in url:
            url += f"|User-Agent={STD_USER_AGENT}"
        lines.append(meta)
        lines.append(url)
    return lines

def parse_txt_file(filename, group_name):
    print(f"   Reading {filename}...")
    if not os.path.exists(filename):
        print("   ⚠️ Temporary Channels file NOT found. Creating empty group.")
        return []
        
    lines = []
    with open(filename, "r") as f:
        content = f.readlines()
    
    title = "Unknown"; logo = ""
    for line in content:
        line = line.strip()
        if line.lower().startswith("title:"): title = line.split(":", 1)[1].strip()
        elif line.lower().startswith("logo:"): logo = line.split(":", 1)[1].strip()
        elif line.lower().startswith("link:") or line.startswith("http"):
            url = line.split("link:", 1)[1].strip() if "link:" in line.lower() else line
            if "http" in url and "|" not in url: url += f"|User-Agent={STD_USER_AGENT}"
            lines.append(f'#EXTINF:-1 group-title="{group_name}" tvg-logo="{logo}",{title}')
            lines.append(url)
            title = "Unknown"; logo = ""
    return lines

# ==========================================
# 4. MAIN EXECUTION
# ==========================================
def main():
    print("🚀 Starting NKTV Playlist Generation (Fix v4)...")
    
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    # Adding timestamp to first line ensures Git always detects a change
    final_lines = ["#EXTM3U", f"# Updated on: {ist_now.strftime('%Y-%m-%d %H:%M:%S IST')}"]

    # 1. Fetch Sources
    src_fakeall = fetch_m3u_entries(SRC_FAKEALL)
    src_arunjunan = fetch_m3u_entries(SRC_ARUNJUNAN)
    
    # 2. Iterate Master List
    print("   Processing Master List...")
    found_count = 0
    missing_list = []
    
    for unique_id, (aliases, display_name, group) in MASTER_CHANNELS.items():
        entry = None
        source_used = ""
        is_sd = "Others" in group or "SD" in group
        
        # Priority 1: Fakeall (Better Playback)
        entry = search_source(aliases, src_fakeall, is_sd_search=is_sd)
        if entry: source_used = "Fakeall"
        
        # Priority 2: Arunjunan
        if not entry:
            entry = search_source(aliases, src_arunjunan, is_sd_search=is_sd)
            if entry: source_used = "Arunjunan"

        if entry:
            found_count += 1
            logo = entry['logo']
            url = entry['url']
            
            # --- HEADER LOGIC ---
            # Fakeall -> Needs Header
            if source_used == "Fakeall" and "http" in url and "|" not in url:
                url += f"|User-Agent={STD_USER_AGENT}"
            # Arunjunan -> RAW (Do not touch)

            meta = f'#EXTINF:-1 group-title="{group}" tvg-logo="{logo}",{display_name}'
            final_lines.append(meta)
            final_lines.append(url)
        else:
            missing_list.append(display_name)
            print(f"   ❌ MISSING: {display_name}")

    print(f"\n   📊 SUMMARY: Found {found_count} / {len(MASTER_CHANNELS)}")
    if missing_list:
        print("   ⚠️  Channels not found in any source:")
        for m in missing_list: print(f"      - {m}")

    # 3. Add Extra Groups
    print("\n   Adding Extras...")
    final_lines.extend(fetch_extra_group(SRC_FANCODE, "Live Events"))
    final_lines.extend(fetch_extra_group(SRC_SONY, "Live Events"))
    final_lines.extend(fetch_extra_group(SRC_ZEE, "Live Events"))
    final_lines.extend(fetch_extra_group(SRC_YOUTUBE_PLAYLIST, "YouTube"))
    final_lines.extend(parse_txt_file(TEMP_CHANNELS_FILE, "Temporary Channels"))

    # 4. Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    print(f"✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
