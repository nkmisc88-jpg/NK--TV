import re

# ================= CONFIGURATION =================
INPUT_FILE = "drm.txt"
OUTPUT_FILE = "ready_for_youtube.txt"

# Default headers to ensure playback works (StarzPlay/Jio often need these)
DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DEFAULT_REF = "https://starzplayarabia.com/" 
# =================================================

def parse_drm_file():
    print(f"Reading from {INPUT_FILE}...")
    
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"❌ Error: {INPUT_FILE} not found. Please create it first.")
        return

    output_lines = []
    
    # Temporary variables to hold channel info
    current_key = ""
    current_logo = ""
    current_title = ""
    current_url = ""

    for line in lines:
        line = line.strip()
        if not line: continue

        # 1. Extract License Key
        if "license_key=" in line:
            # key is usually after the equals sign
            parts = line.split("license_key=")
            if len(parts) > 1:
                current_key = parts[1].strip()

        # 2. Extract Title and Logo
        elif line.startswith("#EXTINF"):
            # Extract Logo
            logo_match = re.search(r'tvg-logo="([^"]*)"', line)
            if logo_match:
                current_logo = logo_match.group(1)
            
            # Extract Title (everything after the comma)
            title_parts = line.split(",")
            if len(title_parts) > 1:
                current_title = title_parts[-1].strip()

        # 3. Extract URL (Lines that are not comments/tags)
        elif not line.startswith("#"):
            current_url = line
            
            # --- FORMATTING THE ENTRY ---
            if current_url and current_title:
                # Build the headers string
                headers = f"User-Agent={DEFAULT_UA}&Referer={DEFAULT_REF}"
                
                # Append clearkey if found
                if current_key:
                    headers += f"&clearkey={current_key}"
                
                # Create the formatted block for youtube.txt
                output_lines.append(f"Title: {current_title}")
                if current_logo:
                    output_lines.append(f"Logo: {current_logo}")
                
                # Combine URL + Pipe + Headers
                final_link = f"{current_url}|{headers}"
                output_lines.append(f"Link: {final_link}")
                output_lines.append("") # Empty line for separation

            # Reset variables for next channel
            current_key = ""
            current_logo = ""
            current_title = ""
            current_url = ""

    # Write to output file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    print(f"✅ Conversion Complete! Check '{OUTPUT_FILE}' for your links.")

if __name__ == "__main__":
    parse_drm_file()
