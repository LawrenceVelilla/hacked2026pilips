import os
from dotenv import load_dotenv

load_dotenv()

REPLICATE_API_TOKEN: str = os.getenv("REPLICATE_API_TOKEN", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")

PHOTOS_DIR: str = "photos"
VALID_PHOTO_TYPES: list[str] = ["face", "upper_body", "full_body"]
