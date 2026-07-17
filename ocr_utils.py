# ocr_utils.py
from io import BytesIO

import pytesseract
from PIL import Image


def extract_text_from_images(image_bytes_list):
    """
    Runs Tesseract OCR on each image and concatenates the results, with a
    page separator, so downstream code can pass one combined text blob to
    the LLM.
    """
    combined_text_parts = []
    for i, img_bytes in enumerate(image_bytes_list, start=1):
        try:
            img = Image.open(BytesIO(img_bytes))
            text = pytesseract.image_to_string(img)
        except Exception as e:
            text = f"[OCR failed on page {i}: {e}]"
        combined_text_parts.append(f"--- Page {i} ---\n{text.strip()}")
    return "\n\n".join(combined_text_parts)
