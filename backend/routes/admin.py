"""
GreenPulse – Admin dashboard overview & management routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from bson import ObjectId
from typing import Optional

from config.database import get_db
from middleware.auth import require_admin, hash_password
from models.schemas import (
    CategoryCreate, CategoryUpdate, CategoryOut,
    TestimonialCreate, TestimonialUpdate, TestimonialOut,
    SiteSettingsUpdate, MessageResponse, UserCreate, UserOut, UserRole,
)
from utils.helpers import serialize_doc, serialize_list, now

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Public Settings Endpoint ─────────────────────────

@router.get("/public-settings")
async def get_public_settings(db=Depends(get_db)):
    """Publicly accessible site settings for frontend headers, footers & metadata."""
    doc = await db.site_settings.find_one({})
    if not doc:
        return {
            "site_name":       "GreenPulse",
            "tagline":         "Growing India's Agriculture",
            "contact_phone":   "+91 98765 43210",
            "contact_email":   "hello@greenpulse.in",
            "contact_address": "Guntur, Andhra Pradesh, India",
            "whatsapp_number": "919876543210",
            "facebook_url":    "",
            "instagram_url":   "",
            "twitter_url":     "",
            "meta_description":"GreenPulse - India's premier agriculture platform connecting farmers with products, services and expert knowledge.",
        }
    return serialize_doc(doc)


# ── Dashboard Overview ───────────────────────────────

@router.get("/dashboard")
async def dashboard_overview(db=Depends(get_db), _=Depends(require_admin)):
    products    = await db.products.count_documents({"is_active": True})
    services    = await db.services.count_documents({"is_active": True})
    partners    = await db.partners.count_documents({"is_active": True})
    articles    = await db.knowledge_articles.count_documents({"is_published": True})
    total_leads = await db.leads.count_documents({})
    new_leads   = await db.leads.count_documents({"status": "new"})
    users       = await db.users.count_documents({})

    recent = await db.leads.find({}).sort("created_at", -1).limit(10).to_list(10)

    pipeline = [{"$group": {"_id": "$type", "count": {"$sum": 1}}}]
    by_type_raw = await db.leads.aggregate(pipeline).to_list(20)
    by_type = {r["_id"]: r["count"] for r in by_type_raw if r.get("_id")}

    return {
        "stats": {
            "products":    products,
            "services":    services,
            "partners":    partners,
            "articles":    articles,
            "total_leads": total_leads,
            "new_leads":   new_leads,
            "users":       users,
        },
        "leads_by_type": by_type,
        "recent_leads":  serialize_list(recent),
    }


# ── Categories ───────────────────────────────────────

@router.get("/categories")
async def list_categories(
    type: Optional[str] = Query(None),
    db=Depends(get_db),
):
    filt = {}
    if type and type != "all":
        filt["type"] = type
    docs = await db.categories.find(filt).sort("order", 1).to_list(200)
    return serialize_list(docs)


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(data: CategoryCreate, db=Depends(get_db), _=Depends(require_admin)):
    slug_clean = data.slug.strip().lower()
    if await db.categories.find_one({"slug": slug_clean}):
        raise HTTPException(status_code=400, detail="Category slug already exists")

    doc = {**data.model_dump(), "slug": slug_clean, "created_at": now()}
    result = await db.categories.insert_one(doc)
    doc["_id"] = result.inserted_id
    return CategoryOut(**serialize_doc(doc))


@router.put("/categories/{cat_id}", response_model=CategoryOut)
async def update_category(
    cat_id: str,
    data: CategoryUpdate,
    db=Depends(get_db),
    _=Depends(require_admin),
):
    try:
        oid = ObjectId(cat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid category ID")

    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    if "slug" in update:
        update["slug"] = update["slug"].strip().lower()

    res = await db.categories.find_one_and_update(
        {"_id": oid},
        {"$set": update},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Category not found")
    return CategoryOut(**serialize_doc(res))


@router.delete("/categories/{cat_id}", response_model=MessageResponse)
async def delete_category(cat_id: str, db=Depends(get_db), _=Depends(require_admin)):
    try:
        oid = ObjectId(cat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid category ID")

    res = await db.categories.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return MessageResponse(message="Category deleted successfully")


# ── Testimonials ─────────────────────────────────────

@router.get("/testimonials")
async def list_testimonials(db=Depends(get_db)):
    docs = await db.testimonials.find({"is_active": True}).sort("created_at", -1).to_list(50)
    return serialize_list(docs)


@router.get("/all-testimonials")
async def list_all_testimonials(db=Depends(get_db), _=Depends(require_admin)):
    docs = await db.testimonials.find({}).sort("created_at", -1).to_list(100)
    return serialize_list(docs)


@router.post("/testimonials", response_model=TestimonialOut, status_code=status.HTTP_201_CREATED)
async def create_testimonial(data: TestimonialCreate, db=Depends(get_db), _=Depends(require_admin)):
    doc = {**data.model_dump(), "photo_url": None, "created_at": now()}
    result = await db.testimonials.insert_one(doc)
    doc["_id"] = result.inserted_id
    return TestimonialOut(**serialize_doc(doc))


@router.put("/testimonials/{tid}", response_model=TestimonialOut)
async def update_testimonial(
    tid: str,
    data: TestimonialUpdate,
    db=Depends(get_db),
    _=Depends(require_admin),
):
    try:
        oid = ObjectId(tid)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid testimonial ID")

    update = {k: v for k, v in data.model_dump().items() if v is not None}
    res = await db.testimonials.find_one_and_update(
        {"_id": oid},
        {"$set": update},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Testimonial not found")
    return TestimonialOut(**serialize_doc(res))


@router.delete("/testimonials/{tid}", response_model=MessageResponse)
async def delete_testimonial(tid: str, db=Depends(get_db), _=Depends(require_admin)):
    try:
        oid = ObjectId(tid)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid testimonial ID")

    res = await db.testimonials.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Testimonial not found")
    return MessageResponse(message="Testimonial deleted successfully")


# ── Site Settings ────────────────────────────────────

@router.get("/settings")
async def get_settings(db=Depends(get_db), _=Depends(require_admin)):
    doc = await db.site_settings.find_one({})
    return serialize_doc(doc) if doc else {}


@router.put("/settings", response_model=MessageResponse)
async def update_settings(data: SiteSettingsUpdate, db=Depends(get_db), _=Depends(require_admin)):
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    update["updated_at"] = now()
    await db.site_settings.update_one({}, {"$set": update}, upsert=True)
    return MessageResponse(message="Settings updated successfully")


# ── User Management ──────────────────────────────────

@router.get("/users")
async def list_users(
    role:   Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db=Depends(get_db),
    _=Depends(require_admin),
):
    filt = {}
    if role and role != "all":
        filt["role"] = role
    if search and search.strip():
        s = search.strip()
        filt["$or"] = [
            {"name":    {"$regex": s, "$options": "i"}},
            {"email":   {"$regex": s, "$options": "i"}},
            {"phone":   {"$regex": s, "$options": "i"}},
            {"village": {"$regex": s, "$options": "i"}},
        ]

    docs = await db.users.find(filt, {"password": 0}).sort("created_at", -1).limit(200).to_list(200)
    return serialize_list(docs)


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user_by_admin(data: UserCreate, db=Depends(get_db), _=Depends(require_admin)):
    """Admin-only endpoint to create staff or user accounts with specified roles."""
    email_clean = data.email.lower().strip()
    if await db.users.find_one({"email": email_clean}):
        raise HTTPException(status_code=400, detail="Email already registered")

    doc = {
        "name":       data.name.strip(),
        "email":      email_clean,
        "password":   hash_password(data.password),
        "role":       data.role.value if hasattr(data.role, "value") else str(data.role),
        "phone":      data.phone,
        "village":    data.village,
        "crop":       data.crop,
        "is_active":  True,
        "created_at": now(),
        "updated_at": None,
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return UserOut(**serialize_doc(doc))


@router.put("/users/{uid}/role", response_model=MessageResponse)
async def change_user_role(uid: str, role: str, db=Depends(get_db), _=Depends(require_admin)):
    allowed_roles = {"admin", "farmer", "partner", "company"}
    if role not in allowed_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Allowed: {list(allowed_roles)}")
    try:
        oid = ObjectId(uid)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    res = await db.users.update_one({"_id": oid}, {"$set": {"role": role, "updated_at": now()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return MessageResponse(message=f"User role updated to {role}")


@router.put("/users/{uid}/status", response_model=MessageResponse)
async def toggle_user_status(uid: str, is_active: bool, db=Depends(get_db), _=Depends(require_admin)):
    try:
        oid = ObjectId(uid)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    res = await db.users.update_one({"_id": oid}, {"$set": {"is_active": is_active, "updated_at": now()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    status_label = "activated" if is_active else "disabled"
    return MessageResponse(message=f"User account {status_label}")


@router.delete("/users/{uid}", response_model=MessageResponse)
async def delete_user(uid: str, db=Depends(get_db), current_admin=Depends(require_admin)):
    try:
        oid = ObjectId(uid)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    if str(current_admin["_id"]) == uid:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")

    res = await db.users.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return MessageResponse(message="User deleted successfully")
