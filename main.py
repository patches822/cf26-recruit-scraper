import os
import keyboard
import logging
from config import MONITOR_NUMBER, REPORTS_DIR, SCREENSHOT_DIR
from src.scraper import RecruitScraper

# Setup basic logging for the console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

def startup_menu():
    """Menu to configure the session."""
    print("\n" + "═"*40)
    print("       COLLEGE FOOTBALL RECRUIT SCRAPER")
    print("═"*40)
    
    # 1. Save Mode
    print("\n[1] SELECT SAVE MODE:")
    print("    (1) Google Sheets")
    print("    (2) Local CSV File")
    save_choice = input("    Choice: ").strip()
    save_mode = "SHEETS" if save_choice == '1' else "CSV"

    # 2. Debug Mode
    print("\n[2] ENABLE DEBUG WINDOWS?")
    print("    (y) Yes | (n) No")
    debug_choice = input("    Choice: ").strip().lower()
    debug_mode = True if debug_choice == 'y' else False

    # 3. Screenshot Record Keeping
    print("\n[3] SAVE SCREENSHOTS FOR EVERY RECRUIT?")
    print("    (y) Yes | (n) No")
    ss_choice = input("    Choice: ").strip().lower()
    keep_screenshots = True if ss_choice == 'y' else False

    # 4. Sound Alerts
    print("\n[4] ENABLE AUDIBLE ALERTS (BEEPS)?")
    print("    (y) Yes | (n) No")
    sound_choice = input("    Choice: ").strip().lower()
    use_sounds = True if sound_choice == 'y' else False

    print("\n" + "═"*40)
    return {
        "save_mode": save_mode,
        "debug_mode": debug_mode,
        "keep_screenshots": keep_screenshots,
        "use_sounds": use_sounds
    }

def main():
    # Ensure directories exist
    for folder in [SCREENSHOT_DIR, REPORTS_DIR]:
        os.makedirs(folder, exist_ok=True)

    # Get user settings
    settings = startup_menu()

    # Initialize the Scraper with selected settings
    scraper = RecruitScraper(
        save_mode=settings["save_mode"],
        use_sounds=settings["use_sounds"],
        keep_screenshots=settings["keep_screenshots"]
    )
    
    # Set the debug toggle directly on the scraper instance
    scraper.debug_mode = settings["debug_mode"]

    print(f"\n🚀 SCRAPER ACTIVE")
    print(f"   Mode:    {settings['save_mode']}")
    print(f"   Monitor: {MONITOR_NUMBER}")
    print("-" * 40)
    print("👉 Press 'S' to capture recruit data.")
    print("👉 Press 'ESC' to exit safely.")
    print("-" * 40 + "\n")

    # Set up the Hotkey Listener
    # We use a lambda to call the method since process_current_recruit takes no arguments
    keyboard.add_hotkey('s', scraper.process_current_recruit)
    
    # Wait until user presses ESC
    keyboard.wait('esc')
    
    print("\nShutting down gracefully...")

if __name__ == "__main__":
    main()