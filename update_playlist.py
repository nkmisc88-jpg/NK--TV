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
backup_url = "https://raw.githubusercontent.com/fakeall12398-sketch/JIO_TV/refs/heads/main/jstar.m3u"
fancode_url = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"

# 1. REMOVAL LIST (Strictly delete these)
REMOVE_KEYWORDS = [
    "sony ten", "sonyten", "sony sports ten", 
    "star sports 1", "star sports 2" 
]

# 2. CHANNELS TO FORCE FROM BACKUP
FORCE_BACKUP_KEYWORDS = [
    "star", "zee", "vijay", "asianet", "suvarna", "maa", "hotstar", "sony", "set", "sab",
    "nick", "cartoon", "pogo", "disney", "hungama", "sonic", "discovery", "nat geo", 
    "history", "tlc", "animal planet", "travelxp", "bbc earth", "movies now", "mnx", "romedy", "mn+", "pix",
    "&pictures", "sports", "ten"
]

# 3. NAME OVERRIDES
NAME_OVERRIDES = {
    # Fix: Map your "Star Sports 2 Hindi HD" to the source's "Sports18 1 HD"
    "star sports 2 hindi hd": "Sports18 1 HD",
    
    # Fix: Map your "Star Sports 2 Tamil HD" to source name
    "star sports 2 tamil hd": "Star Sports 2 Tamil HD",
    
    # Standard Mappings
    "star sports 1 hd": "Star Sports HD1",
    "star sports 2 hd": "Star Sports HD2",
    "star sports 1 hindi hd": "Star Sports HD1 Hindi",
    "sony sports ten 1 hd": "sony ten 1",
    "sony sports ten 2 hd": "sony ten 2",
    "sony sports ten 3 hd": "sony ten 3",
    "sony sports ten 4 hd": "sony ten 4",
    "sony sports ten 5 hd": "sony ten 5",
    "nat geo hd": "national geographic",
    "nat geo wild hd": "nat geo wild",
    "discovery hd world": "discovery channel",
    "history tv18 hd": "history",
    "cartoon network hd+ english": "cartoon network",
    "nick hd+": "nick",
    "star movies hd": "star movies",
    "sony pix hd": "sony pix",
}

browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

# ==========================================

def clean_name_key(name):
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return name.lower().strip()

def get_significant_words(name):
    name = name.lower()
    name = name.replace("sports18", "sports 18") 
    name = re.sub(r'\b(hd|sd|tv|channel|network|india|world|english|tamil|hindi|telugu|kannada|movies|cinema)\b', '', name)
    words = re.findall(r'[a-z0-9]+', name)
    return set(words)

def get_forbidden_words(target_name):
    t = target_name.lower()
    forbidden = []
    if "nat" in t and "wild" not in t: forbidden.append("wild")
    if "discovery" in t:
        if "kids" not in t: forbidden.append("kids")
        if "science" not in t: forbidden.append("science")
        if "turbo" not in t: forbidden.append("turbo")
    if "sports" in t or "ten" in t:
        for n in ["1", "2", "3", "4", "5"]:
            if n in t:
                forbidden.extend([x for x in ["1", "2", "3", "4", "5"] if x != n])
                break     
    return forbidden

def fuzzy_match_logic(target_name, map_keys):
    target_words = get_significant_words(target_name)
    if not target_words: return None
    bad_words = get_forbidden_words(target_name)
    
    for key in map_keys:
        key_lower = key.lower()
        key_norm = key_lower.replace("sports18", "sports 18")
        if any(bad in key_lower for bad in bad_words): continue
        key_words = set(re.findall(r'[a-z0-9]+', key_norm))
        if "national" in key_words and "geographic" in key_words:
            key_words.add("nat"); key_words.add("geo")
        if "&pictures" in key_lower:
            key_words.add("and"); key_words.add("pictures")
        if target_words.issubset(key_words):
            return key
    return None

def find_best
