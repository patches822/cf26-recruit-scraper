import csv
import logging
import os
import re
from typing import Dict, Tuple

import cv2
import easyocr
import gspread
import keyboard
import mss
import mss.tools
import numpy as np
import winsound
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATION ---
MONITOR_NUMBER = 2  # Change to 1, 2, or 3 based on your setup

# Centralized Region of Interest (ROI) Configuration
# Format: (y, h, x, w) -> Top, Height, Left, Width relative to monitor
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
    "basic_info":    (15, 240, 590, 1770)  # Wider crop for fallback
}

# Adjust these offsets if the game window isn't full screen
GLOBAL_OFFSETS = {
    "top": 370,
    "left": 1207,
    "width": 2400,
    "height": 1440
}

# --- BASIC INFO HEADERS ---
BASIC_INFO_HEADERS = ["NAME", "POSITION", "ARCHETYPE", "STARS", "GEM", "HEIGHT", "WEIGHT", "CLASS", "HOMETOWN"]

# --- ATTRIBUTE MAPPING ---
# List of all possible attribute columns in the Google Sheet (Must match Row 1)
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

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class Recruit:
    """Data class to hold recruit information."""
    def __init__(self, name, position, archetype, star_rating, gem_status, height, weight, recruit_class, hometown, attributes):
        self.name = name
        self.position = position
        self.archetype = archetype
        self.star_rating = star_rating
        self.gem_status = gem_status
        self.height = height
        self.weight = weight
        self.recruit_class = recruit_class
        self.hometown = hometown
        self.attributes = attributes
        
    def to_row(self) -> list:
        """Converts recruit data into a row matching the ATTRIBUTE_HEADERS order."""
        # 1. Basic Info Columns
        row = [
            self.name,
            self.position,
            self.archetype,
            self.star_rating,
            self.gem_status,
            self.height,
            self.weight,
            self.recruit_class,
            self.hometown
        ]

        # 2. Dynamic Attribute Columns
        # We look through ALL possible headers. If the recruit has it, we add the value.
        # If not, we add an empty string "".
        for header in ATTRIBUTE_HEADERS:
            # We standardize keys: "Short Accuracy" (sheet) -> "SHORT ACCURACY" (dict)
            key = header.upper()
            val = self.attributes.get(key, "")
            row.append(val)
            
        return row


class RecruitScraper:
    def __init__(self, monitor_num: int):
        self.monitor_num = monitor_num
        
        # 1. Run the Startup Menu
        (self.save_mode, 
         self.debug_mode, 
         self.keep_screenshots, 
         self.use_sounds) = self._startup_menu()
        
        # 2. Initialize Resources
        logger.info("Initializing OCR Reader (this may take a moment)...")
        self.reader = easyocr.Reader(['en'], gpu=True) # Set gpu=False if you don't have NVIDIA

        self.sheet = None
        if self.save_mode == "SHEETS":
            self.sheet = self._connect_google_sheets()

    def _startup_menu(self) -> Tuple[str, bool, bool]:
        """Consolidated menu to configure the session."""
        print("\n" + "═"*40)
        print("       COLLEGE FOOTBALL RECRUIT SCRAPER")
        print("═"*40)
        
        # [1] Save Mode
        print("\n[1] SELECT SAVE MODE:")
        print("    (1) Google Sheets")
        print("    (2) Local CSV File")
        save_choice = input("    Choice: ").strip()
        save_mode = "SHEETS" if save_choice == '1' else "CSV"

        # [2] Debug Mode
        print("\n[2] ENABLE DEBUG WINDOWS?")
        print("    (y) Yes | (n) No")
        debug_choice = input("    Choice: ").strip().lower()
        debug_mode = True if debug_choice == 'y' else False

        # [3] Screenshot Record Keeping
        print("\n[3] SAVE SCREENSHOTS FOR EVERY RECRUIT?")
        print("    (y) Yes - Save to /screenshots folder")
        print("    (n) No  - Data only (Saves space)")
        ss_choice = input("    Choice: ").strip().lower()
        keep_screenshots = True if ss_choice == 'y' else False

        # [4] Sound Alerts
        print("\n[4] ENABLE AUDIBLE ALERTS (BEEPS)?")
        print("    (y) Yes | (n) No")
        sound_choice = input("    Choice: ").strip().lower()
        use_sounds = True if sound_choice == 'y' else False

        print("\n" + "═"*40)
        return save_mode, debug_mode, keep_screenshots, use_sounds
        
    def _connect_google_sheets(self):
        """Connects to Google Sheets API."""
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
            client = gspread.authorize(creds)
            sheet = client.open("CFB26_Recruits").sheet1
            logger.info("Connected to Google Sheets successfully.")
            return sheet
        except Exception as e:
            logger.error(f"Google Sheets connection failed: {e}")
            logger.info("Defaulting to CSV mode for this session.")
            return None
        
    def _save_to_csv(self, row_data):
        """Appends a recruit row to a local CSV file."""
        file_name = "recruits_scraped.csv"
        file_exists = os.path.isfile(file_name)
        
        with open(file_name, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                # Header row: Basic Info + Attribute Headers
                headers = BASIC_INFO_HEADERS + ATTRIBUTE_HEADERS
                writer.writerow(headers)
            writer.writerow(row_data)

    def _save_recruit_data(self, recruit: Recruit):
        """Main entry point for saving data based on selected mode."""
        row = recruit.to_row()
        
        if self.save_mode == "SHEETS" and self.sheet:
            try:
                self.sheet.append_row(row)
                logger.info(f"Saved to Google Sheets: {recruit.name}")
            except Exception as e:
                logger.error(f"Error saving to Sheets: {e}. Attempting CSV backup.")
                self._save_to_csv(row)
        else:
            self._save_to_csv(row)
            logger.info(f"Saved to CSV: {recruit.name}")

    def _show_debug(self, title: str, img):
        """Only shows windows if the user opted-in at startup."""
        if self.debug_mode:
            cv2.imshow(title, img)
            cv2.waitKey(0)  # 1ms delay to allow window to render without blocking
            cv2.destroyAllWindows()

    def _validate_recruit_data(self, data: Recruit) -> bool:
        """Validate none of the fields for the recruit are empty."""
        missing_fields = []
        for key, value in data.__dict__.items():
            if key != "attributes" and (value == "Error" or value == ""):
                missing_fields.append(key)

        if len(missing_fields) > 0:
            list_str = ", ".join(map(str, missing_fields))
            logger.error(f"❌ Basic Info Validation Failed: Missing {list_str}")
            return False
        
        if len(data.attributes) != 10:
            logger.error(f"❌ Attributes Validation Failed: Found {len(data.attributes)}/10 attributes for {data.name}.")
            return False
        
        return True

    def _trigger_alert(self, success=True):
        """Plays sound only if use_sounds is enabled; always logs to console."""
        if success:
            logger.info("✅ SCAN SUCCESSFUL")
            if self.use_sounds:
                winsound.Beep(1000, 200)
        else:
            logger.error("⚠️ SCAN FAILED: Data incomplete. Please re-scan.")
            if self.use_sounds:
                winsound.Beep(400, 600)

    def _crop_roi(self, img, roi_key: str):
        """Crops the image based on the ROI_CONFIG key."""
        if roi_key not in ROI_CONFIG:
            logger.warning(f"ROI key '{roi_key}' not found in config.")
            return img
        
        y, h, x, w = ROI_CONFIG[roi_key]
        # Safety check to ensure we don't crop outside image bounds
        if y + h > img.shape[0] or x + w > img.shape[1]:
            logger.warning(f"ROI '{roi_key}' is outside image bounds.")
        
        return img[y:y+h, x:x+w]

    def _clean_value(self, value: str) -> str: 
        d = re.findall(r'\d+', value)
        return d[0] if d else ""

    def extract_text_from_roi(self, img, roi_key: str) -> list:
        """Generic method to crop an area and extract text."""
        roi_img = self._crop_roi(img, roi_key)
        self._show_debug(f"Debug: {roi_key}", roi_img)

        results = self.reader.readtext(roi_img, detail=0)
        
        if not results:
            return ["Error"]
        
        return results
    
    def extract_name(self, img) -> str:
        """Extracts recruit's first and last name."""
        name_data = self.extract_text_from_roi(img, "name")
        if name_data[0] == "Error":
            return "Error"
        else:
            return f"{name_data[0]} {name_data[1]}"
    
    def extract_position(self, img) -> str:
        """Extracts recruit's position."""
        position_data = self.extract_text_from_roi(img, "position")
        if position_data[0] == "Error":
            return "Error"
        else:
            return position_data[1]
    
    def extract_archetype(self, img) -> str:
        """Extracts recruit's archetype."""
        archetype_data = self.extract_text_from_roi(img, "archetype")
        if archetype_data[0] == "Error":
            return "Error"
        elif len(archetype_data) == 2:
            return archetype_data[1]
        else:
            # TODO: Find a better solution for the issue where the Gritty Possession Archetype is only being captured as "Possession"
            # Archetype Data: ['ARCHETYPE', 'Possession', 'Gritty']
            return f"{archetype_data[2]} {archetype_data[1]}"
        
    def extract_recruit_class(self, img) -> str:
        """Extracts recruit's class."""
        recruit_class_data = self.extract_text_from_roi(img, "recruit_class")
        if recruit_class_data[0] == "Error" or len(recruit_class_data) < 2:
            return "Error"
        elif len(recruit_class_data) == 2:
            return recruit_class_data[1]
        else:
            return f"{recruit_class_data[1]} {recruit_class_data[2]}"

    def extract_hometown(self, img) -> str:
        """Extracts recruit's hometown."""
        hometown_data = self.extract_text_from_roi(img, "hometown")

        if hometown_data[0] == "Error" or len(hometown_data) < 2:
            return "Error"
        elif len(hometown_data) == 2:
            return hometown_data[1]
        else:
            return f"{hometown_data[1]}, {hometown_data[2]}"

    def extract_height_weight(self, img) -> Tuple[str, str]:
        """Extracts recruit's height and weight."""
        height_weight_data = self.extract_text_from_roi(img, "height_weight")

        if height_weight_data[0] == "Error" or len(height_weight_data) < 2:
            return "Error", "Error"
        elif len(height_weight_data) == 2:
            # Look for Height (e.g., 6' 5")
            height_match = re.search(r"(\d['\s]+\d+[\"']?)", height_weight_data[1])
            height = height_match.group(1).replace(" ", "") if height_match else ""

            # Look for Weight (e.g., 298) 
            # We specifically look for 3 digits that are NOT part of the height
            weight_match = re.search(r"(\d{3})\s*(?:Ibs|lbs)?", height_weight_data[1])
            weight = weight_match.group(1) if weight_match else ""
        elif len(height_weight_data) == 3:
            height = height_weight_data[1]
            weight = height_weight_data[2]
        else:
            height = height_weight_data[1]
            weight = height_weight_data[3]
        
        return height, weight

    def check_gem_status(self, img) -> str:
        """Detects Green Gem or Red Bust using Color Filtering."""
        roi_img = self._crop_roi(img, "gem_icon")
        
        hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
        
        # Green Mask
        lower_green = np.array([40, 50, 50])
        upper_green = np.array([80, 255, 255])
        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # Red Mask (wrapping around 0-180)
        lower_red1 = np.array([0, 70, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 70, 50])
        upper_red2 = np.array([180, 255, 255])
        red_mask = cv2.bitwise_or(cv2.inRange(hsv, lower_red1, upper_red1), cv2.inRange(hsv, lower_red2, upper_red2))

        # Show debugs for color masks
        if self.debug_mode:
            self._show_debug("Original Gem ROI", roi_img)
            self._show_debug("Gem Mask", green_mask)
            self._show_debug("Bust Mask", red_mask)

        # Threshold check
        if cv2.countNonZero(green_mask) > 150: return "GEM"
        if cv2.countNonZero(red_mask) > 150: return "BUST"
        return "None"

    def extract_attributes(self, img) -> Dict[str, str]:
        """Extracts attributes and maps them to a dictionary."""
        attribute_data = self.extract_text_from_roi(img, "attributes")

        # --- 1. CREATE NORMALIZATION MAP ---
        # This creates a dictionary like: {'SHORTACCURACY': 'SHORT ACCURACY', 'RUNBLOCK': 'RUN BLOCK'}
        # It allows us to match OCR text even if spaces are missing.
        header_map = {h.replace(" ", "").upper(): h for h in ATTRIBUTE_HEADERS}   

        # --- 2. PROCESS LABELS & VALUES ---
        clean_labels = []
        clean_values = []

        for item in attribute_data:
            # Check if it's a Value (contains digits)
            if any(c.isdigit() for c in item):
                val = self._clean_value(item)
                if len(val) == 2: # filter out noise, keep 2-digit stats
                    clean_values.append(val)
            
            # Check if it's a Label (All caps, no digits)
            elif item.isupper() and not item.isdigit() and len(item) > 2:
                # STRIP SPACES from the OCR result to match our map keys
                ocr_key = item.replace(" ", "").upper()
                
                # If the stripped OCR text matches one of our known headers, use the CLEAN header
                if ocr_key in header_map:
                    clean_labels.append(header_map[ocr_key])
                else:
                    # If it's a label we don't recognize (garbage text), ignore it
                    # or append it raw if you want to see errors
                    print(f"Unrecognized attribute label: {item}")
                    pass

        # --- 3. ZIP AND RETURN ---
        # We assume the lists are aligned (Label -> Value order)
        # If the OCR misses a label but sees a value, alignment might drift. 
        # For now, zip is the standard approach.
        logger.info(f"Extracted Attributes: {dict(zip(clean_labels, clean_values))}")
        return dict(zip(clean_labels, clean_values))

    def extract_star_rating(self, img) -> str:
        """Extract recruit's star rating."""
        # 1. Get the Star Area
        roi_img = self._crop_roi(img, "star_rating")
        
        # 2. Convert to Grayscale
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        
        # 3. Threshold: Everything above 200 (bright white) becomes white, else black
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        
        # 4. Find Contours (the shapes of the stars)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        star_count = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            
            # Filter by area: 
            # You'll need to check the 'print' below to see the actual size of your stars
            # Let's assume a star is at least 50 pixels big.
            if area > 50: 
                star_count += 1
        
        # Debugging: See what the script thinks are stars
        if self.debug_mode:
            debug_vis = roi_img.copy()
            cv2.drawContours(debug_vis, contours, -1, (0, 255, 0), 2)
            self._show_debug("Star Detection", debug_vis)
            self._show_debug("Star Threshold", thresh)
            logger.info(f"Star Area Sizes found: {[cv2.contourArea(c) for c in contours if cv2.contourArea(c) > 10]}")

        # Ensure we don't return more than 5
        return min(star_count, 5)

    def process_recruit(self):
        """Main sequence to capture and save a recruit."""
        with mss.mss() as sct:
            mon = sct.monitors[self.monitor_num]
            
            # defined relative to monitor
            capture_region = {
                "top": mon["top"] + GLOBAL_OFFSETS["top"],
                "left": mon["left"] + GLOBAL_OFFSETS["left"],
                "width": GLOBAL_OFFSETS["width"],
                "height": GLOBAL_OFFSETS["height"],
            }

            img_bgr = cv2.imread("screenshots/TE/CHADLOVE.png")
            if img_bgr is None:
                print(f"Could not find image. Make sure it's in the same folder!")
                return

            # screenshot = sct.grab(capture_region)

            # # Always save debug.png for the immediate scan verification
            # mss.tools.to_png(screenshot.rgb, screenshot.size, output="debug.png")
            
            # # Convert to OpenCV format (BGR)
            # img_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2BGR)
            
            logger.info("Scanned recruit. Extracting data...")

            # --- EXTRACT DATA ---
            name = self.extract_name(img_bgr)
            position = self.extract_position(img_bgr)
            archetype = self.extract_archetype(img_bgr)
            recruit_class = self.extract_recruit_class(img_bgr)
            hometown = self.extract_hometown(img_bgr)
            height, weight = self.extract_height_weight(img_bgr)
            gem_status = self.check_gem_status(img_bgr)
            star_rating = self.extract_star_rating(img_bgr)
            attributes = self.extract_attributes(img_bgr)

            recruit = Recruit(
                name=name, position=position, archetype=archetype, 
                star_rating=star_rating, gem_status=gem_status, 
                height=height, weight=weight, recruit_class=recruit_class, 
                hometown=hometown, attributes=attributes
            )

            # --- VALIDATE DATA ---
            if not self._validate_recruit_data(recruit):
                self._trigger_alert(success=False)
                return

            # --- SAVE DATA ---
            self._save_recruit_data(recruit)

            # Success Beep
            self._trigger_alert(success=True)

            # --- OPTIONAL PERMANENT SCREENSHOT ---
            if self.keep_screenshots:
                os.makedirs(f"screenshots/{position}", exist_ok=True)
                # Clean name for filename compatibility
                safe_name = re.sub(r'\W+', '', name) if name else "Unknown"
                filename = f"screenshots/{position}/{safe_name}.png"
                mss.tools.to_png(screenshot.rgb, screenshot.size, output=filename)
                logger.info(f"Screenshot saved: {filename}")

    def run(self):
        """Starts the main listener loop."""
        mode_str = f"SAVE: {self.save_mode} | DEBUG: {'ON' if self.debug_mode else 'OFF'}"
        
        print(f"\n🚀 SCRAPER ACTIVE")
        print(f"   Settings: {mode_str}")
        print(f"   Monitor:  {self.monitor_num}")
        print("-" * 40)
        print("👉 Press 'S' to scrape the current recruit.")
        print("👉 Press 'ESC' to exit the program.")
        print("-" * 40 + "\n")

        keyboard.add_hotkey('s', self.process_recruit)
        keyboard.wait('esc')
        
        if self.debug_mode:
            cv2.destroyAllWindows()
        logger.info("Scraper shut down safely.")


if __name__ == "__main__":
    scraper = RecruitScraper(monitor_num=MONITOR_NUMBER)
    scraper.run()