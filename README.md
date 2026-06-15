# 🏈 CFB26 Recruit Scraper

An automated Computer Vision (CV) tool designed to scrape recruit profiles in College Football 25/26 and sync them instantly to Google Sheets or a local CSV.

## 🌟 Features

* **Session Configuration:** Interactive startup menu to toggle Debug Mode, Sounds, and Screenshot Archiving.
* **Dual-Output Support:** Choose between real-time Google Sheets syncing or offline CSV logging.
* **Audible Alerts:** High-pitched "Success" and low-pitched "Fail" beeps for eyes-free scouting.
* **One-Key Scrape:** Press `S` while hovering over a recruit to instantly capture all data.
* **Intelligent OCR:** Extracts Player Name, Position, Archetype, Height, Weight, Class, and Hometown using `EasyOCR`.
* **Computer Vision Gem Detection:** Uses HSV color masking to identify **Green Gems** and **Red Busts** that OCR can't read.
* **Star Rating Counter:** A custom contour-detection algorithm that counts white stars (1-5) on the recruit's profile.
* **Dynamic Attribute Mapping:** Automatically identifies and maps 50+ different attributes (Speed, Throw Power, etc.) based on the recruit's position and archetype.

## 🛠️ Tech Stack

* **Python 3.x**
* **OpenCV:** Image processing and color/icon detection.
* **EasyOCR:** Deep learning-based text extraction.
* **MSS:** High-performance screen capturing.
* **GSpread:** Google Sheets API integration.
* **Keyboard:** Global hotkey management.

## 🚀 Getting Started

### 1. Installation

Clone the repo and install the dependencies:

```bash
git clone https://github.com/patches822/cf26-recruit-scraper.git
cd cf26-recruit-scraper
pip install -r requirements.txt

```

### 2. Google Sheets Setup (Optional)

If using Google Sheets mode:

1. Place your `creds.json` in the root folder.
2. Ensure your sheet is titled `CFB26_Recruits` or update the name in the script.

### 3. Usage

Run the script and follow the on-screen prompts to configure your session:

```bash
python recruit_scraper.py

```

* **Press 'S'** to scrape the recruit you are currently hovering over.
* **Press 'ESC'** to save and exit.

### 🗺️ How to Customize for Your Resolution

The `ROI_CONFIG` values are currently tuned for a specific windowed-mode resolution. To adjust for your setup:

1. Run the script once and press `S`.
2. Open the generated `debug.png`.
3. Use a tool like MS Paint or Photoshop to find the  pixel coordinates of the boxes you want to capture.
4. Update the `(y, h, x, w)` tuples in the `ROI_CONFIG` dictionary.

## 🛠️ Troubleshooting & Common Fixes

### 1. The "Blue Gem" / "Orange Bust" Issue

**Problem:** The debug window shows the green gem as blue, or the red bust as orange/yellow.
**Reason:** Different libraries use different color channel orders (RGB vs. BGR).
**Fix:** * Ensure your capture logic uses `cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)`.

* If you use HDR, disable it in Windows/Game settings, as HDR tone-mapping shifts colors outside of the script's hardcoded HSV ranges.

### 2. OpenCV Window Error (`HighGUI` error)

**Problem:** You get an error saying `cv2.imshow` is not implemented.
**Reason:** You likely have the "headless" version of OpenCV installed (common in server environments).
**Fix:**

```bash
pip uninstall opencv-python-headless
pip install opencv-python

```

### 3. GPU Warning (`Neither CUDA nor MPS are available`)

**Problem:** A warning message appears when the script starts.
**Fix:** This is just a notification that the script is using your CPU. It does not affect functionality. To hide it, initialize the reader with `gpu=False`:

```python
reader = easyocr.Reader(['en'], gpu=False)

```

### 4. Star Rating Accuracy

**Problem:** The script detects 0 stars or more than 5 stars.
**Fix:** Open `debug.png` and check the `Star Threshold` window.

* If the stars are "blooming" together into one white blob, **increase** the threshold value in `cv2.threshold(gray, 200, 255...)`.
* If the stars are invisible, **decrease** it to `150`.

## 🚀 Future Features & Roadmap

### 🧠 Ability & Mental Extraction

* **Icon Recognition:** Using Template Matching to identify "Platinum," "Gold," "Silver," and "Bronze" ability tiers.
* **Mental Traits:** Scoping the specific Mental icons (like "Road Warrior" or "Closer") to help predict how players perform in high-pressure situations.

### 📊 Data Portability & Persistence

* **Database Integration:** Exploring SQLite support for local storage to allow for complex historical scouting queries.

### 🛡️ Stability & Code Quality

* **Automated Testing:** Implement a test suite using `pytest` to run the OCR and color detection logic against a library of "Golden Images" (known screenshots) to ensure code updates don't break detection accuracy.
* **Advanced Error Handling:** Add comprehensive try-except blocks for network timeouts, API rate limits, and OCR "hallucinations" to ensure the script doesn't crash during a long scouting session.
* **Validation Logging:** Create a `failsafe.log` that saves the raw OCR text of any failed scan for manual review later.
