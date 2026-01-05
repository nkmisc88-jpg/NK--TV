import requests
import re
import datetime
import os
import sys
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.googl.logging import LogType

# ==========================================
# CONFIGURATION
# ==========================================
OUTPUT_FILE = "pocket_playlist.m3u"
YOUTUBE_FILE = "youtube.txt"
POCKET_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html" 

# [KEEP YOUR EXISTING GROUP MAPPINGS HERE - PASTED FOR BREVITY]
# ... (Paste your Move/Delete lists here if they are missing) ...
BAD_KEYWORDS = ["fashion", "overseas", "yupp", "usa", "pluto", "sun nxt", "sunnxt", "jio specials hd"]

DEFAULT_LOGO = "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Globe_icon.svg/1200px-Globe_icon.svg.png"

def get_real_m3u8_using_browser(url):
    """
    Launches a headless Chrome browser to capture network traffic
    and find the hidden .m3u8 link.
    """
    print(f"   🚀 Launching Browser for: {url}")
    
    # 1. Setup Chrome Options (Headless = Invisible)
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Enable Performance Logging (To see network traffic)
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = None
    found_m3u8 = None

    try:
        # 2. Start Browser
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 3. Visit the Page
        driver.get(url)
        time.sleep(8) # Wait 8 seconds for JS to generate the token
        
        # 4. Scan Network Logs
        logs = driver.get_log("performance")
        for entry in logs:
            message = json.loads(entry["message"])["message"]
            if "Network.requestWillBeSent" in message["method"]:
                request_url = message["params"]["request"]["url"]
                
                # Look for the .m3u8 link
                if ".m3u8" in request_url:
                    print(f"      🎯 Found hidden link: {request_url[:50]}...")
                    found_m3u8 = request_url
                    break # Stop after finding the first one
                    
    except Exception as e:
        print(f"   ⚠️ Browser Error: {e}")
    finally:
        if driver: driver.quit()

    if found_m3u8:
        # Add User-Agent to make it play
        return f"{found_m3u8}|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    return None

# [KEEP YOUR EXISTING HELPER FUNCTIONS]
def get_group_and_name(line):
    grp_match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
    group = grp_match.group(1).strip() if grp_match else ""
    name = line.split(",")[-1].strip()
    return group, name

def should_keep_channel(group, name):
    check_str = (group + " " + name).lower()
    for bad in BAD_KEYWORDS:
        if bad in check_str: return False 
    return True

def get_clean_id(name):
    name = name.lower().replace("hd", "").replace(" ", "").strip()
    return re.sub(r'[^a-z0-9]', '', name)

def fetch_live_events(url):
    # [Paste your existing fetch_live_events code here]
    lines = []
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code == 200:
            content = r.text.splitlines()
            for line in content:
                line = line.strip()
                if not line: continue
                if line.startswith("#EXTM3U"): continue
                if line.startswith("#EXTINF"):
                    line = re.sub(r'group-title="([^"]*)"', '', line)
                    line = re.sub(r'(#EXTINF:[-0-9]+)', r'\1 group-title="Live Events"', line)
                    lines.append(line)
                elif not line.startswith("#"):
                    lines.append(line)
    except: pass
    return lines

def parse_youtube_txt():
    print("   ...Reading youtube.txt")
    lines = []
    if not os.path.exists(YOUTUBE_FILE): return []
        
    try:
        with open(YOUTUBE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            file_lines = f.readlines()
        
        current_title = "Unknown Channel"
        current_logo = DEFAULT_LOGO
        
        for line in file_lines:
            line = line.strip()
            if not line: continue
            lower_line = line.lower()
            
            if lower_line.startswith("title"):
                parts = line.split(":", 1)
                if len(parts) > 1: current_title = parts[1].strip()
            
            elif lower_line.startswith("logo"):
                parts = line.split(":", 1)
                if len(parts) > 1: current_logo = parts[1].strip()
            
            elif "http" in lower_line:
                url_start = lower_line.find("http")
                url = line[url_start:].strip()
                url = url.split(" ")[0]

                # LOGIC: If it's NOT a direct link and NOT YouTube, use Browser
                if "youtube" not in lower_line and not url.endswith(".m3u8"):
                    final_link = get_real_m3u8_using_browser(url)
                    if final_link:
                        lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{current_logo}",{current_title}')
                        lines.append(final_link)
                        print(f"   ✅ Browser Found Stream: {current_title}")
                    else:
                        print(f"   ❌ Browser Failed: {current_title}")

                else:
                     lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{current_logo}",{current_title}')
                     if "|" not in url: url += "|User-Agent=Mozilla/5.0"
                     lines.append(url)

                current_title = "Unknown Channel"
                current_logo = DEFAULT_LOGO

    except Exception as e:
        print(f"   ❌ Error reading youtube.txt: {e}")
    return lines

def main():
    print("📥 Downloading Source Playlist...")
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines = ["#EXTM3U"]
    final_lines.append(f"# Last Updated: {ist_now.strftime('%Y-%m-%d %H:%M:%S IST')}")
    final_lines.append("http://0.0.0.0")

    try:
        r = requests.get(POCKET_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        source_lines = r.text.splitlines()
    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)

    # [Paste the rest of your Main function logic here (HD scan, grouping, etc.)]
    # ... (Keep the exact same logic as before for standard channels) ...
    
    # FOR NOW, I am putting just the essential part to make it run:
    seen_channels = set()
    for line in source_lines:
        # ... (Your existing loop logic) ...
        # If you need me to paste the FULL 200 lines again let me know, 
        # but you can just copy the 'parse_youtube_txt' and 'get_real_m3u8_using_browser' functions
        # and replace them in your current script.
        pass 

    print("📥 Adding Custom Links...")
    final_lines.extend(parse_youtube_txt())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    print(f"\n✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
