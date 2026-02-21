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
    garment_image_url: str


class TryOnAnalysis(BaseModel):
    garment_type: str
    fit_notes: str


class TryOnResponse(BaseModel):
    status: str
    tryon_image_url: str | None = None
    category: str | None = None
    analysis: TryOnAnalysis | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
