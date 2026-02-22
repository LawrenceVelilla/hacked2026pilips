import uuid
from pathlib import Path

from fastapi import FastAPI, File, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import BASE_URL, PHOTOS_DIR, VALID_PHOTO_TYPES
from backend.models import (
    ChatRequest, ChatResponse, HealthResponse,
    TryOnRequest, TryOnResponse,
    UploadPhotoResponse, UserPhotosResponse,
)
from backend.pipeline import chat_modify, start_tryon
from backend.storage import ensure_photos_dir, get_user_photos, save_photo

app = FastAPI(title="FitVision")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ensure_photos_dir()
Path("results").mkdir(exist_ok=True)
app.mount("/results", StaticFiles(directory="results"), name="results")
app.mount("/photos", StaticFiles(directory=PHOTOS_DIR), name="photos")


@app.get("/")
async def index():
    return FileResponse("test_frontend.html")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/upload-photo", response_model=UploadPhotoResponse)
async def upload_photo(
    file: UploadFile = File(...),
    photo_type: str = Query(..., description="One of: face, upper_body, full_body"),
) -> UploadPhotoResponse:
    if photo_type not in VALID_PHOTO_TYPES:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "error": f"Invalid photo_type. Must be one of {VALID_PHOTO_TYPES}"},
        )

    photo_url = await save_photo(file, photo_type)
    return UploadPhotoResponse(status="uploaded", photo_type=photo_type, photo_url=photo_url)


@app.get("/user-photos", response_model=UserPhotosResponse)
async def user_photos() -> UserPhotosResponse:
    photos = get_user_photos()
    return UserPhotosResponse(**photos)


@app.post("/upload-outfit")
async def upload_outfit(file: UploadFile = File(...)):
    """Upload an outfit image file, returns a URL for use with /try-on or /chat."""
    ensure_photos_dir()
    ext = Path(file.filename).suffix if file.filename else ".jpg"
    filename = f"outfit_{uuid.uuid4().hex[:8]}{ext}"
    filepath = Path(PHOTOS_DIR) / filename
    content = await file.read()
    filepath.write_bytes(content)
    return {"image_url": f"{BASE_URL}/photos/{filename}"}


@app.post("/try-on", response_model=TryOnResponse)
async def try_on(request: TryOnRequest) -> TryOnResponse:
    photos = get_user_photos()
    user_photo_url = photos.get("full_body") or photos.get("upper_body")

    if not user_photo_url:
        return TryOnResponse(
            status="error",
            error="No reference photo uploaded. Please upload a full body or upper body photo first.",
        )

    try:
        session = await start_tryon(
            image_url=request.image_url,
            user_photo_url=user_photo_url,
        )
        return TryOnResponse(
            status="success",
            session_id=session.session_id,
            tryon_image_url=session.current_result_url,
            description=session.current_description.description,
            fit_notes=session.current_description.fit_notes,
        )
    except RuntimeError as e:
        return TryOnResponse(status="error", error=str(e))


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        session = await chat_modify(
            session_id=request.session_id,
            message=request.message,
            new_image_url=request.image_url,
        )
        return ChatResponse(
            status="success",
            session_id=session.session_id,
            tryon_image_url=session.current_result_url,
            description=session.current_description.description,
            fit_notes=session.current_description.fit_notes,
        )
    except ValueError as e:
        return ChatResponse(status="error", error=str(e))
    except RuntimeError as e:
        return ChatResponse(status="error", error=str(e))
