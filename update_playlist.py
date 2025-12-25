import requests

# Files
template_file = "template.m3u"
output_file = "playlist.m3u"
# CORRECT Raw URL (Removed 'refs/heads')
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

def update_playlist():
    print("Starting Update Process...")

    # 1. Read Template (UTF-8 Enforced)
    try:
        with open(template_file, "r", encoding="utf-8") as f:
            template_content = f.read().strip() # .strip() removes empty lines at end
            print("Template read successfully.")
    except FileNotFoundError:
        print("CRITICAL ERROR: template.m3u not found!")
        exit(1)

    # 2. Fetch Fancode
    fancode_content = ""
    try:
        print(f"Fetching Fancode from: {fancode_url}")
        response = requests.get(fancode_url)
        response.raise_for_status()
        
        # Split lines to clean up
        lines = response.text.splitlines()
        
        # If the first line is #EXTM3U, remove it to avoid duplicates
        if lines and lines[0].startswith("#EXTM3U"):
            lines = lines[1:]
            
        fancode_content = "\n".join(lines)
        print(f"Fancode fetched. Added {len(lines)/2} channels.")
        
    except Exception as e:
        print(f"ERROR fetching Fancode: {e}")
        # We continue even if Fancode fails, so at least JioTV works

    # 3. Save Combined Playlist (UTF-8 Enforced)
    final_content = template_content + "\n\n" + fancode_content
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_content)
    
    print(f"Success! {output_file} updated.")

if __name__ == "__main__":
    update_playlist()
