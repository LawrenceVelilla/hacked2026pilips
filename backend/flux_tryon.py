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


ALLOWED_RATIOS = [
    "1:1", "4:3", "3:4", "16:9", "9:16",
    "3:2", "2:3", "4:5", "5:4", "21:9", "9:21",
]


def _pick_aspect_ratio(width: int, height: int) -> str:
    """Pick the closest FLUX-supported aspect ratio for the given dimensions."""
    target = width / height
    best = "3:4"
    best_diff = float("inf")
    for ratio_str in ALLOWED_RATIOS:
        w, h = map(int, ratio_str.split(":"))
        diff = abs(target - w / h)
        if diff < best_diff:
            best_diff = diff
            best = ratio_str
    return best


def resize_image(data: bytes) -> io.BytesIO:
    """Resize image so longest side is MAX_DIMENSION. Returns JPEG BytesIO."""
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    return buf


def get_image_dimensions(data: bytes) -> tuple[int, int]:
    """Get width and height of an image from bytes."""
    img = Image.open(io.BytesIO(data))
    return img.size


async def _download(url: str) -> bytes:
    """Download raw bytes from URL."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
    return resp.content


async def _prepare_image(url_or_path: str) -> io.BytesIO:
    """Prepare an image from either a local path or URL."""
    local_path = url_or_path.replace("http://localhost:8000/", "")
    if Path(local_path).exists():
        raw = Path(local_path).read_bytes()
    else:
        raw = await _download(url_or_path)
    return resize_image(raw)


async def _load_raw(url_or_path: str) -> bytes:
    """Load raw image bytes from URL or local path."""
    local_path = url_or_path.replace("http://localhost:8000/", "")
    if Path(local_path).exists():
        return Path(local_path).read_bytes()
    return await _download(url_or_path)


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
        # Compute aspect ratio from user photo to preserve proportions
        user_raw = await _load_raw(user_photo_url)
        user_w, user_h = get_image_dimensions(user_raw)
        aspect_ratio = _pick_aspect_ratio(user_w, user_h)

        user_buf = resize_image(user_raw)

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
                "aspect_ratio": aspect_ratio,
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
