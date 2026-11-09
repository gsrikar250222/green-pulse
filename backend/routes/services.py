"""
GreenPulse – Services routes
  GET    /services            – list (public/admin, paginated, filterable, searchable)
  GET    /services/{id}       – detail (public/admin)
  POST   /services            – create (admin)
  PUT    /services/{id}       – update (admin)
  DELETE /services/{id}       – delete (admin)
  POST   /services/{id}/images – upload images (admin)
  DELETE /services/{id}/images – remove image (admin)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from bson import ObjectId
from typing import Optional, List

from config.database import get_db
from config.cloudinary import upload_image, delete_image
from middleware.auth import require_admin, optional_user
from models.schemas import ServiceCreate, ServiceUpdate, ServiceOut, PaginatedResponse, MessageResponse
from utils.helpers import serialize_doc, serialize_list, paginate, now

router = APIRouter(prefix="/services", tags=["Services"])


@router.get("", response_model=PaginatedResponse)
async def list_services(
    page:             int            = Query(1, ge=1),
    limit:            int            = Query(12, ge=1, le=100),
    category:         Optional[str] = Query(None),
    search:           Optional[str] = Query(None),
    featured:         Optional[bool]= Query(None),
    include_inactive: bool          = Query(False),
    user                            = Depends(optional_user),
    db                              = Depends(get_db),
):
    filt: dict = {}
    is_admin = user and user.get("role") == "admin"
    if not (is_admin and include_inactive):
        filt["is_active"] = True

    if category and category.strip() and category.lower() != "all":
        filt["category"] = {"$regex": f"^{category.strip()}$", "$options": "i"}
    if featured is not None:
        filt["is_featured"] = featured
    if search and search.strip():
        s = search.strip()
        filt["$or"] = [
            {"name":        {"$regex": s, "$options": "i"}},
            {"description": {"$regex": s, "$options": "i"}},
            {"details":     {"$regex": s, "$options": "i"}},
            {"tags":        {"$regex": s, "$options": "i"}},
            {"category":    {"$regex": s, "$options": "i"}},
        ]

    total = await db.services.count_documents(filt)
    skip  = (page - 1) * limit
    docs  = await db.services.find(filt).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {**paginate(page, limit, total), "items": serialize_list(docs)}


@router.get("/{service_id}", response_model=ServiceOut)
async def get_service(
    service_id: str,
    user=Depends(optional_user),
    db=Depends(get_db),
):
    try:
        oid = ObjectId(service_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid service ID")

    filt = {"_id": oid}
    is_admin = user and user.get("role") == "admin"
    if not is_admin:
        filt["is_active"] = True

    doc = await db.services.find_one(filt)
    if not doc:
        raise HTTPException(status_code=404, detail="Service not found")
    return ServiceOut(**serialize_doc(doc))


@router.post("", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
async def create_service(data: ServiceCreate, db=Depends(get_db), _=Depends(require_admin)):
    doc = {
        **data.model_dump(),
        "images": [],
        "created_at": now(),
        "updated_at": None,
    }
    result = await db.services.insert_one(doc)
    doc["_id"] = result.inserted_id
    return ServiceOut(**serialize_doc(doc))


@router.put("/{service_id}", response_model=ServiceOut)
async def update_service(
    service_id: str,
    data: ServiceUpdate,
    db=Depends(get_db),
    _=Depends(require_admin),
):
    try:
        oid = ObjectId(service_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid service ID")

    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    update["updated_at"] = now()
    res = await db.services.find_one_and_update(
        {"_id": oid},
        {"$set": update},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Service not found")
    return ServiceOut(**serialize_doc(res))


@router.delete("/{service_id}", response_model=MessageResponse)
async def delete_service(service_id: str, db=Depends(get_db), _=Depends(require_admin)):
    try:
        oid = ObjectId(service_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid service ID")

    doc = await db.services.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Service not found")

    await db.services.delete_one({"_id": oid})
    return MessageResponse(message="Service deleted successfully")


@router.post("/{service_id}/images", response_model=ServiceOut)
async def upload_service_images(
    service_id: str,
    files: List[UploadFile] = File(...),
    db=Depends(get_db),
    _=Depends(require_admin),
):
    try:
        oid = ObjectId(service_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid service ID")

    urls = []
    for f in files:
        r = await upload_image(f, folder="greenpulse/services")
        urls.append(r["url"])

    res = await db.services.find_one_and_update(
        {"_id": oid},
        {"$push": {"images": {"$each": urls}}, "$set": {"updated_at": now()}},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Service not found")
    return ServiceOut(**serialize_doc(res))


@router.delete("/{service_id}/images", response_model=ServiceOut)
async def remove_service_image(
    service_id: str,
    image_url: str = Query(..., description="Image URL to remove"),
    db=Depends(get_db),
    _=Depends(require_admin),
):
    try:
        oid = ObjectId(service_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid service ID")

    res = await db.services.find_one_and_update(
        {"_id": oid},
        {"$pull": {"images": image_url}, "$set": {"updated_at": now()}},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Service not found")
    return ServiceOut(**serialize_doc(res))
