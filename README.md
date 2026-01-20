# 🏈 CFB26 Recruit Scraper

An automated data extraction tool for **College Football 25/26** that uses Computer Vision (OpenCV) and Optical Character Recognition (OCR) to scrape recruit profiles and instantly sync them to a Google Sheet.

## 🌟 Features

* **One-Key Scrape:** Press `S` while hovering over a recruit to instantly capture all data.
* **Intelligent OCR:** Extracts Player Name, Position, Archetype, Height, Weight, and Hometown using `EasyOCR`.
* **Computer Vision Gem Detection:** Uses HSV color masking to identify **Green Gems** and **Red Busts** that OCR can't read.
* **Star Rating Counter:** A custom contour-detection algorithm that counts white stars (1-5) on the recruit's profile.
* **Dynamic Attribute Mapping:** Automatically identifies and maps 50+ different attributes (Speed, Throw Power, etc.) based on the recruit's position and archetype.
* **Auto-Normalization:** Fixes common OCR errors (e.g., converting "SHORTACCURACY" back to "Short Accuracy").
* **Google Sheets Integration:** Real-time syncing to a centralized recruiting database.

## 🛠️ Tech Stack

* **Python 3.x**
* **OpenCV:** Image processing and color/icon detection.
* **EasyOCR:** Deep learning-based text extraction.
* **MSS:** High-performance screen capturing.
* **GSpread:** Google Sheets API integration.
* **Keyboard:** Global hotkey management.

## 🚀 Installation & Setup

1. **Clone the repo:**
```bash
git clone https://github.com/yourusername/CFB26-Recruit-Scraper.git
cd CFB26-Recruit-Scraper

```

2. **Install dependencies:**
```bash
pip install opencv-python easyocr gspread mss keyboard oauth2client numpy

```

3. **Google Sheets API:**
* Place your `creds.json` (Service Account Key) in the root directory.
* Share your Google Sheet with the email found in your `creds.json`.

4. **Configure Monitor & ROIs:**
* Open `recruit_scraper.py` and adjust the `MONITOR_NUMBER` and `ROI_CONFIG` coordinates to match your screen resolution.

## 📸 How it Works

The script captures a specific region of the screen, converts the image from **BGRA to BGR** (to avoid the "Blue Gem" color swap issue), and runs several parallel processes:

1. **Masking:** Filters for specific color ranges to find gems.
2. **Contours:** Identifies shapes to count star ratings.
3. **OCR:** Reads text and applies a normalization map to fix kerning/spacing issues.
4. **Export:** Compiles a `Recruit` object and appends it as a new row in Google Sheets.

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

## 🗺️ How to Customize for Your Resolution

The `ROI_CONFIG` values are currently tuned for a specific windowed-mode resolution. To adjust for your setup:

1. Run the script once and press `S`.
2. Open the generated `debug.png`.
3. Use a tool like MS Paint or Photoshop to find the  pixel coordinates of the boxes you want to capture.
4. Update the `(y, h, x, w)` tuples in the `ROI_CONFIG` dictionary.

## 🚀 Future Features & Roadmap

### 🧠 Ability & Mental Extraction

* **Icon Recognition:** Using Template Matching to identify "Platinum," "Gold," "Silver," and "Bronze" ability tiers.
* **Mental Traits:** Scoping the specific Mental icons (like "Road Warrior" or "Closer") to help predict how players perform in high-pressure situations.

### 📊 Data Portability & Persistence

* **CSV Fallback Mode:** Add the ability to save recruit data to a local `.csv` file. This allows for offline scouting and serves as a backup if the Google Sheets API quota is reached or if the internet is down.
* **Database Integration:** Exploring SQLite support for local storage to allow for complex historical scouting queries.

### 🛡️ Stability & Code Quality

* **Automated Testing:** Implement a test suite using `pytest` to run the OCR and color detection logic against a library of "Golden Images" (known screenshots) to ensure code updates don't break detection accuracy.
* **Advanced Error Handling:** Add comprehensive try-except blocks for network timeouts, API rate limits, and OCR "hallucinations" to ensure the script doesn't crash during a long scouting session.
* **Validation Logging:** Create a `failsafe.log` that saves the raw OCR text of any failed scan for manual review later.
