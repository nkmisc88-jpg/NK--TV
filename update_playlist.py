import requests

# 1. SETUP
# ==========================================
template_file = "template.m3u"
output_file = "playlist.m3u"
# FIXED URL (This is the specific fix for the "88 channels" error)
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
# ==========================================

def update_playlist():
    print("--- STARTING UPDATE ---")

    # 2. READ STATIC CHANNELS (JioTV + YouTube)
    try:
        with open(template_file, "r", encoding="utf-8") as f:
            static_content = f.read().strip()
        print("Template loaded successfully.")
    except FileNotFoundError:
        print("ERROR: template.m3u not found. Please create it!")
        return

    # 3. FETCH DYNAMIC CHANNELS (Fancode)
    fancode_content = ""
    try:
        print(f"Downloading Fancode from: {fancode_url}")
        response = requests.get(fancode_url)
        response.raise_for_status()
        
        # Clean up the Fancode list (remove duplicate #EXTM3U tags)
        lines = response.text.splitlines()
        clean_lines = [line for line in lines if not line.startswith("#EXTM3U")]
        fancode_content = "\n".join(clean_lines)
        print(f"Fancode downloaded. Found {len(clean_lines)/2} channels.")

    except Exception as e:
        print(f"Warning: Could not download Fancode. Error: {e}")

    # 4. MERGE AND SAVE
    final_playlist = static_content + "\n\n" + fancode_content
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_playlist)
    
    print(f"--- SUCCESS: Saved to {output_file} ---")

if __name__ == "__main__":
    update_playlist()
