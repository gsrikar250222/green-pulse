"""
GreenPulse – Knowledge Center routes
  GET    /knowledge            – list (public/admin, paginated, searchable)
  GET    /knowledge/{id}       – detail (public/admin)
  POST   /knowledge            – create (admin)
  PUT    /knowledge/{id}       – update (admin)
  DELETE /knowledge/{id}       – delete (admin)
  POST   /knowledge/{id}/image – upload featured image (admin)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from bson import ObjectId
from typing import Optional

from config.database import get_db
from config.cloudinary import upload_image
from middleware.auth import require_admin, optional_user
from models.schemas import ArticleCreate, ArticleUpdate, ArticleOut, PaginatedResponse, MessageResponse
from utils.helpers import serialize_doc, serialize_list, paginate, now

router = APIRouter(tags=["Knowledge"])


@router.get("", response_model=PaginatedResponse)
async def list_articles(
    page:                int            = Query(1, ge=1),
    limit:               int            = Query(10, ge=1, le=50),
    category:            Optional[str] = Query(None),
    search:              Optional[str] = Query(None),
    featured:            Optional[bool]= Query(None),
    include_unpublished: bool          = Query(False),
    user                               = Depends(optional_user),
    db                                 = Depends(get_db),
):
    filt: dict = {}
    is_admin = user and user.get("role") == "admin"
    if not (is_admin and include_unpublished):
        filt["is_published"] = True

    if category and category.strip() and category.lower() != "all":
        filt["category"] = {"$regex": f"^{category.strip()}$", "$options": "i"}
    if featured is not None:
        filt["is_featured"] = featured
    if search and search.strip():
        s = search.strip()
        filt["$or"] = [
            {"title":       {"$regex": s, "$options": "i"}},
            {"excerpt":     {"$regex": s, "$options": "i"}},
            {"content":     {"$regex": s, "$options": "i"}},
            {"tags":        {"$regex": s, "$options": "i"}},
            {"category":    {"$regex": s, "$options": "i"}},
            {"author_name": {"$regex": s, "$options": "i"}},
        ]

    total = await db.knowledge_articles.count_documents(filt)
    skip  = (page - 1) * limit
    docs  = await db.knowledge_articles.find(filt).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {**paginate(page, limit, total), "items": serialize_list(docs)}


@router.get("/{article_id}", response_model=ArticleOut)
async def get_article(
    article_id: str,
    user=Depends(optional_user),
    db=Depends(get_db),
):
    try:
        oid = ObjectId(article_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid article ID")

    filt = {"_id": oid}
    is_admin = user and user.get("role") == "admin"
    if not is_admin:
        filt["is_published"] = True

    update_op = {"$inc": {"views": 1}} if not is_admin else {"$set": {"last_viewed": now()}}

    doc = await db.knowledge_articles.find_one_and_update(
        filt,
        update_op,
        return_document=True,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleOut(**serialize_doc(doc))


@router.post("", response_model=ArticleOut, status_code=status.HTTP_201_CREATED)
async def create_article(data: ArticleCreate, db=Depends(get_db), _=Depends(require_admin)):
    doc = {
        **data.model_dump(),
        "featured_image": None,
        "views": 0,
        "created_at": now(),
        "updated_at": None,
    }
    result = await db.knowledge_articles.insert_one(doc)
    doc["_id"] = result.inserted_id
    return ArticleOut(**serialize_doc(doc))


@router.put("/{article_id}", response_model=ArticleOut)
async def update_article(
    article_id: str,
    data: ArticleUpdate,
    db=Depends(get_db),
    _=Depends(require_admin),
):
    try:
        oid = ObjectId(article_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid article ID")

    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    update["updated_at"] = now()
    res = await db.knowledge_articles.find_one_and_update(
        {"_id": oid},
        {"$set": update},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleOut(**serialize_doc(res))


@router.delete("/{article_id}", response_model=MessageResponse)
async def delete_article(article_id: str, db=Depends(get_db), _=Depends(require_admin)):
    try:
        oid = ObjectId(article_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid article ID")

    doc = await db.knowledge_articles.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Article not found")

    await db.knowledge_articles.delete_one({"_id": oid})
    return MessageResponse(message="Article deleted successfully")


@router.post("/{article_id}/image", response_model=ArticleOut)
async def upload_article_image(
    article_id: str,
    file: UploadFile = File(...),
    db=Depends(get_db),
    _=Depends(require_admin),
):
    try:
        oid = ObjectId(article_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid article ID")

    r = await upload_image(file, folder="greenpulse/articles")
    res = await db.knowledge_articles.find_one_and_update(
        {"_id": oid},
        {"$set": {"featured_image": r["url"], "updated_at": now()}},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleOut(**serialize_doc(res))
