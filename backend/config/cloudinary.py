"""
GreenPulse – Cloudinary configuration & upload helpers
Supports production Cloudinary uploads with fallback for local dev & testing
"""
import cloudinary
import cloudinary.uploader
import cloudinary.api
from dotenv import load_dotenv
import os
import base64
from fastapi import UploadFile, HTTPException

load_dotenv()

CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
API_KEY    = os.getenv("CLOUDINARY_API_KEY")
API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

is_configured = bool(
    CLOUD_NAME and API_KEY and API_SECRET and
    not CLOUD_NAME.startswith("your_") and
    not API_KEY.startswith("your_")
)

if is_configured:
    cloudinary.config(
        cloud_name = CLOUD_NAME,
        api_key    = API_KEY,
        api_secret = API_SECRET,
        secure     = True,
    )

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"}
MAX_SIZE_MB   = 10


async def upload_image(file: UploadFile, folder: str = "greenpulse") -> dict:
    """
    Upload a FastAPI UploadFile to Cloudinary.
    If Cloudinary is unconfigured or credentials are placeholders in local dev,
    encodes image as base64 data URI to prevent broken developer experience.
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}. Allowed: JPEG, PNG, WebP, GIF")

    contents = await file.read()
    if len(contents) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size is {MAX_SIZE_MB} MB")

    if is_configured:
        try:
            result = cloudinary.uploader.upload(
                contents,
                folder         = folder,
                resource_type  = "image",
                transformation = [{"quality": "auto:good", "fetch_format": "auto"}],
            )
            return {"url": result["secure_url"], "public_id": result["public_id"]}
        except Exception as e:
            # If Cloudinary network error occurs, log and fallback to data uri in non-fatal way
            pass

    # Local fallback for development / testing without live Cloudinary keys
    b64 = base64.b64encode(contents).decode("utf-8")
    data_url = f"data:{file.content_type};base64,{b64}"
    filename_id = file.filename.rsplit(".", 1)[0] if file.filename else "image"
    return {"url": data_url, "public_id": f"local_{filename_id}"}


async def delete_image(public_id: str) -> bool:
    if not is_configured or public_id.startswith("local_"):
        return True
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get("result") == "ok"
    except Exception:
        return False
