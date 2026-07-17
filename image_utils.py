# image_utils.py
from io import BytesIO
from PIL import Image, ImageOps

# Longest-side cap and JPEG quality chosen to keep handwritten text legible
# while meaningfully shrinking file size for faster OCR/upload/storage.
MAX_DIMENSION = 2000
JPEG_QUALITY = 88


def compress_image(image_bytes, max_dimension=MAX_DIMENSION, quality=JPEG_QUALITY):
    """
    Resizes (if needed) and re-encodes an image as JPEG to reduce file size
    before OCR / Dropbox upload. Returns (compressed_bytes, new_filename_suffix).
    """
    try:
        img = Image.open(BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)  # respect phone camera orientation
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        width, height = img.size
        longest_side = max(width, height)
        if longest_side > max_dimension:
            scale = max_dimension / float(longest_side)
            new_size = (int(width * scale), int(height * scale))
            img = img.resize(new_size, Image.LANCZOS)

        output = BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        return output.getvalue()
    except Exception:
        # If anything goes wrong (unsupported format etc.), fall back to
        # the original bytes rather than losing the photo.
        return image_bytes
