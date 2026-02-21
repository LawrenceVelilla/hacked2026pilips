import io
from pathlib import Path

import replicate
from PIL import Image

from backend.config import REPLICATE_API_TOKEN

IDMVTON_MODEL = "cuuupid/idm-vton:0513734a452173b8173e907e3a59d19a36266e55b48528559432bd21c7d7e985"

MAX_DIMENSION = 1920


def _prepare_local_image(path: Path) -> io.BytesIO:
    """Load a local image, convert to RGB, resize if needed, return as JPEG bytes."""
    img = Image.open(path).convert("RGB")
    if max(img.size) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    return buf


def _to_file_input(path_or_url: str) -> str | io.BytesIO:
    """If it's a local file path, preprocess and return as bytes. Otherwise return the URL."""
    p = Path(path_or_url)
    if p.exists() and p.is_file():
        return _prepare_local_image(p)
    return path_or_url


async def run_tryon(
    human_img_url: str,
    garm_img_url: str,
    category: str,
    garment_des: str = "Garment",
) -> str:
    try:
        client = replicate.Client(api_token=REPLICATE_API_TOKEN)

        output = client.run(
            IDMVTON_MODEL,
            input={
                "human_img": _to_file_input(human_img_url),
                "garm_img": _to_file_input(garm_img_url),
                "category": category,
                "garment_des": garment_des,
                "crop": True,
            },
        )

        # IDM-VTON returns a single image URL
        if isinstance(output, list):
            return str(output[0])
        return str(output)

    except replicate.exceptions.ReplicateError as e:
        raise RuntimeError(f"Replicate API error: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Try-on failed: {e}") from e
