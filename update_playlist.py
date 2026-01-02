import requests
import re
import datetime
import os

# ==========================================
# 1. SETUP & VARIABLES
# ==========================================
template_file = "template.m3u"
youtube_file = "youtube.txt"
reference_file = "jiotv_playlist.m3u.m3u8" # Local ID Map
output_file = "playlist.m3u"

# Source URLs
URL_LOCAL_BASE = "http://192.168.0.146:5350/live"
URL_ARUN = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/refs/heads/main/index.html"
URL_FAKEALL = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"

# Live Event URLs
URL_FANCODE = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
URL_SONY_LIVE = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
URL_ZEE_LIVE = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"

# Headers (Browser Simulation)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def clean_key(name):
    """Converts 'Star Sports 1 HD' -> 'starsports1hd' for matching."""
    if not name: return ""
    # Remove brackets, symbols, spaces, and convert to lower
    clean = re.sub(r'\(.*?\)|\[.*?\]', '', name)
    return re.sub(r'[^a-z0-9]', '', clean.lower())

def parse_m3u(source_type, location):
    """
    Reads an M3U file (URL or Local) and returns a dictionary.
    Format: { 'starsports1hd': {'link': '...', 'logo': '...'} }
    """
    db = {}
    content = ""
    print(f"Loading {source_type}...")

    try:
        if source_type == "LOCAL_MAP":
            if os.path.exists(location):
                with open(location, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                print(f"   ⚠️ Local file missing: {location}")
                return {}
        else:
            # Remote URL
            r = requests.get(location, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                content = r.text
            else:
                print(f"   ❌ Failed to fetch {source_type}: {r.status_code}")
                return {}

        lines = content.splitlines()
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("#EXTINF"):
                # 1. Extract Name
                name = line.split(",")[-1].strip()
                # 2. Extract Logo
                logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                logo = logo_match.group(1) if logo_match else ""
                # 3. Extract ID (Specific to Local Map)
                id_match = re.search(r'tvg-id="(\d+)"', line)
                ch_id = id_match.group(1) if id_match else None
                
                # 4. Determine Link
                link = ""
                if source_type == "LOCAL_MAP" and ch_id:
                    link = f"{URL_LOCAL_BASE}/{ch_id}.m3u8"
                elif source_type != "LOCAL_MAP":
                    # For remote lists, link is usually on the next line
                    if i + 1 < len(lines):
                        next_line = lines[i+1].strip()
                        if next_line and not next_line.startswith("#"):
                            link = next_line

                # 5. Save to DB
                if link and name:
                    key = clean_key(name)
                    # Store original name too for display if needed
                    db[key] = {'link': link, 'logo': logo, 'name': name}

        print(f"   ✅ {source_type}: {len(db)} channels loaded.")
        return db

    except Exception as e:
        print(f"   ❌ Critical Error loading {source_type}: {e}")
        return {}

# ==========================================
# 3. MAIN SCRIPT
# ==========================================

# --- Step A: Load All Sources ---
DB_LOCAL = parse_m3u("LOCAL_MAP", reference_file)
DB_ARUN = parse_m3u("ARUN_POCKET", URL_ARUN)
DB_FAKEALL = parse_m3u("FAKEALL", URL_FAKEALL)

final_lines = []
final_lines.append('#EXTM3U x-tvg-url="http://192.168.0.146:5350/epg.xml.gz"')

# Add Update Time
ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
final_lines.append(f'#EXTINF:-1 group-title="Update Info" tvg-logo="https://i.imgur.com/7Xj4G6d.png",🟡 Updated: {ist_now.strftime("%d-%m-%Y %H:%M")}')
final_lines.append("http://0.0.0.0")

# --- Step B: Process Template (Main Channels) ---
print("\nProcessing Template...")
if os.path.exists(template_file):
    with open(template_file, "r", encoding="utf-8") as f:
        template_lines = f.readlines()

    for line in template_lines:
        line = line.strip()
        if line.startswith("#EXTINF"):
            # Extract info from template
            name = line.split(",")[-1].strip()
            group_match = re.search(r'group-title="([^"]*)"', line)
            group = group_match.group(1) if group_match else "General"
            
            key = clean_key(name)
            link = None
            logo = None

            # --- PRIORITY LOGIC ---
            # Group 1: Star, Sony, Zee (Arun > Fakeall > Local)
            if any(k in key for k in ["star", "sony", "zee", "set"]):
                if key in DB_ARUN:
                    link = DB_ARUN[key]['link']
                    logo = DB_ARUN[key]['logo']
                elif key in DB_FAKEALL:
                    link = DB_FAKEALL[key]['link']
                    logo = DB_FAKEALL[key]['logo']
                elif key in DB_LOCAL:
                    link = DB_LOCAL[key]['link']
            
            # Group 2: All Others (Local > Arun > Fakeall)
            else:
                if key in DB_LOCAL:
                    link = DB_LOCAL[key]['link']
                elif key in DB_ARUN:
                    link = DB_ARUN[key]['link']
                    logo = DB_ARUN[key]['logo']
                elif key in DB_FAKEALL:
                    link = DB_FAKEALL[key]['link']
                    logo = DB_FAKEALL[key]['logo']

            # --- WRITE TO PLAYLIST ---
            # If no logo found in source, use template logic (simplified here to reuse source logo if exists)
            logo_str = f'tvg-logo="{logo}"' if logo else 'tvg-logo=""'
            
            if link:
                final_lines.append(f'#EXTINF:-1 group-title="{group}" {logo_str},{name}')
                final_lines.append(link)
            else:
                print(f"   ⚠️ Missing: {name}")
                final_lines.append(f'#EXTINF:-1 group-title="{group}" {logo_str},⚠️ Offline: {name}')
                final_lines.append("http://0.0.0.0")

else:
    print("❌ Template file not found!")

# --- Step C: Extras (Astro / Rasi) ---
print("\nAdding Extras...")
wanted_keywords = ["astro", "rasi", "vijay takkar", "zee thirai"]
for key, data in DB_ARUN.items():
    # Check if any wanted keyword is in the channel name
    if any(w in key for w in wanted_keywords):
        # Determine Group
        grp = "Tamil Extra"
        if "cricket" in key or "sports" in key:
            grp = "Sports Extra"
            
        final_lines.append(f'#EXTINF:-1 group-title="{grp}" tvg-logo="{data["logo"]}",{data["name"]}')
        final_lines.append(data['link'])

# --- Step D: Live Events ---
print("\nAdding Live Events...")
def add_live(url):
    db = parse_m3u("LIVE", url)
    for key, data in db.items():
        final_lines.append(f'#EXTINF:-1 group-title="Live Events" tvg-logo="{data["logo"]}",{data["name"]}')
        final_lines.append(data['link'])

add_live(URL_FANCODE)
add_live(URL_SONY_LIVE)
add_live(URL_ZEE_LIVE)

# --- Step E: Manual (Youtube) ---
print("\nAdding Manual/Youtube...")
if os.path.exists(youtube_file):
    with open(youtube_file, "r") as f:
        yt_lines = f.readlines()
    
    current_title = ""
    current_logo = ""
    for line in yt_lines:
        line = line.strip()
        if line.lower().startswith("title:"):
            current_title = line.split(":", 1)[1].strip()
        elif line.lower().startswith("logo:"):
            current_logo = line.split(":", 1)[1].strip()
        elif line.lower().startswith("link:") or line.startswith("http"):
            link = line.split(":", 1)[1].strip() if "link:" in line.lower() else line
            if current_title:
                final_lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{current_logo}",{current_title}')
                final_lines.append(link)
                current_title = "" # Reset

# --- Step F: Save ---
with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n".join(final_lines))

print(f"\n✅ DONE! Saved to {output_file}")
