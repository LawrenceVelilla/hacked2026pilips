"""FLUX.2 Pro wrapper: generate try-on images with optional layering."""

import asyncio
import io
from pathlib import Path

import uuid

import httpx
import replicate
from PIL import Image
from rembg import new_session, remove

from backend.config import BASE_URL, MAX_DIMENSION, REPLICATE_API_TOKEN

# Preload the background removal model at import time (server startup)
# so the first request doesn't pay the ~10s model download/load cost
_rembg_session = new_session("u2net")

RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

FLUX_MODEL = "black-forest-labs/flux-2-pro"

IDENTITY_ANCHOR = (
    "Keep the same face along with the original facial structure, facial expression, "
    "and skin tone. Keep the original hair. Same body type and proportions."
)

GARMENT_ANCHOR = (
    "Reproduce the clothing EXACTLY as shown — do not alter sleeve length, cuffs, "
    "collars, zippers, or any garment details. No rolling, cuffing, or tucking "
    "unless explicitly described. Do NOT add any head or face accessories "
    "(no hats, glasses, face masks, scarves on head, headbands) unless the user "
    "explicitly requests them. Only apply clothing from the neck down."
)

BASE_PROMPT = (
    "Photo of the person from image 1 wearing the exact outfit "
    "shown in image 2. Outfit description: {description}. "
    f"{IDENTITY_ANCHOR} {GARMENT_ANCHOR} "
    "Photorealistic, natural lighting, full body shot."
)

LAYERING_PROMPT = (
    "Photo of the person from image 1 wearing the outfit shown in image 2, "
    "with the addition of the item from image 3: {description_delta}. "
    "The new item should be layered on top of the existing outfit, not replacing it. "
    f"{IDENTITY_ANCHOR} {GARMENT_ANCHOR} "
    "Photorealistic, natural lighting, full body shot."
)

TEXT_MODIFY_PROMPT = (
    "Photo of the person from image 1 wearing the outfit from image 2, "
    "but modified as follows: {description}. "
    f"{IDENTITY_ANCHOR} {GARMENT_ANCHOR} "
    "Photorealistic, natural lighting, full body shot."
)


def resize_image(data: bytes) -> io.BytesIO:
    """Resize image so longest side is MAX_DIMENSION. Returns JPEG BytesIO."""
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    return buf


async def _download_and_resize(url: str) -> io.BytesIO:
    """Download an image from URL and resize it."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
    return resize_image(resp.content)


def _resize_local_file(path: str) -> io.BytesIO:
    """Load a local file and resize it."""
    return resize_image(Path(path).read_bytes())


async def _prepare_image(url_or_path: str) -> io.BytesIO:
    """Prepare an image from either a local path or URL."""
    # Check if it's a localhost URL pointing to photos/
    local_path = url_or_path.replace("http://localhost:8000/", "")
    if Path(local_path).exists():
        return _resize_local_file(local_path)
    return await _download_and_resize(url_or_path)


async def generate_tryon(
    user_photo_url: str,
    outfit_description: str,
    outfit_image_url: str,
    previous_result_url: str | None = None,
    new_item_image_url: str | None = None,
) -> str:
    """
    Generate a try-on image with FLUX.2 Pro.

    Modes:
        - Initial: user photo + outfit image (2 images)
        - Layering: user photo + previous result + new item (3 images)
        - Text modify: user photo + previous result (2 images, new prompt)
    """
    try:
        user_buf = await _prepare_image(user_photo_url)

        if previous_result_url and new_item_image_url:
            # Layering: user + current look + new item
            prev_buf = await _prepare_image(previous_result_url)
            new_buf = await _prepare_image(new_item_image_url)
            input_images = [user_buf, prev_buf, new_buf]
            prompt = LAYERING_PROMPT.format(description_delta=outfit_description)
        elif previous_result_url:
            # Text-only modification: user + current look
            prev_buf = await _prepare_image(previous_result_url)
            input_images = [user_buf, prev_buf]
            prompt = TEXT_MODIFY_PROMPT.format(description=outfit_description)
        else:
            # Initial try-on: user + outfit reference
            outfit_buf = await _prepare_image(outfit_image_url)
            input_images = [user_buf, outfit_buf]
            prompt = BASE_PROMPT.format(description=outfit_description)

        output = await asyncio.to_thread(
            replicate.run,
            FLUX_MODEL,
            input={
                "prompt": prompt,
                "input_images": input_images,
                "aspect_ratio": "3:4",
                "output_format": "webp",
                "output_quality": 90,
                "safety_tolerance": 2,
            },
        )
        raw_url = str(output)

        # Post-process: download result and remove background
        async with httpx.AsyncClient() as client:
            resp = await client.get(raw_url)
            resp.raise_for_status()

        nobg_bytes = await asyncio.to_thread(remove, resp.content, session=_rembg_session)

        filename = f"tryon_{uuid.uuid4().hex[:8]}.png"
        (RESULTS_DIR / filename).write_bytes(nobg_bytes)

        return f"{BASE_URL}/results/{filename}"

    except Exception as e:
        raise RuntimeError(f"FLUX generation failed: {e}") from e
