"""
GreenPulse – Partners routes
  GET    /partners            – list (public/admin, paginated, searchable)
  GET    /partners/{id}       – detail (public/admin)
  POST   /partners            – create (admin)
  PUT    /partners/{id}       – update (admin)
  DELETE /partners/{id}       – delete (admin)
  POST   /partners/{id}/logo   – upload logo (admin)
  POST   /partners/{id}/images – upload gallery images (admin)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from bson import ObjectId
from typing import Optional, List

from config.database import get_db
from config.cloudinary import upload_image, delete_image
from middleware.auth import require_admin, optional_user
from models.schemas import PartnerCreate, PartnerUpdate, PartnerOut, PaginatedResponse, MessageResponse
from utils.helpers import serialize_doc, serialize_list, paginate, now

router = APIRouter(prefix="/partners", tags=["Partners"])


@router.get("", response_model=PaginatedResponse)
async def list_partners(
    page:             int            = Query(1, ge=1),
    limit:            int            = Query(20, ge=1, le=100),
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
            {"company_name": {"$regex": s, "$options": "i"}},
            {"description":  {"$regex": s, "$options": "i"}},
            {"category":     {"$regex": s, "$options": "i"}},
        ]

    total = await db.partners.count_documents(filt)
    skip  = (page - 1) * limit
    docs  = await db.partners.find(filt).sort("company_name", 1).skip(skip).limit(limit).to_list(limit)
    return {**paginate(page, limit, total), "items": serialize_list(docs)}


@router.get("/{partner_id}", response_model=PartnerOut)
async def get_partner(
    partner_id: str,
    user=Depends(optional_user),
    db=Depends(get_db),
):
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid partner ID")

    filt = {"_id": oid}
    is_admin = user and user.get("role") == "admin"
    if not is_admin:
        filt["is_active"] = True

    doc = await db.partners.find_one(filt)
    if not doc:
        raise HTTPException(status_code=404, detail="Partner not found")
    return PartnerOut(**serialize_doc(doc))


@router.post("", response_model=PartnerOut, status_code=status.HTTP_201_CREATED)
async def create_partner(data: PartnerCreate, db=Depends(get_db), _=Depends(require_admin)):
    doc = {
        **data.model_dump(),
        "logo_url": None,
        "images": [],
        "created_at": now(),
        "updated_at": None,
    }
    result = await db.partners.insert_one(doc)
    doc["_id"] = result.inserted_id
    return PartnerOut(**serialize_doc(doc))


@router.put("/{partner_id}", response_model=PartnerOut)
async def update_partner(
    partner_id: str,
    data: PartnerUpdate,
    db=Depends(get_db),
    _=Depends(require_admin),
):
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid partner ID")

    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    update["updated_at"] = now()
    res = await db.partners.find_one_and_update(
        {"_id": oid},
        {"$set": update},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Partner not found")
    return PartnerOut(**serialize_doc(res))


@router.delete("/{partner_id}", response_model=MessageResponse)
async def delete_partner(partner_id: str, db=Depends(get_db), _=Depends(require_admin)):
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid partner ID")

    doc = await db.partners.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Partner not found")

    await db.partners.delete_one({"_id": oid})
    return MessageResponse(message="Partner deleted successfully")


@router.post("/{partner_id}/logo", response_model=PartnerOut)
async def upload_partner_logo(
    partner_id: str,
    file: UploadFile = File(...),
    db=Depends(get_db),
    _=Depends(require_admin),
):
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid partner ID")

    r = await upload_image(file, folder="greenpulse/partners")
    res = await db.partners.find_one_and_update(
        {"_id": oid},
        {"$set": {"logo_url": r["url"], "updated_at": now()}},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Partner not found")
    return PartnerOut(**serialize_doc(res))


@router.post("/{partner_id}/images", response_model=PartnerOut)
async def upload_partner_images(
    partner_id: str,
    files: List[UploadFile] = File(...),
    db=Depends(get_db),
    _=Depends(require_admin),
):
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid partner ID")

    urls = []
    for f in files:
        r = await upload_image(f, folder="greenpulse/partners/gallery")
        urls.append(r["url"])

    res = await db.partners.find_one_and_update(
        {"_id": oid},
        {"$push": {"images": {"$each": urls}}, "$set": {"updated_at": now()}},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Partner not found")
    return PartnerOut(**serialize_doc(res))
