"""Quick test: call FLUX.2 Pro on Replicate to check facial integrity preservation.

Sends your reference photo + an outfit photo as input_images, then asks FLUX
to generate you wearing that outfit. Compare output to your actual face.

Images are resized to ~1MP before sending to avoid the $1.23 megapixel bill.
Cost: ~$0.05-0.06 per call. This runs the best prompt only = ~$0.06 total.
"""

import asyncio
import io
from pathlib import Path

from PIL import Image
import replicate
from dotenv import load_dotenv

load_dotenv()

USER_PHOTO = Path("photos/IMG_2759-2.png")
OUTFIT_IMAGE = Path("test_images/ccc95a0d1a4ca5771f32506b249eacba.jpg")

PROMPT = (
    "Photo of the person from image 1 wearing the exact outfit "
    "shown in image 2. Maintain the same face and facial features / expression, body type, skin "
    "tone, and hair. Photorealistic, natural lighting, full body shot."
)

# Max dimension — keeps each image under ~1MP to control cost
MAX_DIMENSION = 1024


def resize_for_upload(path: Path) -> io.BytesIO:
    """Resize image so the longest side is MAX_DIMENSION. Returns a BytesIO buffer."""
    img = Image.open(path)
    orig_w, orig_h = img.size
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
    new_w, new_h = img.size
    megapixels = (new_w * new_h) / 1_000_000
    print(f"  {path.name}: {orig_w}x{orig_h} -> {new_w}x{new_h} ({megapixels:.2f} MP)")

    buf = io.BytesIO()
    fmt = "PNG" if path.suffix.lower() == ".png" else "JPEG"
    img.save(buf, format=fmt, quality=85)
    buf.seek(0)
    return buf


async def main():
    for path in [USER_PHOTO, OUTFIT_IMAGE]:
        if not path.exists():
            print(f"Missing file: {path}")
            return

    print("=== FLUX.2 Pro Facial Integrity Test (cost-optimized) ===")
    print(f"User photo:   {USER_PHOTO}")
    print(f"Outfit image: {OUTFIT_IMAGE}")
    print(f"Max dimension: {MAX_DIMENSION}px per side\n")

    print("Resizing images...")
    user_buf = resize_for_upload(USER_PHOTO)
    outfit_buf = resize_for_upload(OUTFIT_IMAGE)

    print(f"\nPrompt: {PROMPT[:100]}...")
    print("Calling FLUX.2 Pro (~$0.05-0.06)...\n")

    try:
        output = await asyncio.to_thread(
            replicate.run,
            "black-forest-labs/flux-2-pro",
            input={
                "prompt": PROMPT,
                "input_images": [user_buf, outfit_buf],
                "aspect_ratio": "3:4",
                "output_format": "webp",
                "output_quality": 90,
                "safety_tolerance": 2,
            },
        )

        result_url = str(output)
        print(f"Good --> Result: {result_url}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
