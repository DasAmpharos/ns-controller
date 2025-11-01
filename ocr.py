#!/usr/bin/env python3
"""OCR script to extract text from images using pytesseract."""

import argparse
import pytesseract
from PIL import Image


def extract_text_from_region(image_path: str, x: int, y: int, width: int, height: int) -> str:
    """
    Extract text from a specific region of an image.

    Args:
        image_path: Path to the image file
        x: X coordinate of the top-left corner of the region
        y: Y coordinate of the top-left corner of the region
        width: Width of the region
        height: Height of the region

    Returns:
        Extracted text from the region
    """
    # Load the image
    image = Image.open(image_path)

    # Crop to the specified region (left, top, right, bottom)
    region = image.crop((x, y, x + width, y + height))


    # Extract text using pytesseract
    text = pytesseract.image_to_string(region)

    return text.strip()


def main():
    parser = argparse.ArgumentParser(description="Extract text from image regions using OCR")
    parser.add_argument("image", help="Path to the image file")
    parser.add_argument("-x", type=int, default=0, help="X coordinate of region (default: 0)")
    parser.add_argument("-y", type=int, default=0, help="Y coordinate of region (default: 0)")
    parser.add_argument("-w", "--width", type=int, help="Width of region (default: full image width)")
    parser.add_argument("-H", "--height", type=int, help="Height of region (default: full image height)")
    parser.add_argument("-s", "--save-region", help="Save the cropped region to this path")

    args = parser.parse_args()

    # Load image to get dimensions if width/height not specified
    image = Image.open(args.image)
    width = args.width if args.width else image.width - args.x
    height = args.height if args.height else image.height - args.y

    print(f"Extracting text from {args.image}")
    print(f"Region: ({args.x}, {args.y}) - {width}x{height}")

    # Extract text
    text = extract_text_from_region(args.image, args.x, args.y, width, height)

    # Optionally save the cropped region
    if args.save_region:
        region = image.crop((args.x, args.y, args.x + width, args.y + height))
        region.save(args.save_region)
        print(f"Saved region to: {args.save_region}")

    print("\nExtracted text:")
    print("-" * 40)
    print(text)
    print("-" * 40)


if __name__ == "__main__":
    main()

