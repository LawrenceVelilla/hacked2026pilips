"""Test: Can FLUX.2 Pro layer clothing items?

Step 1: Put the DRMS Club hoodie on the user (~$0.08)
Step 2: Add the black suede jacket OVER the hoodie (~$0.08)

Total cost: ~$0.16
"""

import asyncio
import io
import httpx
from pathlib import Path

from PIL import Image
import replicate
from dotenv import load_dotenv

load_dotenv()

USER_PHOTO = Path("photos/IMG_2759-2.png")
HOODIE_IMAGE = Path("test_images/layering/hoodie.jpg")
JACKET_IMAGE = Path("test_images/layering/jacket.jpg")

MAX_DIMENSION = 1024


def resize_for_upload(path: Path) -> io.BytesIO:
    """Resize image so the longest side is MAX_DIMENSION."""
    img = Image.open(path)
    orig_w, orig_h = img.size
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
    new_w, new_h = img.size
    mp = (new_w * new_h) / 1_000_000
    print(f"  {path.name}: {orig_w}x{orig_h} -> {new_w}x{new_h} ({mp:.2f} MP)")

    buf = io.BytesIO()
    fmt = "PNG" if path.suffix.lower() == ".png" else "JPEG"
    img.save(buf, format=fmt, quality=85)
    buf.seek(0)
    return buf


def resize_from_bytes(data: bytes, name: str) -> io.BytesIO:
    """Resize an image from raw bytes."""
    img = Image.open(io.BytesIO(data))
    orig_w, orig_h = img.size
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
    new_w, new_h = img.size
    mp = (new_w * new_h) / 1_000_000
    print(f"  {name}: {orig_w}x{orig_h} -> {new_w}x{new_h} ({mp:.2f} MP)")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    return buf


async def run_flux(prompt: str, input_images: list[io.BytesIO]) -> str | None:
    """Run FLUX.2 Pro and return result URL."""
    try:
        output = await asyncio.to_thread(
            replicate.run,
            "black-forest-labs/flux-2-pro",
            input={
                "prompt": prompt,
                "input_images": input_images,
                "aspect_ratio": "3:4",
                "output_format": "webp",
                "output_quality": 90,
                "safety_tolerance": 5,
            },
        )
        return str(output)
    except Exception as e:
        print(f"Error: {e}")
        return None


async def main():
    for path in [USER_PHOTO, HOODIE_IMAGE, JACKET_IMAGE]:
        if not path.exists():
            print(f"Missing file: {path}")
            return

    print("=== FLUX.2 Pro Layering Test ===\n")

    # ---- STEP 1: Put the hoodie on ----
    print("STEP 1: Put the DRMS Club hoodie on you")
    print("Resizing inputs...")
    user_buf = resize_for_upload(USER_PHOTO)
    hoodie_buf = resize_for_upload(HOODIE_IMAGE)

    step1_prompt = (
        "Photo of the person from image 1 wearing the dark grey hoodie "
        "with candy hearts graphic and 'drmers club' text from image 2. "
        "Keep the same black pants and tan shoes from image 1. "
        "Maintain the same face, body type, skin tone, and hair. "
        "Photorealistic, natural lighting, full body shot."
    )
    print(f"Prompt: {step1_prompt[:100]}...")
    print("Calling FLUX.2 Pro (~$0.08)...\n")

    step1_url = await run_flux(step1_prompt, [user_buf, hoodie_buf])
    if not step1_url:
        print("Step 1 failed, aborting.")
        return

    print(f"Step 1 result: {step1_url}\n")

    # ---- STEP 2: Layer the jacket OVER the hoodie ----
    print("STEP 2: Add the black suede jacket OVER the hoodie")
    print("Downloading step 1 result to use as reference...")

    async with httpx.AsyncClient() as client:
        resp = await client.get(step1_url)
        step1_bytes = resp.content

    # Re-prepare inputs: original photo + step 1 result + jacket
    print("Resizing inputs...")
    user_buf2 = resize_for_upload(USER_PHOTO)
    step1_buf = resize_from_bytes(step1_bytes, "step1_result")
    jacket_buf = resize_for_upload(JACKET_IMAGE)

    step2_prompt = (
        "Photo of the person from image 1. They are wearing the exact outfit "
        "from image 2 (dark grey candy hearts hoodie with black pants), "
        "with the black suede zip-up jacket from image 3 layered OPEN on top "
        "of the hoodie. The hoodie should be visible underneath the open jacket. "
        "Maintain the same face, body type, skin tone, and hair. "
        "Photorealistic, natural lighting, full body shot."
    )
    print(f"Prompt: {step2_prompt[:100]}...")
    print("Calling FLUX.2 Pro (~$0.08)...\n")

    step2_url = await run_flux(step2_prompt, [user_buf2, step1_buf, jacket_buf])
    if not step2_url:
        print("Step 2 failed.")
        return

    print(f"Step 2 result: {step2_url}\n")

    # ---- Summary ----
    print("=== RESULTS ===")
    print(f"  Step 1 (hoodie only):          {step1_url}")
    print(f"  Step 2 (jacket over hoodie):   {step2_url}")
    print("\nCheck:")
    print("  1. Does step 1 show you in the hoodie?")
    print("  2. Does step 2 show the jacket OVER the hoodie (not replacing it)?")
    print("  3. Is your face consistent across both?")


if __name__ == "__main__":
    asyncio.run(main())
