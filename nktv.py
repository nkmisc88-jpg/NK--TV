import requests
import os
import re
import datetime

# --- CONFIG ---
OUTPUT_FILE = "nktv.m3u"
TEMP_CHANNELS_FILE = "temporary_channels.txt"
SRC_FAKEALL = "https://raw.githubusercontent.com/ForceGT/Discord-IPTV/master/playlist.m3u"
SRC_ARUNJUNAN = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html"
SRC_EXTRAS = [
    ("Live Events", "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"),
    ("Live Events", "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"),
    ("Live Events", "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"),
    ("YouTube", "https://raw.githubusercontent.com/nkmisc88-jpg/my-youtube-live-playlist/refs/heads/main/playlist.m3u")
]
STD_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DL_HEADERS = {"User-Agent": STD_USER_AGENT}

# --- MASTER LIST (ALIASES) ---
# Format: "key": (["alias1", "alias2"], "Display Name", "Group")
MASTER_CHANNELS = {
    "suntvhd": (["sun tv hd", "suntv hd"], "Sun TV HD", "Tamil HD"),
    "ktvhd": (["ktv hd"], "KTV HD", "Tamil HD"),
    "sunmusichd": (["sun music hd"], "Sun Music HD", "Tamil HD"),
    "starvijayhd": (["star vijay hd", "vijay hd"], "Star Vijay HD", "Tamil HD"),
    "ss1tamilhd": (["star sports 1 tamil hd", "ss1 tamil hd", "sports18 1 hd"], "Star Sports 1 Tamil HD", "Sports HD"),
    "ss1hindihd": (["star sports 1 hindi hd", "ss1 hindi hd", "sports18 1"], "Star Sports 1 Hindi HD", "Sports HD"),
    "ss1hd": (["star sports 1 hd", "ss1 hd"], "Star Sports 1 HD", "Sports HD"),
    "ss2hd": (["star sports 2 hd", "ss2 hd"], "Star Sports 2 HD", "Sports HD"),
    # ... (Full list in previous chat)
}

# --- FUNCTIONS ---
def clean_name(name): return re.sub(r'[^a-z0-9]', '', name.lower())

def fetch_m3u_entries(url):
    try:
        r = requests.get(url, headers=DL_HEADERS, timeout=15)
        if r.status_code != 200: return []
        entries = []
        for line in r.text.splitlines():
            if line.startswith("#EXTINF"):
                logo = re.search(r'tvg-logo="([^"]*)"', line)
                current = {"name": line.split(",")[-1].strip(), "logo": logo.group(1) if logo else "", "raw": line}
            elif line.startswith("http"):
                current["url"] = line.strip()
                entries.append(current)
        return entries
    except: return []

def search_source(aliases, data):
    for entry in data:
        clean = clean_name(entry['name'])
        for alias in aliases:
            if clean_name(alias) in clean: return entry
    return None

def main():
    print("Starting NKTV...")
    lines = ["#EXTM3U", f"# Updated: {datetime.datetime.utcnow()}"]
    
    # 1. Get Sources
    fakeall = fetch_m3u_entries(SRC_FAKEALL)
    arunjunan = fetch_m3u_entries(SRC_ARUNJUNAN)
    
    # 2. Process Master List
    for k, (aliases, name, group) in MASTER_CHANNELS.items():
        entry = search_source(aliases, fakeall)
        src = "fakeall"
        if not entry:
            entry = search_source(aliases, arunjunan)
            src = "arunjunan"
            
        if entry:
            url = entry['url']
            if src == "fakeall" and "|" not in url: url += f"|User-Agent={STD_USER_AGENT}"
            lines.append(f'#EXTINF:-1 group-title="{group}" tvg-logo="{entry["logo"]}",{name}')
            lines.append(url)
        else:
            print(f"Missing: {name}")

    # 3. Add Extras
    for group, url in SRC_EXTRAS:
        for e in fetch_m3u_entries(url):
            url = e['url']
            if "|" not in url: url += f"|User-Agent={STD_USER_AGENT}"
            lines.append(f'#EXTINF:-1 group-title="{group}",{e["name"]}')
            lines.append(url)

    with open(OUTPUT_FILE, "w") as f: f.write("\n".join(lines))
    print("Done.")

if __name__ == "__main__": main()
