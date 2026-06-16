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
    def __init__(self, save_mode="CSV", use_sounds=True, keep_screenshots=False):
        # 1. Configuration
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
            cv2.waitKey(0)  # 1ms delay to allow window to render without blocking
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
        archetype_data = self.extract_text(img, "archetype")
        if archetype_data[0] == "Error":
            return "Error"
        elif len(archetype_data) == 2:
            result = archetype_data[1]
        else:
            # TODO: Find a better solution for the issue where the Gritty Possession Archetype is only being captured as "Possession"
            # Archetype Data: ['ARCHETYPE', 'Possession', 'Gritty']
            result = f"{archetype_data[2]} {archetype_data[1]}"

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
        attribute_data = self.extract_text(img, "attributes")

        # --- 1. CREATE NORMALIZATION MAP ---
        # This creates a dictionary like: {'SHORTACCURACY': 'SHORT ACCURACY', 'RUNBLOCK': 'RUN BLOCK'}
        # It allows us to match OCR text even if spaces are missing.
        header_map = {h.replace(" ", "").upper(): h for h in ATTRIBUTE_HEADERS}   

        # --- 2. PROCESS LABELS & VALUES ---
        clean_labels = []
        clean_values = []

        for item in attribute_data:
            # Check if it's a Value (contains digits)
            if all(c.isdigit() for c in item):
                val = self._clean_value(item)
                if len(val) == 2: # filter out noise, keep 2-digit stats
                    clean_values.append(val)
            else:
                # Item is a Label
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
        y, h, x, w = ROI_CONFIG["star_rating"]
        star_roi = img[y:y+h, x:x+w]
        star_rating = processor.get_star_rating(star_roi, debug_mode=self.debug_mode)
        
        y, h, x, w = ROI_CONFIG["gem_icon"]
        gem_roi = img[y:y+h, x:x+w]
        gem_status = processor.detect_gem_status(gem_roi, debug_mode=self.debug_mode)

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
