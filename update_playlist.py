import requests

# URLs
template_file = "template.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/refs/heads/main/data/fancode.m3u"
output_file = "playlist.m3u"

def update_playlist():
    # 1. Read the Static Template
    try:
        with open(template_file, "r") as f:
            template_content = f.read()
    except FileNotFoundError:
        print("Error: template.m3u not found!")
        return

    # 2. Fetch the Dynamic Fancode List
    try:
        response = requests.get(fancode_url)
        response.raise_for_status()
        fancode_content = response.text
        
        # Remove the top #EXTM3U line from fancode if it exists to avoid duplicates
        lines = fancode_content.splitlines()
        if lines[0].startswith("#EXTM3U"):
            lines = lines[1:]
        fancode_clean = "\n".join(lines)
        
    except Exception as e:
        print(f"Error fetching Fancode: {e}")
        fancode_clean = ""

    # 3. Combine and Save
    final_playlist = template_content + "\n" + fancode_clean
    
    with open(output_file, "w") as f:
        f.write(final_playlist)
    
    print("Playlist updated successfully!")

if __name__ == "__main__":
    update_playlist()
