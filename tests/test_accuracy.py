import sys
import os

# Get the absolute path of the current script's directory (tests/)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Get the path of the project root (one level up)
project_root = os.path.dirname(current_dir)

# Add the project root to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import cv2
import logging
import json
from datetime import datetime
from src.scraper import RecruitScraper

# Setup logging to be less noisy during tests
logging.basicConfig(level=logging.ERROR)

def export_results_to_json(data, total_accuracy):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = {
        "timestamp": timestamp,
        "total_accuracy": f"{total_accuracy:.1f}%",
        "detailed_results": data
    }
    
    os.makedirs("test_reports", exist_ok=True)
    filename = f"test_reports/report_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(report, f, indent=4)
    print(f"📊 Detailed report saved to: {filename}")

def run_batch_test(base_folder="screenshots"):
    # Initialize scraper in dummy mode
    scraper = RecruitScraper()
    scraper.debug_mode = False
    scraper.use_sounds = False
    
    full_data_log = []
    results = {"pass": 0, "fail": 0}
    
    # Supported image extensions
    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')

    print(f"\n🧪 Recursive Accuracy Test: Searching in /{base_folder}...")
    print(f"{'Folder/Filename':<40} | {'Name':<20} | {'Attrs':<6} | {'Status'}")
    print("-" * 100)

    # os.walk travels through every subfolder
    for root, dirs, files in os.walk(base_folder):
        for filename in files:
            if filename.lower().endswith(valid_extensions):
                img_path = os.path.join(root, filename)
                
                # Get the relative path for cleaner display (e.g., "2026/QB/image.png")
                rel_path = os.path.relpath(img_path, base_folder)
                
                img_bgr = cv2.imread(img_path)
                if img_bgr is None:
                    continue

                # Run Scraper Logic
                name = scraper.extract_name(img_bgr)
                position = scraper.extract_position(img_bgr)
                archetype = scraper.extract_archetype(img_bgr)
                recruit_class = scraper.extract_recruit_class(img_bgr)
                hometown = scraper.extract_hometown(img_bgr)
                height, weight = scraper.extract_height_weight(img_bgr)
                attributes = scraper.extract_attributes(img_bgr)
                attr_count = len(attributes)

                # Validation
                is_valid = (len(name) > 0 and len(position) > 0 and len(archetype) > 0 and len(recruit_class) > 0 and len(hometown) > 0  and len(height) > 0 and len(weight) > 0 and attr_count == 10)
                status = "✅ PASS" if is_valid else "❌ FAIL"
                
                if is_valid: results["pass"] += 1
                else: results["fail"] += 1

                # Log for JSON
                full_data_log.append({
                    "relative_path": rel_path,
                    "filename": filename,
                    "parent_folder": os.path.basename(root),
                    "captured_name": name,
                    "captured_position": position,
                    "captured_archetype": archetype,
                    "captured_recruit_class": recruit_class,
                    "captured_hometown": hometown,
                    "captured_height": height,
                    "captured_weight": weight,
                    "captured_attributes": attributes,
                    "attribute_count": attr_count,
                    "status": "PASS" if is_valid else "FAIL"
                })

                # Print scannable table row
                # Truncate path if it's too long for the console
                display_path = (rel_path[:37] + '..') if len(rel_path) > 40 else rel_path
                print(f"{display_path:<40} | {name[:20]:<20} | {attr_count:<6} | {status}")

    # --- Summary and Export ---
    total = results["pass"] + results["fail"]
    accuracy = (results["pass"] / total) * 100 if total > 0 else 0
    
    print("-" * 100)
    print(f"SUMMARY: {results['pass']} Passed | {results['fail']} Failed")
    print(f"OVERALL ACCURACY: {accuracy:.1f}%")
    print("-" * 100 + "\n")

    if total > 0:
        export_results_to_json(full_data_log, accuracy)
    else:
        print("Empty-handed! No images found in the specified directory tree.")

if __name__ == "__main__":
    run_batch_test()