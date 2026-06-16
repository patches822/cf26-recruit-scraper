import cv2
import mss
import numpy as np
import easyocr
import logging
import os
import shutil
import re
import winsound
from datetime import datetime

# Local Imports
from config import ATTRIBUTE_HEADERS, CREDENTIALS_FILE, GLOBAL_OFFSETS, GOOGLE_SHEET_NAME, LOCAL_CSV_NAME, MONITOR_NUMBER, ROI_CONFIG
from src import processor
from src.models import Recruit
from src.output_manager import CSVManager, SheetsManager

logger = logging.getLogger(__name__)

class RecruitScraper:
    def __init__(self, save_mode="CSV", debug_mode=False, use_sounds=True, keep_screenshots=False):
        # 1. Configuration
        self.debug_mode = debug_mode
        self.use_sounds = use_sounds
        self.keep_screenshots = keep_screenshots
        self.monitor_num = MONITOR_NUMBER
        
        # 2. Initialize OCR (Loads model into memory once)
        logger.info("Initializing EasyOCR...")
        self.reader = easyocr.Reader(['en'], gpu=True)

        # 3. Initialize Output Manager (Polymorphism)
        if save_mode == "SHEETS":
            self.output = SheetsManager(GOOGLE_SHEET_NAME, CREDENTIALS_FILE)
        else:
            self.output = CSVManager(LOCAL_CSV_NAME)

    def _capture_screen(self):
        """Captures the defined recruit card region."""
        with mss.mss() as sct:
            screenshot = sct.grab(GLOBAL_OFFSETS)

            # Save debug.png for the immediate scan verification
            mss.tools.to_png(screenshot.rgb, screenshot.size, output="debug.png")

            # Convert to BGR for OpenCV
            return cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2BGR)

    def _clean_value(self, value: str) -> str:
        d = re.findall(r'\d+', value)
        return d[0] if d else ""

    def _normalize_height(self, height: str) -> str:
        match = re.search(r"(\d)'[\s]*(\d+)", height)
        if match:
            return f"{match.group(1)}'{match.group(2)}\""
        return height

    def _save_recruit_screenshot(self, screenshot, name, position):
        """Saves a screenshot with the recruit's name and timestamp."""
        os.makedirs(f"screenshots/{position}", exist_ok=True)
        # Clean name for filename compatibility
        safe_name = re.sub(r'\W+', '', name) if name else "Unknown"
        filename = f"screenshots/{position}/{safe_name}.png"
        shutil.copy("debug.png", filename)

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

    def extract_text(self, img, field_name):
        """Helper to crop and OCR a specific ROI from config."""
        y, h, x, w = ROI_CONFIG[field_name]
        roi = img[y:y+h, x:x+w]

        if self.debug_mode:
            cv2.imshow(f"Debug: {field_name}", roi)
            cv2.waitKey(0)  # Wait for keypress to close debug window
            cv2.destroyAllWindows()

        results = self.reader.readtext(roi, detail=0)

        if not results:
            return ["Error"]
        
        return results
    
    def extract_name(self, img) -> str:
        """Extracts recruit's first and last name."""
        name_data = self.extract_text(img, "name")
        if name_data[0] == "Error":
            return "Error"
        else:
            return f"{name_data[0]} {name_data[1]}"
    
    def extract_position(self, img) -> str:
        """Extracts recruit's position."""
        position_data = self.extract_text(img, "position")
        if position_data[0] == "Error":
            return "Error"
        else:
            return position_data[1]
    
    def extract_archetype(self, img) -> str:
        """Extracts recruit's archetype."""
        y, h, x, w = ROI_CONFIG["archetype"]
        roi = img[y:y+h, x:x+w]

        if self.debug_mode:
            cv2.imshow("Debug: archetype", roi)
            cv2.waitKey(0)  # Wait for keypress to close debug window
            cv2.destroyAllWindows()

        results = self.reader.readtext(roi, detail=1)
        if not results:
            return "Error"

        # Sort tokens by Y coordinate so multi-line archetypes are always top-to-bottom,
        # regardless of the order EasyOCR happens to return them.
        words = sorted(
            [(bbox[0][1], text) for bbox, text, _ in results if text.upper() != "ARCHETYPE"],
            key=lambda x: x[0]
        )
        if not words:
            return "Error"

        result = " ".join(text for _, text in words)

        # OCR reads "/" as "W" or "I", turning "East/West" into "EastWWest" or "EastIWest"
        result = re.sub(r'East(?:/|[WI]+)West', 'East/West', result)
        # OCR occasionally inserts a stray "." between words (e.g. "Edge . Setter")
        result = re.sub(r'\s+\.\s+', ' ', result)
        return result
        
    def extract_recruit_class(self, img) -> str:
        """Extracts recruit's class."""
        recruit_class_data = self.extract_text(img, "recruit_class")
        if recruit_class_data[0] == "Error" or len(recruit_class_data) < 2:
            return "Error"
        elif len(recruit_class_data) == 2:
            return recruit_class_data[1]
        else:
            return f"{recruit_class_data[1]} {recruit_class_data[2]}"

    def extract_hometown(self, img) -> str:
        """Extracts recruit's hometown."""
        hometown_data = self.extract_text(img, "hometown")

        if hometown_data[0] == "Error" or len(hometown_data) < 2:
            return "Error"
        elif len(hometown_data) == 2:
            hometown = hometown_data[1]
        else:
            hometown = f"{hometown_data[1]}, {hometown_data[2]}"

        # OCR sometimes reads "," as ";"
        return hometown.replace(";", ",")

    def extract_height_weight(self, img) -> tuple[str, str]:
        """Extracts recruit's height and weight."""
        height_weight_data = self.extract_text(img, "height_weight")

        if height_weight_data[0] == "Error" or len(height_weight_data) < 2:
            return "Error", "Error"
        elif len(height_weight_data) == 2:
            # Look for Height (e.g., 6' 5")
            height_match = re.search(r"(\d['\s]+\d+[\"']?)", height_weight_data[1])
            height = height_match.group(1) if height_match else ""

            # Look for Weight (e.g., 298)
            # We specifically look for 3 digits that are NOT part of the height
            weight_match = re.search(r"(\d{3})\s*(?:[Ii]bs)?", height_weight_data[1])
            weight = weight_match.group(1) if weight_match else ""
        elif len(height_weight_data) == 3:
            height = height_weight_data[1]
            weight = height_weight_data[2]
        else:
            height = height_weight_data[1]
            weight = height_weight_data[3]

        height = self._normalize_height(height)
        weight = re.sub(r'\s*[Ii]bs\s*', '', weight).strip()
        return height, weight

    def extract_attributes(self, img) -> dict[str, str]:
        """Extracts attributes and maps them to a dictionary."""
        y, h, x, w = ROI_CONFIG["attributes"]
        roi = img[y:y+h, x:x+w]

        if self.debug_mode:
            cv2.imshow("Debug: attributes", roi)
            cv2.waitKey(0)  # Wait for keypress to close debug window
            cv2.destroyAllWindows()

        # detail=1 returns (bbox, text, confidence) — we need Y coordinates for spatial pairing
        attribute_data = self.reader.readtext(roi, detail=1)

        # --- 1. CREATE NORMALIZATION MAP ---
        # {'SHORTACCURACY': 'SHORT ACCURACY', 'RUNBLOCK': 'RUN BLOCK', ...}
        header_map = {h.replace(" ", "").upper(): h for h in ATTRIBUTE_HEADERS}

        # --- 2. PROCESS LABELS & VALUES, TRACKING Y POSITION ---
        label_items = []  # (y, clean_label)
        value_items = []  # (y, clean_value)

        for bbox, item, _ in attribute_data:
            item_y = bbox[0][1]  # top-left Y of bounding box

            if all(c.isdigit() for c in item):
                val = self._clean_value(item)
                if len(val) == 2:  # keep only 2-digit stats, filter noise
                    value_items.append((item_y, val))
            else:
                ocr_key = item.replace(" ", "").upper()
                if ocr_key in header_map:
                    label_items.append((item_y, header_map[ocr_key]))
                else:
                    print(f"Unrecognized attribute label: {item}")

        # --- 3. SORT BOTH BY Y, THEN ZIP ---
        # Sorting independently means a missed label only drops that one attribute
        # rather than corrupting all subsequent pairings.
        label_items.sort(key=lambda x: x[0])
        value_items.sort(key=lambda x: x[0])

        result = dict(zip(
            [label for _, label in label_items],
            [val for _, val in value_items]
        ))
        logger.info(f"Extracted Attributes: {result}")
        return result

    def extract_star_rating(self, img) -> int:
        """Extracts the recruit's star rating (1–5)."""
        y, h, x, w = ROI_CONFIG["star_rating"]
        star_roi = img[y:y+h, x:x+w]
        return processor.get_star_rating(star_roi, debug_mode=self.debug_mode)

    def extract_gem_status(self, img) -> str:
        """Returns 'GEM', 'BUST', or 'NORMAL' based on the recruit icon color."""
        y, h, x, w = ROI_CONFIG["gem_icon"]
        gem_roi = img[y:y+h, x:x+w]
        return processor.detect_gem_status(gem_roi, debug_mode=self.debug_mode)

    def process_current_recruit(self):
        """The main execution logic for a single 'S' key press."""
        img = self._capture_screen()
        
        # 1. Extract Identity via OCR
        name = self.extract_name(img)
        position = self.extract_position(img)
        archetype = self.extract_archetype(img)
        recruit_class = self.extract_recruit_class(img)
        hometown = self.extract_hometown(img)
        height, weight = self.extract_height_weight(img)
        attributes = self.extract_attributes(img)
        
        # 2. Extract Specialized Data via Processor
        star_rating = self.extract_star_rating(img)
        gem_status = self.extract_gem_status(img)

        # 3. Create Model
        recruit = Recruit(
                name=name, position=position, archetype=archetype, 
                star_rating=star_rating, gem_status=gem_status, 
                height=height, weight=weight, recruit_class=recruit_class, 
                hometown=hometown, attributes=attributes
            )

        # 4. Validation & Save
        if recruit.is_valid():
            self.output.save(recruit)
            if self.keep_screenshots:
                self._save_recruit_screenshot(img, name, position)
            logger.info(f"Successfully saved {name}")
            self._trigger_alert(success=True)
        else:
            logger.warning("Scan failed validation.")
            self._trigger_alert(success=False)
