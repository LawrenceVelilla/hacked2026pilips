import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from backend.config import BASE_URL, PHOTOS_DIR, VALID_PHOTO_TYPES


def ensure_photos_dir() -> None:
    Path(PHOTOS_DIR).mkdir(exist_ok=True)


async def save_photo(file: UploadFile, photo_type: str) -> str:
    if photo_type not in VALID_PHOTO_TYPES:
        raise ValueError(f"Invalid photo_type: {photo_type}. Must be one of {VALID_PHOTO_TYPES}")

    ensure_photos_dir()

    # Remove any existing photo of this type
    for existing in Path(PHOTOS_DIR).glob(f"{photo_type}_*"):
        existing.unlink()

    ext = Path(file.filename).suffix if file.filename else ".jpg"
    filename = f"{photo_type}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = Path(PHOTOS_DIR) / filename

    content = await file.read()
    filepath.write_bytes(content)

    return f"{BASE_URL}/photos/{filename}"


def get_user_photos() -> dict[str, str | None]:
    ensure_photos_dir()
    photos: dict[str, str | None] = {pt: None for pt in VALID_PHOTO_TYPES}

    for filepath in Path(PHOTOS_DIR).iterdir():
        for pt in VALID_PHOTO_TYPES:
            if filepath.name.startswith(f"{pt}_"):
                photos[pt] = f"{BASE_URL}/photos/{filepath.name}"
                break

    return photos


def get_photo_path(photo_type: str) -> str | None:
    ensure_photos_dir()
    for filepath in Path(PHOTOS_DIR).iterdir():
        if filepath.name.startswith(f"{photo_type}_"):
            return str(filepath)
    return None
