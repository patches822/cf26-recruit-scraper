"""
config.py
Centralized configuration for CFB Recruit Scraper.
Adjust MONITOR_NUMBER and GLOBAL_OFFSETS based on your display settings.
"""

# --- Display Settings ---
MONITOR_NUMBER = 3 

# Global screen crop offsets (top, left, width, height)
# This defines the 'Recruit Card' area on your screen
GLOBAL_OFFSETS = {
    "top": 370,
    "left": 1207,
    "width": 2400,
    "height": 1440
}

# --- Region of Interest (ROI) Definitions ---
# Format: (y, h, x, w) -> Top, Height, Left, Width
# These are relative to the GLOBAL_OFFSETS crop
ROI_CONFIG = {
    "gem_icon":      (287, 90, 13, 90),
    "attributes":    (530, 730, 660, 800),
    "height_weight": (15, 120, 2060, 300),
    "hometown":      (135, 110, 1710, 685),
    "archetype":     (130, 120, 1400, 300),
    "recruit_class": (30, 110, 1710, 340),
    "position":      (15, 120, 1400, 200),
    "name":          (15, 160, 590, 805),
    "star_rating":   (175, 50, 615, 240),
    "basic_info":    (15, 240, 590, 1770)
}

# --- BASIC INFO HEADER MAPPING ---
BASIC_INFO_HEADERS = ["NAME", "POSITION", "ARCHETYPE", "STARS", "GEM", "HEIGHT", "WEIGHT", "CLASS", "HOMETOWN"]

# --- ATTRIBUTE HEADER MAPPING ---
# Maps messy OCR text to clean Spreadsheet headers
# Order matters: This defines the column order in the output sheet
ATTRIBUTE_HEADERS = [
    "SPEED", "ACCELERATION", "AGILITY", "CHANGE OF DIRECTION", "STRENGTH", "AWARENESS", 
    "CARRYING", "BC VISION", "BREAK TACKLE", "TRUCKING", "STIFF ARM", "SPIN MOVE", 
    "JUKE MOVE", "CATCHING", "CATCH IN TRAFFIC", "SPECTACULAR CATCH", "SHORT ROUTE", 
    "MEDIUM ROUTE", "DEEP ROUTE", "RELEASE", "JUMPING", "THROW POWER", "SHORT ACCURACY", 
    "MEDIUM ACCURACY", "DEEP ACCURACY", "THROW ON RUN", "UNDER PRESSURE", "BREAK SACK", 
    "PLAY ACTION", "PASS BLOCK", "PASS BLOCK POWER", "PASS BLOCK FINESSE", "RUN BLOCK", 
    "RUN BLOCK POWER", "RUN BLOCK FINESSE", "LEAD BLOCK", "IMPACT BLOCKING", "PLAY RECOGNITION", 
    "TACKLE", "HIT POWER", "BLOCK SHEDDING", "FINESSE MOVES", "POWER MOVES", "PURSUIT", "MAN COVERAGE", 
    "ZONE COVERAGE", "PRESS", "KICK RETURN", "KICK POWER", "KICK ACCURACY", "STAMINA", "TOUGHNESS", 
    "INJURY", "LONG SNAPPER"
]

# --- Per-Position Expected Attribute Count ---
# All positions currently show 10 attributes on the recruit card.
# Update this map if a position is discovered to show a different number.
POSITION_ATTRIBUTE_COUNT = {
    "QB": 10, "HB": 10, "FB": 10, "WR": 10, "TE": 10,
    "OT": 10, "OG": 10, "C": 10, "DT": 10, "DE": 10,
    "OLB": 10, "MLB": 10, "CB": 10, "SS": 10, "FS": 10,
    "K": 10, "P": 10, "ATH": 10,
}

# --- Star Template Matching ---
STAR_TEMPLATE_PATH = "assets/star_template.png"
STAR_MATCH_THRESHOLD = 0.70  # Confidence threshold for cv2.matchTemplate (TM_CCOEFF_NORMED)

# --- File Paths & API ---
GOOGLE_SHEET_NAME = "CFB26_Recruits"
CREDENTIALS_FILE = "creds.json"
LOCAL_CSV_NAME = "recruits_scraped.csv"
SCREENSHOT_DIR = "screenshots"
REPORTS_DIR = "test_reports"