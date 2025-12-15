import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
WATERMARK_TEXT = os.getenv('WATERMARK_TEXT', 'TEST_WATERMARK')

# Create output directory
OUTPUT_DIR = "watermark_examples"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def process_image_improved(image_bytes, watermark_text, opacity, text_width_ratio, shadow_offset, shadow_opacity):
    """
    Improved watermark processing function (same as in bot.py)
    """
    # Open image from bytes
    img = Image.open(BytesIO(image_bytes))

    # Create copies to work with
    img_copy = img.copy()
    if img_copy.mode != 'RGBA':
        img_copy = img_copy.convert('RGBA')

    # Create a transparent overlay for watermark
    watermark = Image.new('RGBA', img_copy.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark)

    # Available fonts (Ubuntu paths first, then macOS for local testing)
    font_paths = [
        # Ubuntu/Debian - Liberation fonts (usually pre-installed)
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        # Ubuntu/Debian - DejaVu fonts (common fallback)
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        # Ubuntu - Ubuntu font family
        '/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf',
        '/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf',
        # macOS (for local development/testing)
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
        '/System/Library/Fonts/Supplemental/Arial.ttf',
    ]

    # Find first available font path
    available_font_path = None
    for font_path in font_paths:
        try:
            test_font = ImageFont.truetype(font_path, size=20)
            available_font_path = font_path
            print(f"Found available font: {font_path}")
            break
        except Exception as e:
            continue

    # Calculate target text width based on ratio
    target_text_width = img_copy.width * text_width_ratio
    print(f"Target text width: {target_text_width}px (ratio: {text_width_ratio})")

    # Calculate optimal font size using binary search
    if available_font_path:
        min_size = 10
        max_size = int(img_copy.height * 0.4)  # Max 40% of image height
        best_font_size = min_size
        best_font = None

        # Binary search for optimal font size
        for iteration in range(20):  # Max 20 iterations
            current_size = (min_size + max_size) // 2

            try:
                test_font = ImageFont.truetype(available_font_path, size=current_size)
                bbox = draw.textbbox((0, 0), watermark_text, font=test_font)
                current_text_width = bbox[2] - bbox[0]

                # Within 3% of target is acceptable
                if abs(current_text_width - target_text_width) < target_text_width * 0.03:
                    best_font_size = current_size
                    best_font = test_font
                    print(f"Found optimal font size: {current_size}px after {iteration + 1} iterations")
                    break

                if current_text_width < target_text_width:
                    min_size = current_size + 1
                    best_font_size = current_size
                    best_font = test_font
                else:
                    max_size = current_size - 1

            except Exception as e:
                print(f"Error during font size calculation: {e}")
                break

        if best_font is None:
            best_font = ImageFont.truetype(available_font_path, size=best_font_size)

        font = best_font
        base_font_size = best_font_size

    else:
        # Fallback: use larger multiplier if no TrueType font available
        print("No TrueType fonts found, using default font")
        font = ImageFont.load_default()
        base_font_size = 11  # Default font size

    # Get final text dimensions
    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    print(f"Final text dimensions: {text_width}x{text_height} with font size {base_font_size}px")

    # Calculate position with padding
    padding = max(20, min(img_copy.width, img_copy.height) // 30)
    max_x = img_copy.width - text_width - padding
    max_y = img_copy.height - text_height - padding

    if max_x < padding:
        max_x = padding
    if max_y < padding:
        max_y = padding

    # Fixed position for testing (bottom right)
    x = max_x
    y = max_y

    print(f"Watermark position: ({x}, {y})")

    # Calculate stroke width for better visibility
    stroke_width = max(2, base_font_size // 15)

    # Draw the shadow (larger offset for better visibility)
    shadow_offset_scaled = max(shadow_offset, base_font_size // 20)
    draw.text(
        (x + shadow_offset_scaled, y + shadow_offset_scaled),
        watermark_text,
        font=font,
        fill=(0, 0, 0, shadow_opacity)
    )

    # Draw the main text with stroke/outline for better visibility
    draw.text(
        (x, y),
        watermark_text,
        font=font,
        fill=(255, 255, 255, opacity),
        stroke_width=stroke_width,
        stroke_fill=(0, 0, 0, min(255, shadow_opacity + 40))
    )

    # Combine the original image with the watermark
    watermarked = Image.alpha_composite(img_copy, watermark)

    # Convert back to RGB
    watermarked = watermarked.convert('RGB')

    return watermarked


def process_image_old(image_bytes, watermark_text, opacity, text_width_ratio, shadow_offset, shadow_opacity):
    """
    Old watermark processing function for comparison
    """
    # Open image from bytes
    img = Image.open(BytesIO(image_bytes))

    # Create copies to work with
    img_copy = img.copy()
    if img_copy.mode != 'RGBA':
        img_copy = img_copy.convert('RGBA')

    # Create a transparent overlay for watermark
    watermark = Image.new('RGBA', img_copy.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark)

    # OLD METHOD: Calculate base font size from image dimensions
    base_font_size = int(min(img_copy.width, img_copy.height) / 15)
    print(f"OLD - Base font size: {base_font_size}")

    # Available fonts (Ubuntu paths first, then macOS for local testing)
    font_paths = [
        # Ubuntu/Debian - Liberation fonts (usually pre-installed)
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        # Ubuntu/Debian - DejaVu fonts (common fallback)
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        # Ubuntu - Ubuntu font family
        '/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf',
        '/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf',
        # macOS (for local development/testing)
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
        '/System/Library/Fonts/Supplemental/Arial.ttf',
    ]

    # Find first available font with proper size
    font = None
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, size=base_font_size)
            break
        except Exception:
            continue

    if font is None:
        font = ImageFont.load_default()

    # Get text size
    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Calculate position with padding
    padding = min(img_copy.width, img_copy.height) // 30
    max_x = img_copy.width - text_width - padding
    max_y = img_copy.height - text_height - padding

    if max_x < padding:
        max_x = padding
    if max_y < padding:
        max_y = padding

    # Fixed position for testing (bottom right)
    x = max_x
    y = max_y

    # Draw the shadow
    draw.text((x + shadow_offset, y + shadow_offset),
              watermark_text,
              font=font,
              fill=(0, 0, 0, shadow_opacity))

    # Draw the main text
    draw.text((x, y),
              watermark_text,
              font=font,
              fill=(255, 255, 255, opacity))

    # Combine the original image with the watermark
    watermarked = Image.alpha_composite(img_copy, watermark)

    # Convert back to RGB
    watermarked = watermarked.convert('RGB')

    return watermarked


def create_sample_image(width, height, text):
    """Create a sample image with gradient background"""
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)

    # Create a gradient
    for y in range(height):
        r = int(100 + (155 * y / height))
        g = int(150 - (50 * y / height))
        b = int(200 - (100 * y / height))
        draw.rectangle([(0, y), (width, y+1)], fill=(r, g, b))

    # Add some text to make it look like a real image
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', size=30)
    except:
        try:
            font = ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', size=30)
        except:
            font = ImageFont.load_default()

    draw.text((width//2 - 100, height//2), text, fill=(255, 255, 255), font=font)

    return img


def run_tests():
    """Run watermark tests with different image sizes and settings"""
    print("="*60)
    print("WATERMARK TESTING SCRIPT")
    print(f"Watermark text: {WATERMARK_TEXT}")
    print("="*60)
    print()

    # Test configurations
    test_sizes = [
        (500, 500, "Small Square"),
        (1000, 1000, "Medium Square"),
        (1920, 1080, "Full HD Landscape"),
        (1080, 1920, "Full HD Portrait"),
        (2048, 2048, "Large Square"),
    ]

    test_configs = [
        {
            "name": "Default Settings",
            "opacity": 128,
            "text_width_ratio": 0.33,
            "shadow_offset": 3,
            "shadow_opacity": 40
        },
        {
            "name": "High Opacity",
            "opacity": 200,
            "text_width_ratio": 0.33,
            "shadow_offset": 3,
            "shadow_opacity": 80
        },
        {
            "name": "Larger Text",
            "opacity": 128,
            "text_width_ratio": 0.45,
            "shadow_offset": 4,
            "shadow_opacity": 40
        },
        {
            "name": "Smaller Text",
            "opacity": 128,
            "text_width_ratio": 0.25,
            "shadow_offset": 2,
            "shadow_opacity": 40
        },
    ]

    # Generate samples for each size
    for width, height, size_name in test_sizes:
        print(f"\n{'='*60}")
        print(f"Testing: {size_name} ({width}x{height})")
        print('='*60)

        # Create sample image
        sample_img = create_sample_image(width, height, size_name)

        # Convert to bytes
        img_bytes = BytesIO()
        sample_img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)

        # Save original
        original_path = f"{OUTPUT_DIR}/{size_name.replace(' ', '_')}_0_original.jpg"
        sample_img.save(original_path)
        print(f"Saved original: {original_path}")

        # Test OLD method
        print(f"\n--- OLD METHOD ---")
        img_bytes.seek(0)
        old_watermarked = process_image_old(
            img_bytes.read(),
            WATERMARK_TEXT,
            opacity=128,
            text_width_ratio=0.33,
            shadow_offset=3,
            shadow_opacity=40
        )
        old_path = f"{OUTPUT_DIR}/{size_name.replace(' ', '_')}_1_old_method.jpg"
        old_watermarked.save(old_path, quality=95)
        print(f"Saved OLD: {old_path}")

        # Test NEW method with default config
        print(f"\n--- NEW METHOD (Default) ---")
        img_bytes.seek(0)
        new_watermarked = process_image_improved(
            img_bytes.read(),
            WATERMARK_TEXT,
            opacity=128,
            text_width_ratio=0.33,
            shadow_offset=3,
            shadow_opacity=40
        )
        new_path = f"{OUTPUT_DIR}/{size_name.replace(' ', '_')}_2_new_default.jpg"
        new_watermarked.save(new_path, quality=95)
        print(f"Saved NEW: {new_path}")

        # Test variations only for medium square (to avoid too many files)
        if "Medium" in size_name:
            for i, config in enumerate(test_configs[1:], start=3):
                print(f"\n--- NEW METHOD ({config['name']}) ---")
                img_bytes.seek(0)
                variant = process_image_improved(
                    img_bytes.read(),
                    WATERMARK_TEXT,
                    opacity=config['opacity'],
                    text_width_ratio=config['text_width_ratio'],
                    shadow_offset=config['shadow_offset'],
                    shadow_opacity=config['shadow_opacity']
                )
                variant_path = f"{OUTPUT_DIR}/{size_name.replace(' ', '_')}_{i}_{config['name'].replace(' ', '_')}.jpg"
                variant.save(variant_path, quality=95)
                print(f"Saved: {variant_path}")

    print("\n" + "="*60)
    print("TESTING COMPLETE!")
    print(f"Check the '{OUTPUT_DIR}' folder for all generated examples.")
    print("="*60)
    print("\nComparison guide:")
    print("- *_0_original.jpg = Original image without watermark")
    print("- *_1_old_method.jpg = OLD watermark (small, low quality)")
    print("- *_2_new_default.jpg = NEW watermark (improved)")
    print("- *_3_*.jpg = NEW watermark variations (different settings)")
    print("\nReview the images and compare old vs new methods!")


if __name__ == '__main__':
    run_tests()
