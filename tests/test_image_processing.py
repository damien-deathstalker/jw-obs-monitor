from PIL import Image

from src.utils.image_processing import detect_media_content, rms_of_image


def test_rms_of_flat_image_is_zero():
    image = Image.new("L", (4, 4), color=100)

    assert rms_of_image(image) == 0.0


def test_detect_media_content_uses_rms_threshold():
    image = Image.new("L", (2, 1))
    image.putdata([0, 255])

    assert detect_media_content(image, threshold=100) is True
    assert detect_media_content(image, threshold=200) is False
