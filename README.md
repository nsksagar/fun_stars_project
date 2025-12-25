# Constellation Identifier from Night Sky Photos

A fun AI/computer vision project that analyzes a photo of the night sky to detect stars and identify the constellations present using astrometry.net for plate solving and Astropy for astronomical data.

## Features

- Detects stars in the input image using OpenCV.
- Uses astrometry.net API to calibrate the image (map to sky coordinates).
- Identifies constellations based on star positions.
- Visualizes detected stars and saves the result.

## Requirements

- Python 3.7+
- opencv-python
- numpy
- requests
- astropy
- matplotlib
- pandas
- scikit-learn

## Installation

1. Install dependencies: `pip install -r requirements.txt`
2. Get an API key from [astrometry.net](https://nova.astrometry.net/) (free, sign up required).

## Usage

Run the script with an image path and your API key:

`python space_view.py <path_to_image.jpg> <your_api_key>`

Example: `python space_view.py night_sky.jpg abc123`

The script will:
- Detect stars in the image.
- Attempt to solve the image orientation.
- Identify the main constellation(s).
- Save a visualization as `constellation_detection.png`.

## Notes

- Use clear night sky photos with visible stars (e.g., from APOD).
- Plate solving may take time and requires internet.
- If solving fails, it will still detect stars but cannot identify constellations.
- For testing, download a sample image like an Orion photo.

## Troubleshooting

- Ensure the image is in JPG/PNG format and not too large.
- Check API key validity.
- If star detection misses stars, adjust threshold in the code.
- For real-time, integrate with camera capture (add cv2.VideoCapture).