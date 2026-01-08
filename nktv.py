import requests
import os
import re
import datetime

# ==========================================
# 1. CONFIGURATION
# ==========================================
OUTPUT_FILE = "nktv.m3u"
TEMP_CHANNELS_FILE = "temporary_channels.txt"

# SOURCES
SRC_ARUNJUNAN = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html"
SRC_FAKEALL = "https://raw.githubusercontent.com/ForceGT/Discord-IPTV/master/playlist.m3u"
SRC_YOUTUBE_PLAYLIST = "https://raw.githubusercontent.com/nkmisc88-jpg/my-youtube-live-playlist/refs/heads/main/playlist.m3u"

# Live Events
SRC_FANCODE = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SRC_SONY = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
SRC_ZEE = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# HEADERS
# Fakeall/Direct links usually need this. Arunjunan often does NOT.
BACKUP_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DL_HEADERS = {"User-Agent": BACKUP_USER_AGENT}

# ==========================================
# 2. MASTER CHANNEL LIST (Keys are Search Tokens)
# ==========================================
# We use simple keywords. If a channel has these words, we grab it.
MASTER_CHANNELS = {
    # 1. TAMIL HD
    "sun tv hd": ("Sun TV HD", "Tamil HD"),
    "ktv hd": ("KTV HD", "Tamil HD"),
    "sun music hd": ("Sun Music HD", "Tamil HD"),
    "star vijay hd": ("Star Vijay HD", "Tamil HD"),
    "vijay super hd": ("Vijay Super HD", "Tamil HD"),
    "zee tamil hd": ("Zee Tamil HD", "Tamil HD"),
    "zee thirai hd": ("Zee Thirai HD", "Tamil HD"),
    "colors tamil hd": ("Colors Tamil HD", "Tamil HD"),
    "jaya tv hd": ("Jaya TV HD", "Tamil HD"),

    # 2. TAMIL SD
    "sun tv": ("Sun TV", "Tamil - Others"),
    "ktv": ("KTV", "Tamil - Others"),
    "sun music": ("Sun Music", "Tamil - Others"),
    "star vijay": ("Star Vijay", "Tamil - Others"),
    "vijay super": ("Vijay Super", "Tamil - Others"),
    "vijay takkar": ("Vijay Takkar", "Tamil - Others"),
    "zee tamil": ("Zee Tamil", "Tamil - Others"),
    "zee thirai": ("Zee Thirai", "Tamil - Others"),
    "colors tamil": ("Colors Tamil", "Tamil - Others"),
    "jaya tv": ("Jaya TV", "Tamil - Others"),
    "j movies": ("J Movies", "Tamil - Others"),
    "jaya max": ("Jaya Max", "Tamil - Others"),
    "adithya": ("Adithya TV", "Tamil - Others"),
    "chutti": ("Chutti TV", "Tamil - Others"),
    "sun life": ("Sun Life", "Tamil - Others"),
    "raj tv": ("Raj TV", "Tamil - Others"),
    "raj digital": ("Raj Digital Plus", "Tamil - Others"),
    "raj musix": ("Raj Musix", "Tamil - Others"),
    "kalaignar": ("Kalaignar TV", "Tamil - Others"),
    "murasu": ("Murasu TV", "Tamil - Others"),
    "isaiaruvi": ("Isaiaruvi", "Tamil - Others"),
    "sirippoli": ("Sirippoli", "Tamil - Others"),
    "polimer tv": ("Polimer TV", "Tamil - Others"),
    "vasanth": ("Vasanth TV", "Tamil - Others"),
    "mega tv": ("Mega TV", "Tamil - Others"),
    "makkal": ("Makkal TV", "Tamil - Others"),
    "vendhar": ("Vendhar TV", "Tamil - Others"),
    "captain tv": ("Captain TV", "Tamil - Others"),
    "mktv": ("MKTV", "Tamil - Others"),
    "peppers": ("Peppers TV", "Tamil - Others"),
    "blacksheep": ("Blacksheep TV", "Tamil - Others"),
    "podhigai": ("DD Podhigai", "Tamil - Others"),

    # 3. TAMIL NEWS
    "sun news": ("Sun News", "Tamil News"),
    "polimer news": ("Polimer News", "Tamil News"),
    "puthiya": ("Puthiya Thalaimurai", "Tamil News"),
    "news7 tamil": ("News7 Tamil", "Tamil News"),
    "thanthi": ("Thanthi TV", "Tamil News"),
    "news18 tamil": ("News18 Tamil Nadu", "Tamil News"),
    "kalaignar seithigal": ("Kalaignar Seithigal", "Tamil News"),
    "jaya plus": ("Jaya Plus", "Tamil News"),
    "news j": ("News J", "Tamil News"),
    "sathiyam": ("Sathiyam TV", "Tamil News"),
    "raj news": ("Raj News 24x7", "Tamil News"),
    "captain news": ("Captain News", "Tamil News"),
    "malai murasu": ("Malai Murasu Seithigal", "Tamil News"),
    "news tamil 24": ("News Tamil 24x7", "Tamil News"),
    "lotus": ("Lotus News", "Tamil News"),

    # 4. SPORTS HD
    "star sports 1 tamil hd": ("Star Sports 1 Tamil HD", "Sports HD"),
    "star sports 2 tamil hd": ("Star Sports 2 Tamil HD", "Sports HD"),
    "star sports 1 hindi hd": ("Star Sports 1 Hindi HD", "Sports HD"),
    "star sports 2 hindi hd": ("Star Sports 2 Hindi HD", "Sports HD"),
    "star sports 1 hd": ("Star Sports 1 HD", "Sports HD"),
    "star sports 2 hd": ("Star Sports 2 HD", "Sports HD"),
    "select 1 hd": ("Star Sports Select 1 HD", "Sports HD"),
    "select 2 hd": ("Star Sports Select 2 HD", "Sports HD"),
    "ten 1 hd": ("Sony Sports Ten 1 HD", "Sports HD"),
    "ten 2 hd": ("Sony Sports Ten 2 HD", "Sports HD"),
    "ten 3 hd": ("Sony Sports Ten 3 HD", "Sports HD"),
    "ten 4 hd": ("Sony Sports Ten 4 HD", "Sports HD"),
    "ten 5 hd": ("Sony Sports Ten 5 HD", "Sports HD"),
    "sports18 1 hd": ("Sports18 1 HD", "Sports HD"),
    "eurosport hd": ("Eurosport HD", "Sports HD"),

    # 5. SPORTS SD
    "star sports 1 tamil": ("Star Sports 1 Tamil", "Sports - Others"),
    "star sports 2 tamil": ("Star Sports 2 Tamil", "Sports - Others"),
    "star sports 1 hindi": ("Star Sports 1 Hindi", "Sports - Others"),
    "star sports 2 hindi": ("Star Sports 2 Hindi", "Sports - Others"),
    "star sports 1 kannada": ("Star Sports 1 Kannada", "Sports - Others"),
    "star sports 1 telugu": ("Star Sports 1 Telugu", "Sports - Others"),
    "star sports 2 telugu": ("Star Sports 2 Telugu", "Sports - Others"),
    "star sports 1": ("Star Sports 1", "Sports - Others"),
    "star sports 2": ("Star Sports 2", "Sports - Others"),
    "star sports 3": ("Star Sports 3", "Sports - Others"),
    "star sports first": ("Star Sports First", "Sports - Others"),
    "star sports khel": ("Star Sports Khel", "Sports - Others"),
    "dd sports": ("DD Sports", "Sports - Others"),

    # 6. GLOBAL SPORTS
    "astro cricket": ("Astro Cricket", "Global Sports"),
    "fox cricket": ("Fox Cricket 501", "Global Sports"),
    "fox 501": ("Fox Cricket 501", "Global Sports"),
    "fox sports 505": ("Fox Sports 505", "Global Sports"),
    "fox 505": ("Fox Sports 505", "Global Sports"),
    "willow": ("Willow Sports", "Global Sports"),
    "sky sports cricket": ("Sky Sports Cricket", "Global Sports"),
    "tnt sports 1": ("TNT Sports 1", "Global Sports"),
    "tnt sports 2": ("TNT Sports 2", "Global Sports"),
    "tnt sports 3": ("TNT Sports 3", "Global Sports"),
    "tnt sports 4": ("TNT Sports 4", "Global Sports"),
    "tnt sports ultimate": ("TNT Sports Ultimate", "Global Sports"),

    # 7. INFOTAINMENT HD
    "discovery hd": ("Discovery HD", "Infotainment HD"),
    "animal planet hd": ("Animal Planet HD", "Infotainment HD"),
    "tlc hd": ("TLC HD", "Infotainment HD"),
    "nat geo hd": ("Nat Geo HD", "Infotainment HD"),
    "nat geo wild hd": ("Nat Geo Wild HD", "Infotainment HD"),
    "sony bbc earth hd": ("Sony BBC Earth HD", "Infotainment HD"),
    "history tv18 hd": ("History TV18 HD", "Infotainment HD"),
    "zee zest hd": ("Zee Zest HD", "Infotainment HD"),

    # 8. INFOTAINMENT SD
    "discovery science": ("Discovery Science", "Infotainment SD"),
    "discovery turbo": ("Discovery Turbo", "Infotainment SD"),
    "dtamil": ("DTamil", "Infotainment SD"),
    "fox life": ("Fox Life", "Infotainment SD"),
    "travelxp": ("TravelXP", "Infotainment SD"),
    "food food": ("Food Food", "Infotainment SD"),
    "good times": ("Good Times", "Infotainment SD"),

    # 9. NEWS (ENG/HIN)
    "ndtv 24x7": ("NDTV 24x7", "English and Hindi News"),
    "republic tv": ("Republic TV", "English and Hindi News"),
    "times now": ("Times Now", "English and Hindi News"),
    "india today": ("India Today", "English and Hindi News"),
    "cnn news18": ("CNN News18", "English and Hindi News"),
    "wion": ("WION", "English and Hindi News"),
    "mirror now": ("Mirror Now", "English and Hindi News"),
    "aaj tak": ("Aaj Tak", "English and Hindi News"),
    "zee news": ("Zee News", "English and Hindi News"),
    "abp news": ("ABP News", "English and Hindi News"),
    "india tv": ("India TV", "English and Hindi News"),
    "news18 india": ("News18 India", "English and Hindi News"),
    "tv9 bharatvarsh": ("TV9 Bharatvarsh", "English and Hindi News"),
    "republic bharat": ("Republic Bharat", "English and Hindi News"),
    "dd news": ("DD News", "English and Hindi News"),

    # 10. OTHERS
    "star maa hd": ("Star Maa HD", "Others"),
    "gemini tv hd": ("Gemini TV HD", "Others"),
    "etv hd": ("ETV HD", "Others"),
    "zee telugu hd": ("Zee Telugu HD", "Others"),
    "asianet hd": ("Asianet HD", "Others"),
    "surya tv hd": ("Surya TV HD", "Others"),
    "zee keralam hd": ("Zee Keralam HD", "Others"),
    "mazhavil manorama hd": ("Mazhavil Manorama HD", "Others"),
    "colors kannada hd": ("Colors Kannada HD", "Others"),
    "zee kannada hd": ("Zee Kannada HD", "Others"),
    "star suvarna hd": ("Star Suvarna HD", "Others"),
    "udaya tv hd": ("Udaya TV HD", "Others"),
    "star plus hd": ("Star Plus HD", "Others"),
    "sony tv hd": ("Sony TV HD", "Others"),
    "zee tv hd": ("Zee TV HD", "Others"),
    "colors hd": ("Colors HD", "Others"),
    "star gold hd": ("Star Gold HD", "Others"),
    "zee cinema hd": ("Zee Cinema HD", "Others"),
    "sony max hd": ("Sony Max HD", "Others"),
    "star movies hd": ("Star Movies HD", "Others"),
    "sony pix hd": ("Sony PIX HD", "Others"),
    "dd national": ("DD National", "Others"),
    "dd malayalam": ("DD Malayalam", "Others"),
    "dd chandana": ("DD Chandana", "Others"),
    "dd yadagiri": ("DD Yadagiri", "Others"),
    "dd saptagiri": ("DD Saptagiri", "Others")
}

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================

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

def search_source(search_tokens, source_data):
    """
    Smart Search:
    Checks if ALL distinct words in the search_tokens exist in the source name.
    Example: 'star sports 1 kannada' matches 'Star Sports 1 Kan' or 'Star Sports 1 Kannada HD'
    """
    required_words = search_tokens.split()
    
    for entry in source_data:
        target_name = entry['name'].lower()
        # Clean target slightly
        target_name = target_name.replace("  ", " ")

        # Check if ALL required words are present in the target name
        match = True
        for word in required_words:
            if word not in target_name:
                match = False
                break
        
        # Additional Logic: If searching for SD (no "hd" in tokens), ignore results with "hd"
        if "hd" not in search_tokens and "hd" in target_name:
             match = False

        if match:
            return entry
    return None

def fetch_extra_group(url, group_name):
    entries = fetch_m3u_entries(url)
    lines = []
    for e in entries:
        meta = re.sub(r'group-title="[^"]*"', '', e['raw_meta'])
        meta = meta.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group_name}"')
        url = e['url']
        
        # PLAYBACK FIX: Add User-Agent ONLY for non-Arunjunan links
        if "http" in url and "|" not in url:
            url += f"|User-Agent={BACKUP_USER_AGENT}"
            
        lines.append(meta)
        lines.append(url)
    return lines

def parse_txt_file(filename, group_name):
    if not os.path.exists(filename): return []
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
            
            # Txt files usually need Headers
            if "http" in url and "|" not in url: 
                url += f"|User-Agent={BACKUP_USER_AGENT}"
                
            lines.append(f'#EXTINF:-1 group-title="{group_name}" tvg-logo="{logo}",{title}')
            lines.append(url)
            title = "Unknown"; logo = ""
    return lines

# ==========================================
# 4. MAIN EXECUTION
# ==========================================
def main():
    print("🚀 Starting NKTV Playlist Generation (Smart Match)...")
    
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines = ["#EXTM3U", f"# Updated on: {ist_now.strftime('%Y-%m-%d %H:%M:%S IST')}"]

    # 1. Fetch Sources
    src1_data = fetch_m3u_entries(SRC_ARUNJUNAN)
    src2_data = fetch_m3u_entries(SRC_FAKEALL)
    
    # 2. Iterate Master List
    print("   Processing Master List...")
    found_count = 0
    
    for search_tokens, (display_name, group) in MASTER_CHANNELS.items():
        entry = None
        source_used = ""
        
        # Priority 1: Arunjunan
        entry = search_source(search_tokens, src1_data)
        if entry: source_used = "Arunjunan"
        
        # Priority 2: Fakeall
        if not entry:
            entry = search_source(search_tokens, src2_data)
            if entry: source_used = "Fakeall"

        if entry:
            found_count += 1
            logo = entry['logo']
            url = entry['url']
            
            # --- PLAYBACK LOGIC ---
            # If Source is Arunjunan -> DO NOT ADD HEADER (Usually breaks it)
            # If Source is Fakeall   -> ADD HEADER (Usually requires it)
            if source_used == "Fakeall" and "http" in url and "|" not in url:
                url += f"|User-Agent={BACKUP_USER_AGENT}"
            
            # Note: We leave Arunjunan URLs purely RAW.

            meta = f'#EXTINF:-1 group-title="{group}" tvg-logo="{logo}",{display_name}'
            final_lines.append(meta)
            final_lines.append(url)
        else:
            print(f"   ⚠️ Missing Channel: {display_name} (Tokens: {search_tokens})")

    print(f"   ✅ Total Main Channels Found: {found_count} / {len(MASTER_CHANNELS)}")

    # 3. Add Extra Groups
    print("   Adding Live Events & Youtube...")
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