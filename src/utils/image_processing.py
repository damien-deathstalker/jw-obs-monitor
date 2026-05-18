from PIL import Image
import numpy as np


def rms_of_image(pil_image):
    gray = pil_image.convert("L")
    arr = np.asarray(gray, dtype=np.float32)
    mean = arr.mean()
    rms = float(np.sqrt(np.mean((arr - mean) ** 2)))
    return rms


def detect_media_content(pil_image, threshold=15.0):
    """Return True if the image is likely to contain displayed media.

    This is a simple brightness/contrast metric based on RMS; tune threshold
    for your environment.
    """
    return rms_of_image(pil_image) >= threshold


def process_image(image):
    # Implement image processing logic here
    pass