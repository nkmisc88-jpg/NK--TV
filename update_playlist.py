import requests
import re

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"
reference_file = "jiotv_playlist.m3u.m3u8"
output_file = "playlist.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
base_url = "http://192.168.0.146:5350/live" 
# ==========================================

def load_reference_ids(ref_file):
    id_map = {}
    try:
        with open(ref_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Capture ID and Name
        pattern = r'tvg-id="(\d+)".*?tvg-name="([^"]+)"'
        matches = re.findall(pattern, content)
        
        for ch_id, ch_name in matches:
            # Store as lowercase and stripped for better matching
            clean_name = ch_name.strip().lower()
            id_map[clean_name] = ch_id
            
        print(f"✅ Reference Loaded: {len(id_map)} channels.")
        return id_map
    except FileNotFoundError:
        print(f"❌ CRITICAL ERROR: '{ref_file}' not found.")
        return {}

def update_playlist():
    print("--- STARTING SMART UPDATE ---")
    
    # 1. Load Map
    channel_map = load_reference_ids(reference_file)
    if not channel_map: return

    # 2. Process Template
    final_lines = ["#EXTM3U x-tvg-url=\"http://192.168.0.146:5350/epg.xml.gz\""]
    missing_channels = []

    try:
        with open(template_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            line = line.strip()
            
            if line.startswith("#EXTINF"):
                # Get name from template (everything after last comma)
                original_name = line.split(",")[-1].strip()
                lookup_name = original_name.lower()
                
                # CHECK 1: Is it in the JioTV Map?
                if lookup_name in channel_map:
                    # Success! Found the ID.
                    final_lines.append(line)
                    final_lines.append(f"{base_url}/{channel_map[lookup_name]}.m3u8")
                    
                # CHECK 2: Is it a manual YouTube link? (Check next line)
                elif i + 1 < len(lines) and "youtube.com" in lines[i+1]:
                    # Keep YouTube lines exactly as is
                    final_lines.append(line)
                    final_lines.append(lines[i+1].strip())
                    
                # FAILURE: It's a placeholder line but we couldn't find the ID
                elif i + 1 < len(lines) and "http://placeholder" in lines[i+1]:
                    missing_channels.append(original_name)
                
                # Catch-all: Keep other manual links
                elif i + 1 < len(lines) and not lines[i+1].startswith("#"):
                     final_lines.append(line)
                     final_lines.append(lines[i+1].strip())

    except FileNotFoundError:
        print(f"❌ ERROR: {template_file} not found!")
        return

    # 3. Add Fancode
    try:
        response = requests.get(fancode_url)
        if response.status_code == 200:
            f_lines = response.text.splitlines()
            if f_lines and f_lines[0].startswith("#EXTM3U"): f_lines = f_lines[1:]
            final_lines.append("\n" + "\n".join(f_lines))
            print("✅ Fancode merged.")
    except:
        print("⚠️ Fancode failed.")

    # 4. Save
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print(f"🎉 SUCCESS! Playlist created.")
    
    if missing_channels:
        print("\n⚠️ WARNING: The following channels were REMOVED because no ID was found:")
        for ch in missing_channels:
            print(f"   - {ch}")
        print("👉 Check the spelling in your jiotv_playlist file!")

if __name__ == "__main__":
    update_playlist()
