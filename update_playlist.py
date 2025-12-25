import requests
import re

# ==========================================
# CONFIGURATION
# ==========================================
template_file = "template.m3u"
youtube_file = "youtube.txt"
reference_file = "jiotv_playlist.m3u.m3u8"
output_file = "playlist.m3u"

# SOURCES
base_url = "http://192.168.0.146:5350/live" 
# Backup Source (FakeAll/Jstar)
backup_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# CHANNELS TO FORCE FROM BACKUP
# (If a channel matches these words, look in Backup FIRST)
FORCE_BACKUP_KEYWORDS = [
    "star", "zee", "vijay", "asianet", "suvarna", "maa", "hotstar", "sony", "set", "sab",
    "nick", "cartoon", "pogo", "disney", "hungama", "sonic", "discovery", "nat geo", 
    "history", "tlc", "animal planet", "travelxp", "bbc earth", "movies now", "mnx", "romedy", "mn+", "pix",
    "&pictures"
]

# NAME OVERRIDES (Try these alternates if exact match fails)
NAME_OVERRIDES = {
    # Sony
    "sony ten 4": "sony sports ten 4",
    "sony ten 3": "sony sports ten 3",
    "sony ten 2": "sony sports ten 2",
    "sony ten 1": "sony sports ten 1",
    "sony ten 5": "sony sports ten 5",
    
    # Discovery / Nat Geo
    "nat geo hd": "national geographic",
    "nat geo wild": "nat geo wild",
    "discovery hd world": "discovery channel",
    "history tv18": "history",
    
    # Kids
    "cartoon network hd+ english": "cartoon network",
    "nick hd+": "nick",
    
    # Movies
    "star movies hd": "star movies",
    "sony pix hd": "sony pix",
    "mn+ hd": "mn+",
    "mnx hd": "mnx",
}

# Browser UA
browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
# ==========================================

def clean_name_key(name):
    """Normalizes names."""
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

def get_significant_words(name):
    """Extracts core words for fuzzy matching."""
    name = name.lower()
    # Remove noise words to focus on the unique ID
    name = re.sub(r'\b(hd|sd|tv|channel|network|india|world|english|tamil|hindi|telugu|kannada|movies|cinema)\b', '', name)
    words = re.findall(r'[a-z0-9]+', name)
    return set(words)

def get_forbidden_words(target_name):
    """Context-aware blacklist."""
    t = target_name.lower()
    forbidden = []
    
    if "nat" in t and "wild" not in t: forbidden.append("wild")
    if "discovery" in t:
        if "kids" not in t: forbidden.append("kids")
        if "science" not in t: forbidden.append("science")
        if "turbo" not in t: forbidden.append("turbo")
    
    # Sports Numbering Protection
    if "sports" in t or "ten" in t:
        for n in ["1", "2", "3", "4", "5"]:
            if n in t:
                # If searching for "1", forbid 2,3,4,5
                forbidden.extend([x for x in ["1", "2", "3", "4", "5"] if x != n])
                break
                
    return forbidden

def fuzzy_match_logic(target_name, map_keys):
    """Tries to find a match using word logic."""
    target_words = get_significant_words(target_name)
    if not target_words: return None
    
    bad_words = get_forbidden_words(target_name)
    
    for key in map_keys:
        key_lower = key.lower()
        
        # Blacklist Check
        if any(bad in key_lower for bad in bad_words):
            continue
            
        # Word Subset Check
        key_words = set(re.findall(r'[a-z0-9]+', key_lower))
        
        # Mapping tweaks for fuzzy
        if "national" in key_words and "geographic" in key_words:
            key_words.add("nat"); key_words.add("geo")
        if "&pictures" in key_lower:
            key_words.add("and"); key_words.add("pictures")

        if target_words.issubset(key_words):
            return key
            
    return None

def find_best_backup_link(original_name, backup_map):
    """Try 1: Exact, Try 2: Mapped, Try 3: Fuzzy"""
    clean_orig = clean_name_key(original_name)
    
    # 1. Exact Match
    if clean_orig in backup_map:
        return backup_map[clean_orig]
        
    # 2. Mapped Match (Overrides)
    clean_mapped = clean_name_key(NAME_OVERRIDES.get(clean_orig, "")) # Check if normalized key is in overrides?
    # Better: Check original name against overrides dict keys
    for k, v in NAME_OVERRIDES.items():
        if clean_name_key(k) == clean_orig:
            clean_mapped = clean_name_key(v)
            if clean_mapped in backup_map:
                return backup_map[clean_mapped]
    
    # 3. Fuzzy Match
    fuzzy_key = fuzzy_match_logic(original_name, backup_map.keys())
    if fuzzy_key:
        return backup_map[fuzzy_key]
        
    return None

def load_local_map(ref_file):
    id_map = {}
    try:
        with open(ref_file, "r", encoding="utf-8") as f:
            content = f.read()
        pattern = r'tvg-id="(\d+)".*?tvg-name="([^"]+)"'
        matches = re.findall(pattern, content)
        for ch_id, ch_name in matches:
            key = clean_name_key(ch_name)
            id_map[key] = ch_id
        print(f"✅ Local JioTV: Found {len(id_map)} channels.")
        return id_map
    except FileNotFoundError:
        return {}

def fetch_backup_map(url):
    block_map = {}
    try:
        print("🌍 Fetching FakeAll Source...")
        response = requests.get(url, headers={"User-Agent": browser_ua}, timeout=20)
        if response.status_code == 200:
            lines = response.text.splitlines()
            current_block = []
            current_name = ""
            for line in lines:
                line = line
