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

# 1. REMOVAL LIST (Strictly delete these)
REMOVE_KEYWORDS = [
    "sony ten", "sonyten", "sony sports ten", 
    "star sports 1", "star sports 2", # SD versions
    "star sports 1 kannada hd" # REMOVED as per request (playing SD content)
]

# 2. CHANNELS TO FORCE FROM BACKUP
FORCE_BACKUP_KEYWORDS = [
    "star", "zee", "vijay", "asianet", "suvarna", "maa", "hotstar", "sony", "set", "sab",
    "nick", "cartoon", "pogo", "disney", "hungama", "sonic", "discovery", "nat geo", 
    "history", "tlc", "animal planet", "travelxp", "bbc earth", "movies now", "mnx", "romedy", "mn+", "pix",
    "&pictures", "sports", "ten"
]

# 3. NAME OVERRIDES (Left: YOUR Template Name | Right: BACKUP Source Name)
NAME_OVERRIDES = {
    # --- STAR SPORTS FIXES ---
    "star sports 1 hd": "Star Sports HD1",
    "star sports 2 hd": "Star Sports HD2",
    "star sports 1 hindi hd": "Star Sports HD1 Hindi",
    
    # --- REBRANDING FIXES (JioStar 2025) ---
    # Maps your Template Name -> The actual Source Name
    "star sports 2 hindi hd": "Sports18 1 HD",  # Renamed & Fixed mapping
    "star sports 2 tamil hd": "Star Sports 2 Tamil HD", # Added Explicitly
    "star sports 2 telugu hd": "Star Sports 2 Telugu HD",
    "star sports 2 kannada hd": "Star Sports 2 Kannada HD",
    
    # --- STAR SPORTS SELECT ---
    "star sports select 1 hd": "Star Sports Select HD1",
    "star sports select 2 hd": "Star Sports Select HD2",
    
    # --- INFOTAINMENT & OTHERS ---
    "nat geo hd": "National Geographic HD",
    "nat geo wild hd": "Nat Geo Wild HD",
    "discovery hd world": "Discovery HD",
    "history tv18 hd": "History TV18 HD",
    "cartoon network hd+ english": "Cartoon Network HD+",
    "nick hd+": "Nick HD+",
    "star movies hd": "Star Movies HD",
    "sony pix hd": "Sony Pix HD",
    "zee tamil": "Zee Tamil HD"
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
    name = name.replace("sports18", "sports 18") 
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
        if "science
