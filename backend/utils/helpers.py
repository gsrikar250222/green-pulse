"""
GreenPulse – Utility helpers
"""
from bson import ObjectId
from datetime import datetime
import re
import math


def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB _id ObjectId to string id."""
    if doc is None:
        return None
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    # Recursively convert nested ObjectIds
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            doc[k] = str(v)
        elif isinstance(v, list):
            doc[k] = [str(i) if isinstance(i, ObjectId) else i for i in v]
    return doc


def serialize_list(docs: list) -> list:
    return [serialize_doc(d) for d in docs]


def paginate(page: int, limit: int, total: int) -> dict:
    pages = math.ceil(total / limit) if limit else 1
    return {"page": page, "limit": limit, "total": total, "pages": pages}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text


def now() -> datetime:
    return datetime.utcnow()


def build_search_filter(query: str, fields: list) -> dict:
    """Build a MongoDB $or text search filter across given fields."""
    if not query:
        return {}
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return {"$or": [{f: {"$regex": pattern}} for f in fields]}
