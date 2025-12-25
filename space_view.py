import cv2
import numpy as np
import requests
import json
import time
import sys
from astropy.coordinates import SkyCoord
from astropy import units as u
import matplotlib.pyplot as plt

# Function to load image
def load_image(path):
    return cv2.imread(path)

# Function to detect stars
def detect_stars(image, threshold=200):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    coords = np.column_stack(np.where(thresh > 0))
    # Get unique positions
    stars = list(set((x, y) for y, x in coords))
    return stars

# Function to solve image with astrometry.net
def solve_image_astrometry(image_path, api_key):
    try:
        # Login
        login_url = 'http://nova.astrometry.net/api/login'
        login_data = {'request-json': json.dumps({'apikey': api_key})}
        response = requests.post(login_url, data=login_data)
        if response.status_code != 200 or 'session' not in response.json():
            print("Login failed: Invalid API key or network issue.")
            return None
        session = response.json()['session']

        # Upload file
        upload_url = 'http://nova.astrometry.net/api/upload'
        with open(image_path, 'rb') as f:
            files = {'file': f}
            data = {
                'request-json': json.dumps({
                    'session': session,
                    'publicly_visible': 'n',
                    'allow_commercial_use': 'n'
                })
            }
            response = requests.post(upload_url, files=files, data=data)
        if response.status_code != 200 or 'subid' not in response.json():
            print("Upload failed: Check image or session.")
            return None
        subid = response.json()['subid']

        # Poll for status
        while True:
            status_url = f'http://nova.astrometry.net/api/submissions/{subid}'
            response = requests.get(status_url)
            if response.status_code != 200:
                print("Status check failed.")
                return None
            jobs = response.json().get('jobs', [])
            if jobs:
                job_id = jobs[0]
                break
            time.sleep(5)

        # Get calibration
        calib_url = f'http://nova.astrometry.net/api/jobs/{job_id}/calibration/'
        response = requests.get(calib_url)
        if response.status_code != 200 or not response.json():
            print("Calibration failed: Image may not be solvable.")
            return None
        calib = response.json()
        return calib
    except Exception as e:
        print(f"Error in plate solving: {e}")
        return None

def pixels_to_radec(stars, calib, image_shape):
    if not calib:
        return []
    center_ra = calib['ra']
    center_dec = calib['dec']
    pixscale = calib['pixscale'] / 3600  # deg/pixel
    height, width = image_shape[:2]
    radec_list = []
    for x, y in stars:
        ra_offset = (x - width/2) * pixscale / np.cos(np.radians(center_dec))
        dec_offset = (y - height/2) * pixscale
        ra = center_ra + ra_offset
        dec = center_dec + dec_offset
        radec_list.append((ra, dec))
    return radec_list

# Simple pattern matching for known constellations (fallback)
def match_constellation_patterns(stars, image_shape):
    try:
        print(f"Matching patterns for {len(stars)} stars")
        print(f"stars[0]: {stars[0]}, type: {type(stars[0])}")
        # Dummy implementation: if many stars, assume Orion and draw belt lines
        if len(stars) > 50:
            # Sort stars by x-coordinate
            sorted_stars = sorted(stars, key=lambda p: p[0])
            print(f"Sorted stars: {len(sorted_stars)}")
            # Take first 3 as belt
            if len(sorted_stars) >= 3:
                belt = sorted_stars[:3]
                lines = [(belt[0], belt[1]), (belt[1], belt[2])]
                print(f"Matched Orion with lines: {lines}")
                return "Orion", lines
        print("No match")
        return None, []
    except Exception as e:
        print(f"Error in match: {e}")
        return None, []

# Identify constellations
def identify_constellations(radec_list):
    from astropy.coordinates import get_constellation
    constellations = {}
    for ra, dec in radec_list:
        coord = SkyCoord(ra=ra*u.deg, dec=dec*u.deg)
        const = get_constellation(coord)
        constellations[const] = constellations.get(const, 0) + 1
    if constellations:
        main = max(constellations, key=constellations.get)
        return main, constellations
    return None, {}

# Simple pattern matching for known constellations (fallback when solving fails)
def match_constellation_patterns(stars, image_shape):
    # Normalize stars to 0-1 scale
    height, width = image_shape[:2]
    normalized_stars = [(x/width, y/height) for x, y in stars]
    
    # Define patterns as relative positions (scaled 0-1)
    patterns = {
        'Orion': [  # Belt: three in a line
            (0.5, 0.5), (0.52, 0.5), (0.54, 0.5)
        ],
        'Ursa Major': [  # Big Dipper: rough shape
            (0.3, 0.3), (0.35, 0.25), (0.4, 0.2), (0.45, 0.25), (0.5, 0.3), (0.55, 0.35), (0.6, 0.4)
        ],
        'Ursa Minor': [  # Little Dipper
            (0.7, 0.2), (0.72, 0.18), (0.74, 0.15), (0.76, 0.12), (0.78, 0.1), (0.8, 0.08), (0.82, 0.05)
        ]
    }
    
    tolerance = 0.05  # Allow 5% deviation
    for const, pattern in patterns.items():
        if len(normalized_stars) >= len(pattern):
            # Check if any subset matches the pattern
            from itertools import combinations
            for subset in combinations(normalized_stars, len(pattern)):
                if all(abs(sx - px) < tolerance and abs(sy - py) < tolerance for (sx, sy), (px, py) in zip(subset, pattern)):
                    return const
    return None

# Main script
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("No image and key provided. Generating synthetic star field for demo.")
        # Create synthetic image
        image = np.zeros((500, 500, 3), dtype=np.uint8)
        # Add random stars
        for _ in range(50):
            x, y = np.random.randint(0, 500, 2)
            cv2.circle(image, (x, y), 1, (255, 255, 255), -1)
        image_path = 'synthetic_sky.jpg'
        cv2.imwrite(image_path, image)
        api_key = 'dummy'
    else:
        image_path = sys.argv[1]
        api_key = sys.argv[2]
        image = load_image(image_path)
        if image is None:
            print("Error loading image")
            sys.exit(1)

    if 'image' not in locals():
        image = load_image(image_path)

    stars = detect_stars(image)
    print(f"Detected {len(stars)} stars")

    calib = solve_image_astrometry(image_path, api_key)
    if calib:
        print(f"Calibration successful: {calib}")
        radec_list = pixels_to_radec(stars, calib, image.shape)
        print(f"RA/Dec list: {radec_list[:5]}...")  # Print first 5
        main_constellation, all_const = identify_constellations(radec_list)
        print(f"Main constellation: {main_constellation}")
        print(f"All constellations: {all_const}")
    else:
        print("Plate solving failed. Trying simple pattern matching...")
        print("About to call match")
        main_constellation, lines = match_constellation_patterns(stars, image.shape)
        if main_constellation:
            print(f"Pattern matched: {main_constellation}")
        else:
            print("No known constellation pattern matched.")
            main_constellation = "Unknown"
            lines = []

    # Visualize
    plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    for x, y in stars:
        plt.scatter(x, y, c='red', s=1)
    for line in lines:
        (x1, y1), (x2, y2) = line
        plt.plot([x1, x2], [y1, y2], 'b-', linewidth=2)
    plt.title(f"Detected Stars - Main Constellation: {main_constellation}")
    plt.savefig('constellation_detection.png')
    plt.show()