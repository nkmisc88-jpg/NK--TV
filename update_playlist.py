import requests
import re

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"      # Your organized list (Groups, Names)
reference_file = "jiotv_playlist.m3u.m3u8" # The file with IDs (Upload this to repo!)
output_file = "playlist.m3u"        # The final result
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
base_url = "http://192.168.0.146:5350/live"  # Your Local Server IP & Port
# ==========================================

def load_id_map(ref_file):
    """Reads the reference file and creates a Name -> ID map."""
    id_map = {}
    try:
        with open(ref_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Regex to find tvg-id (the number) and tvg-name (the name)
        # Looking for: #EXTINF:-1 tvg-id="896" tvg-name="Sun TV HD"
        matches = re.findall(r'tvg-id="(\d+)".*?tvg-name="([^"]+)"', content)
        
        for ch_id, ch_name in matches:
            id_map[ch_name.strip()] = ch_id
            
        print(f"Loaded {len(id_map)} channels from reference file.")
        return id_map
    except FileNotFoundError:
        print(f"CRITICAL ERROR: {ref_file} not found. Upload it to GitHub!")
        return {}

def update_playlist():
    print("--- STARTING SMART UPDATE ---")
    
    # 1. Load the Map (Name -> ID)
    channel_map = load_id_map(reference_file)
    if not channel_map:
        return

    # 2. Process Template (Your Master List)
    final_lines = []
    try:
        with open(template_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            line = line.strip()
            
            # If it's an EXTINF line, try to find the channel name
            if line.startswith("#EXTINF"):
                final_lines.append(line)
                
                # Extract channel name (everything after the last comma)
                # Example: ... group-title="Tamil HD",Sun TV HD
                channel_name = line.split(",")[-1].strip()
                
                # Check if we have an ID for this name
                if channel_name in channel_map:
                    mapped_id = channel_map[channel_name]
                    # Create the new correct link
                    new_link = f"{base_url}/{mapped_id}.m3u8"
                    
                    # Skip the NEXT line in the file (the old wrong link) and add ours
                    # We will handle the link injection in the loop logic
                    continue 
                else:
                    print(f"Warning: No ID found for '{channel_name}'")
            
            # If it's a URL line (doesn't start with #), replace it ONLY if we just processed a mapped channel
            elif not line.startswith("#") and len(final_lines) > 0 and final_lines[-1].startswith("#EXTINF"):
                prev_line = final_lines[-1]
                prev_name = prev_line.split(",")[-1].strip()
                
                if prev_name in channel_map:
                    # We found a map, so we use the generated link
                    mapped_id = channel_map[prev_name]
                    final_lines.append(f"{base_url}/{mapped_id}.m3u8")
                else:
                    # No map found, keep original link (or it might be YouTube)
                    final_lines.append(line)
            
            # Keep other lines (like top #EXTM3U)
            elif line.startswith("#"):
                final_lines.append(line)

        print("Template processed and IDs mapped.")

    except FileNotFoundError:
        print(f"ERROR: {template_file} not found!")
        return

    # 3. Fetch Fancode (Dynamic)
    fancode_content = ""
    try:
        print(f"Fetching Fancode...")
        response = requests.get(fancode_url)
        if response.status_code == 200:
            f_lines = response.text.splitlines()
            # Remove header to avoid duplicate #EXTM3U
            if f_lines and f_lines[0].startswith("#EXTM3U"):
                f_lines = f_lines[1:]
            fancode_content = "\n".join(f_lines)
            print("Fancode merged.")
    except Exception as e:
        print(f"Fancode Error: {e}")

    # 4. Save Final Playlist
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
        f.write("\n\n" + fancode_content)
    
    print(f"--- SUCCESS: {output_file} created successfully ---")

if __name__ == "__main__":
    update_playlist()
