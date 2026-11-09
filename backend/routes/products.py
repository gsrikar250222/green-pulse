"""
GreenPulse – Products routes
  GET    /products            – list (public/admin, paginated, filterable, searchable)
  GET    /products/{id}       – detail (public/admin)
  POST   /products            – create (admin)
  PUT    /products/{id}       – update (admin)
  DELETE /products/{id}       – delete (admin)
  POST   /products/{id}/images – upload images (admin)
  DELETE /products/{id}/images – remove specific image (admin)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from bson import ObjectId
from typing import Optional, List

from config.database import get_db
from config.cloudinary import upload_image, delete_image
from middleware.auth import require_admin, optional_user
from models.schemas import ProductCreate, ProductUpdate, ProductOut, PaginatedResponse, MessageResponse
from utils.helpers import serialize_doc, serialize_list, paginate, now

router = APIRouter(prefix="/products", tags=["Products"])


# ── List & Detail ───────────────────────────────────

@router.get("", response_model=PaginatedResponse)
async def list_products(
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
            {"brand":       {"$regex": s, "$options": "i"}},
            {"tags":        {"$regex": s, "$options": "i"}},
            {"category":    {"$regex": s, "$options": "i"}},
        ]

    total = await db.products.count_documents(filt)
    skip  = (page - 1) * limit
    docs  = await db.products.find(filt).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {**paginate(page, limit, total), "items": serialize_list(docs)}


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: str,
    user=Depends(optional_user),
    db=Depends(get_db),
):
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    filt = {"_id": oid}
    is_admin = user and user.get("role") == "admin"
    if not is_admin:
        filt["is_active"] = True

    doc = await db.products.find_one(filt)
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductOut(**serialize_doc(doc))


# ── Admin CRUD ───────────────────────────────────────

@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(data: ProductCreate, db=Depends(get_db), _=Depends(require_admin)):
    doc = {
        **data.model_dump(),
        "images": [],
        "created_at": now(),
        "updated_at": None,
    }
    result = await db.products.insert_one(doc)
    doc["_id"] = result.inserted_id
    return ProductOut(**serialize_doc(doc))


@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: str,
    data: ProductUpdate,
    db=Depends(get_db),
    _=Depends(require_admin),
):
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    update["updated_at"] = now()
    res = await db.products.find_one_and_update(
        {"_id": oid},
        {"$set": update},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductOut(**serialize_doc(res))


@router.delete("/{product_id}", response_model=MessageResponse)
async def delete_product(product_id: str, db=Depends(get_db), _=Depends(require_admin)):
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    doc = await db.products.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")

    # Clean up Cloudinary images if possible
    images = doc.get("images", [])
    for img_url in images:
        if "cloudinary.com" in img_url:
            try:
                parts = img_url.split("/")
                filename = parts[-1].split(".")[0]
                folder = parts[-2]
                await delete_image(f"{folder}/{filename}")
            except Exception:
                pass

    await db.products.delete_one({"_id": oid})
    return MessageResponse(message="Product deleted successfully")


@router.post("/{product_id}/images", response_model=ProductOut)
async def upload_product_images(
    product_id: str,
    files: List[UploadFile] = File(...),
    db=Depends(get_db),
    _=Depends(require_admin),
):
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    uploaded_urls = []
    for f in files:
        result = await upload_image(f, folder="greenpulse/products")
        uploaded_urls.append(result["url"])

    res = await db.products.find_one_and_update(
        {"_id": oid},
        {"$push": {"images": {"$each": uploaded_urls}}, "$set": {"updated_at": now()}},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductOut(**serialize_doc(res))


@router.delete("/{product_id}/images", response_model=ProductOut)
async def remove_product_image(
    product_id: str,
    image_url: str = Query(..., description="Image URL to remove"),
    db=Depends(get_db),
    _=Depends(require_admin),
):
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    res = await db.products.find_one_and_update(
        {"_id": oid},
        {"$pull": {"images": image_url}, "$set": {"updated_at": now()}},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Product not found")

    if "cloudinary.com" in image_url:
        try:
            parts = image_url.split("/")
            filename = parts[-1].split(".")[0]
            folder = parts[-2]
            await delete_image(f"{folder}/{filename}")
        except Exception:
            pass

    return ProductOut(**serialize_doc(res))
