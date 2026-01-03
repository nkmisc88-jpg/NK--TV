import requests
import datetime
import os
import sys

# ==========================================
# CONFIGURATION
# ==========================================
OUTPUT_FILE = "pocket_playlist.m3u"
YOUTUBE_FILE = "youtube.txt"
POCKET_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html" 

def main():
    print("📥 Downloading Source Playlist...")
    try:
        r = requests.get(POCKET_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if r.status_code != 200:
            print(f"❌ Error: Status {r.status_code}")
            sys.exit(1)
        
        # Get the raw text exactly as it is
        raw_content = r.text
        print(f"✅ Downloaded {len(raw_content.splitlines())} lines.")

    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)

    # Prepare final content
    # We add a timestamp comment at the top so GitHub sees a "change" and allows the commit.
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    header = f"#EXTM3U\n# Last Updated: {ist_now.strftime('%Y-%m-%d %H:%M:%S IST')}\n"
    
    # Remove the first #EXTM3U from the source to avoid double headers
    clean_content = raw_content.replace("#EXTM3U", "", 1).strip()
    
    final_content = header + clean_content

    # Append Temporary Channels (if file exists)
    if os.path.exists(YOUTUBE_FILE):
        print("   + Appending youtube.txt")
        with open(YOUTUBE_FILE, "r") as f:
            yt_lines = f.read()
            final_content += "\n" + yt_lines

    # Save to file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final_content)
    
    print(f"\n✅ DONE. Saved exactly as source to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
