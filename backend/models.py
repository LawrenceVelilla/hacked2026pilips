from pydantic import BaseModel


class UploadPhotoResponse(BaseModel):
    status: str
    photo_type: str
    photo_url: str


class UserPhotosResponse(BaseModel):
    face: str | None = None
    upper_body: str | None = None
    full_body: str | None = None


class TryOnRequest(BaseModel):
    image_url: str


class TryOnResponse(BaseModel):
    status: str
    session_id: str | None = None
    tryon_image_url: str | None = None
    description: str | None = None
    fit_notes: str | None = None
    error: str | None = None


class ChatRequest(BaseModel):
    session_id: str
    message: str
    image_url: str | None = None


class ChatResponse(BaseModel):
    status: str
    session_id: str | None = None
    tryon_image_url: str | None = None
    description: str | None = None
    fit_notes: str | None = None
    error: str | None = None


class ClassificationResult(BaseModel):
    description: str
    fit_notes: str
    colors: list[str]
    style: str


class HealthResponse(BaseModel):
    status: str
