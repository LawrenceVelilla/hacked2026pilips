from fastapi import FastAPI, File, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import PHOTOS_DIR, VALID_PHOTO_TYPES
from backend.models import ( HealthResponse, TryOnRequest, TryOnResponse, 
                             UploadPhotoResponse, UserPhotosResponse,)
from backend.storage import ensure_photos_dir, get_user_photos, save_photo
from backend.tryon import run_tryon

app = FastAPI(title="Fitted")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ensure_photos_dir()
app.mount("/photos", StaticFiles(directory=PHOTOS_DIR), name="photos")


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


@app.post("/try-on", response_model=TryOnResponse)
async def try_on(request: TryOnRequest) -> TryOnResponse:
    # upper body only for now
    category = "upper_body"

    photos = get_user_photos()

    # Select the right reference photo based on category
    photo_url = photos.get(category) or photos.get("full_body")
    if not photo_url:
        return TryOnResponse(
            status="error",
            error=f"No {category} photo uploaded. Please upload a reference photo first.",
        )

    try:
        result_url = await run_tryon(
            human_img_url=photo_url,
            garm_img_url=request.garment_image_url,
            category=category,
        )
        return TryOnResponse(
            status="success",
            tryon_image_url=result_url,
            category=category,
        )
    except RuntimeError as e:
        return TryOnResponse(status="error", error=str(e))
