import cv2
import numpy as np

def get_star_rating(roi_img: np.ndarray, debug_mode=False) -> int:
    """
    Counts the number of stars in the star rating ROI.
    Uses contour detection to find star-shaped objects.
    """
    gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    star_count = 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        # Adjust area threshold based on your resolution
        if 50 < area < 500:
            star_count += 1

    # Debugging: See what the script thinks are stars
    if debug_mode:
        debug_vis = roi_img.copy()
        cv2.drawContours(debug_vis, contours, -1, (0, 255, 0), 2)
        cv2.imshow("Star Detection", debug_vis)
        cv2.imshow("Star Threshold", thresh)
        cv2.waitKey(0)  # 1ms delay to allow window to render without blocking
        cv2.destroyAllWindows()
    
    return min(star_count, 5)

def detect_gem_status(roi_img: np.ndarray, debug_mode=False) -> str:
    """
    Identifies if a recruit is a 'Gem', 'Bust', or 'Normal'.
    Uses HSV color masking to detect Green (Gem) or Red (Bust).
    """
    hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
    
    # Define color ranges for Green and Red icons
    lower_green = np.array([40, 40, 40])
    upper_green = np.array([80, 255, 255])
    green_mask = cv2.inRange(hsv, lower_green, upper_green)
    
    lower_red = np.array([0, 50, 50])
    upper_red = np.array([10, 255, 255])
    red_mask = cv2.inRange(hsv, lower_red, upper_red)

    # Show debugs for color masks
    if debug_mode:
        cv2.imshow("Original Gem ROI", roi_img)
        cv2.imshow("Gem Mask", green_mask)
        cv2.imshow("Bust Mask", red_mask)
        cv2.waitKey(0)  # 1ms delay to allow window to render without blocking
        cv2.destroyAllWindows()

    if cv2.countNonZero(green_mask) > 100:
        return "GEM"
    elif cv2.countNonZero(red_mask) > 100:
        return "BUST"
        
    return "NORMAL"
