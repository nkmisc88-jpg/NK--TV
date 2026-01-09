name: Auto-Generate Playlist

on:
  schedule:
    - cron: '*/15 * * * *' # Runs every 15 mins
  workflow_dispatch:
  push:
    paths:
      - 'temp_channels.txt'

permissions:
  contents: write

jobs:
  build-playlist:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Install Requests
        run: pip install requests pytz

      - name: Run Generator Script
        run: |
          cat <<EOF > generate.py
          import requests
          import os
          from datetime import datetime, timedelta, timezone

          # --- CONFIGURATION ---
          OUTPUT_FILE = "index.html"
          TEMP_FILE = "temp_channels.txt"
          
          # 1. THE MAIN SOURCE (Working Source - We copy ALL of it)
          MAIN_SOURCE = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html"

          # 2. ADDITIONAL SOURCES
          YOUTUBE_SOURCE = "https://raw.githubusercontent.com/nkmisc88-jpg/my-youtube-live-playlist/refs/heads/main/playlist.m3u"
          
          EVENT_SOURCES = [
              ("FanCode", "https://raw.githubusercontent.com/byte-capsule/FanCode-Hls-Fetcher/main/Fancode_Live.m3u"),
              ("SonyLIV", "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"),
              ("Zee5 Live", "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u")
          ]

          def get_ist_time():
              ist = timezone(timedelta(hours=5, minutes=30))
              return datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S IST")

          def fetch_m3u_content(url):
              """Downloads M3U and strips the top #EXTM3U tag so we can merge it."""
              try:
                  text = requests.get(url).text
                  lines = text.splitlines()
                  # Remove the first line if it's #EXTM3U (to avoid duplicate headers)
                  if lines and lines[0].startswith("#EXTM3U"):
                      return "\n".join(lines[1:])
                  return text
              except:
                  return ""

          def main():
              # START THE FILE
              final_content = "#EXTM3U x-tvg-url=\"http://botallen.live/epg.xml.gz\"\n"
              final_content += f"# Playlist Updated: {get_ist_time()}\n\n"

              # ---------------------------------------------------------
              # SECTION 1: TEMPORARY CHANNELS (From your txt file)
              # ---------------------------------------------------------
              if os.path.exists(TEMP_FILE):
                  print(">>> Adding Temporary Channels...")
                  with open(TEMP_FILE, "r") as f:
                      for line in f:
                          parts = [p.strip() for p in line.split('|')]
                          if len(parts) >= 3:
                              name, logo, link = parts[0], parts[1], parts[2]
                              final_content += f'#EXTINF:-1 group-title="Temporary" tvg-logo="{logo}", {name}\n'
                              final_content += f'{link}\n'
                  final_content += "\n"

              # ---------------------------------------------------------
              # SECTION 2: LIVE EVENTS & YOUTUBE
              # ---------------------------------------------------------
              print(">>> Adding Live Events...")
              for name, url in EVENT_SOURCES:
                  content = fetch_m3u_content(url)
                  # Optional: Force group-title to "Live Events"
                  content = content.replace('group-title="', 'group-title="Live Events" x-orig-group="')
                  # If no group title exists, add one
                  content = content.replace('#EXTINF:-1 ', '#EXTINF:-1 group-title="Live Events" ')
                  final_content += content + "\n"

              print(">>> Adding YouTube...")
              yt_content = fetch_m3u_content(YOUTUBE_SOURCE)
              yt_content = yt_content.replace('#EXTINF:-1 ', '#EXTINF:-1 group-title="YouTube" ')
              final_content += yt_content + "\n"

              # ---------------------------------------------------------
              # SECTION 3: THE MAIN SOURCE (1000+ Channels)
              # ---------------------------------------------------------
              print(">>> Adding Main Channel List (Arunjunan20)...")
              main_content = fetch_m3u_content(MAIN_SOURCE)
              final_content += main_content

              # ---------------------------------------------------------
              # WRITE OUTPUT
              # ---------------------------------------------------------
              with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                  f.write(final_content)
              
              print(f"Success! Playlist created with IST Time: {get_ist_time()}")

          if __name__ == "__main__":
              main()
          EOF
          
          python generate.py

      - name: Commit & Push
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add index.html
          if git diff --cached --quiet; then
            echo "➡️ No changes detected"
            exit 0
          fi
          git commit -m "Merged Playlist Update"
          git push origin main