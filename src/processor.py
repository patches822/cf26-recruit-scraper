import os
import cv2
import numpy as np

# Imported here to avoid circular imports from scraper.py
from config import STAR_MATCH_THRESHOLD, STAR_TEMPLATE_PATH


def _deduplicate_star_matches(points, min_distance: int) -> list:
    """Groups nearby template match hits and returns one point per group.
    Stars are horizontal, so we cluster by X distance only.
    """
    if not points:
        return []

    sorted_points = sorted(points, key=lambda p: p[0])
    groups = [[sorted_points[0]]]

    for point in sorted_points[1:]:
        if point[0] - groups[-1][-1][0] < min_distance:
            groups[-1].append(point)
        else:
            groups.append([point])

    return groups  # one group = one star


def get_star_rating(roi_img: np.ndarray, debug_mode=False) -> int:
    """
    Counts stars in the star rating ROI.
    Uses template matching when assets/star_template.png exists;
    falls back to contour detection otherwise.
    """
    gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)

    if os.path.exists(STAR_TEMPLATE_PATH):
        template = cv2.imread(STAR_TEMPLATE_PATH, cv2.IMREAD_GRAYSCALE)
        match_result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
        ys, xs = np.where(match_result >= STAR_MATCH_THRESHOLD)
        hits = list(zip(xs.tolist(), ys.tolist()))
        groups = _deduplicate_star_matches(hits, min_distance=template.shape[1] // 2)
        star_count = len(groups)

        if debug_mode:
            debug_vis = roi_img.copy()
            for group in groups:
                # Mark the first (leftmost) hit in each group
                cx, cy = group[0]
                cv2.rectangle(debug_vis, (cx, cy), (cx + template.shape[1], cy + template.shape[0]), (0, 255, 0), 2)
            cv2.imshow("Star Detection (template)", debug_vis)
            cv2.waitKey(0)  # Wait for keypress to close debug window
            cv2.destroyAllWindows()
    else:
        # Fallback: contour-based detection until the template is created
        print(f"[WARNING] Star template not found at '{STAR_TEMPLATE_PATH}'. "
              "Using contour fallback. See README to create the template.")
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        star_count = sum(1 for c in contours if 50 < cv2.contourArea(c) < 500)

        if debug_mode:
            debug_vis = roi_img.copy()
            cv2.drawContours(debug_vis, contours, -1, (0, 255, 0), 2)
            cv2.imshow("Star Detection (contour fallback)", debug_vis)
            cv2.imshow("Star Threshold", thresh)
            cv2.waitKey(0)  # Wait for keypress to close debug window
            cv2.destroyAllWindows()

    return min(star_count, 5)


def detect_gem_status(roi_img: np.ndarray, debug_mode=False) -> str:
    """
    Identifies if a recruit is a 'Gem', 'Bust', or 'Normal'.
    Uses HSV color masking to detect Green (Gem) or Red (Bust).
    """
    hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)

    lower_green = np.array([40, 40, 40])
    upper_green = np.array([80, 255, 255])
    green_mask = cv2.inRange(hsv, lower_green, upper_green)

    # Red wraps around in HSV — check both ends of the hue range
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    red_mask = cv2.bitwise_or(
        cv2.inRange(hsv, lower_red1, upper_red1),
        cv2.inRange(hsv, lower_red2, upper_red2)
    )

    if debug_mode:
        cv2.imshow("Original Gem ROI", roi_img)
        cv2.imshow("Gem Mask", green_mask)
        cv2.imshow("Bust Mask", red_mask)
        cv2.waitKey(0)  # Wait for keypress to close debug window
        cv2.destroyAllWindows()

    if cv2.countNonZero(green_mask) > 100:
        return "GEM"
    elif cv2.countNonZero(red_mask) > 100:
        return "BUST"

    return "NORMAL"
