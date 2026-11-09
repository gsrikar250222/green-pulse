"""
GreenPulse – Leads / Inquiries routes
  POST /leads             – submit inquiry (public, spam protected)
  GET  /leads             – list all (admin)
  GET  /leads/{id}        – detail (admin)
  PUT  /leads/{id}/status – update status & notes (admin)
  DELETE /leads/{id}      – delete (admin)
  GET  /leads/export      – CSV export (admin)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from bson import ObjectId
from typing import Optional
import csv, io
from datetime import datetime

from config.database import get_db
from middleware.auth import require_admin
from models.schemas import LeadCreate, LeadStatusUpdate, LeadOut, PaginatedResponse, MessageResponse, LeadStatus
from utils.helpers import serialize_doc, serialize_list, paginate, now

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.post("", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
async def submit_lead(data: LeadCreate, db=Depends(get_db)):
    # Honeypot spam defense: if bot filled hp_website, silently drop or return dummy
    if data.hp_website and len(data.hp_website.strip()) > 0:
        return LeadOut(
            id=str(ObjectId()),
            name=data.name,
            phone=data.phone,
            email=data.email,
            village=data.village,
            crop=data.crop,
            message=data.message,
            type=data.type,
            status=LeadStatus.new,
            product_id=data.product_id,
            service_id=data.service_id,
            source=data.source,
            notes=None,
            created_at=now(),
        )

    doc = {
        "name":        data.name.strip(),
        "phone":       data.phone.strip(),
        "email":       data.email.lower().strip() if data.email else None,
        "village":     data.village.strip() if data.village else None,
        "crop":        data.crop.strip() if data.crop else None,
        "message":     data.message.strip() if data.message else None,
        "type":        data.type.value if hasattr(data.type, "value") else str(data.type),
        "status":      LeadStatus.new.value,
        "product_id":  data.product_id,
        "service_id":  data.service_id,
        "source":      data.source or "website",
        "notes":       None,
        "created_at":  now(),
        "updated_at":  None,
    }
    result = await db.leads.insert_one(doc)
    doc["_id"] = result.inserted_id
    return LeadOut(**serialize_doc(doc))


@router.get("", response_model=PaginatedResponse)
async def list_leads(
    page:   int            = Query(1, ge=1),
    limit:  int            = Query(20, ge=1, le=100),
    type:   Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db=Depends(get_db),
    _=Depends(require_admin),
):
    filt = {}
    if type and type.strip() and type.lower() != "all":
        filt["type"] = type.strip()
    if status and status.strip() and status.lower() != "all":
        filt["status"] = status.strip()
    if search and search.strip():
        s = search.strip()
        filt["$or"] = [
            {"name":    {"$regex": s, "$options": "i"}},
            {"phone":   {"$regex": s, "$options": "i"}},
            {"village": {"$regex": s, "$options": "i"}},
            {"crop":    {"$regex": s, "$options": "i"}},
            {"message": {"$regex": s, "$options": "i"}},
        ]

    total = await db.leads.count_documents(filt)
    skip  = (page - 1) * limit
    docs  = await db.leads.find(filt).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {**paginate(page, limit, total), "items": serialize_list(docs)}


@router.get("/export")
async def export_leads_csv(db=Depends(get_db), _=Depends(require_admin)):
    docs = await db.leads.find({}).sort("created_at", -1).to_list(10000)
    output = io.StringIO()
    # Write UTF-8 BOM for Microsoft Excel compatibility
    output.write('\ufeff')
    writer = csv.DictWriter(output, fieldnames=[
        "ID", "Name", "Phone", "Email", "Village", "Crop", "Inquiry Type", "Status", "Notes", "Source", "Date"
    ])
    writer.writeheader()
    for d in docs:
        created = d.get("created_at")
        date_str = created.strftime("%Y-%m-%d %H:%M") if isinstance(created, datetime) else str(created or "")
        writer.writerow({
            "ID":           str(d.get("_id", "")),
            "Name":         d.get("name", ""),
            "Phone":        d.get("phone", ""),
            "Email":        d.get("email", ""),
            "Village":      d.get("village", ""),
            "Crop":         d.get("crop", ""),
            "Inquiry Type": d.get("type", ""),
            "Status":       d.get("status", ""),
            "Notes":        d.get("notes", ""),
            "Source":       d.get("source", ""),
            "Date":         date_str,
        })
    output.seek(0)
    filename = f"greenpulse_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{lead_id}", response_model=LeadOut)
async def get_lead(lead_id: str, db=Depends(get_db), _=Depends(require_admin)):
    try:
        oid = ObjectId(lead_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid lead ID")

    doc = await db.leads.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadOut(**serialize_doc(doc))


@router.put("/{lead_id}/status", response_model=LeadOut)
async def update_lead_status(
    lead_id: str,
    data: LeadStatusUpdate,
    db=Depends(get_db),
    _=Depends(require_admin),
):
    try:
        oid = ObjectId(lead_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid lead ID")

    update_fields = {
        "status": data.status.value if hasattr(data.status, "value") else str(data.status),
        "updated_at": now(),
    }
    if data.notes is not None:
        update_fields["notes"] = data.notes.strip()

    res = await db.leads.find_one_and_update(
        {"_id": oid},
        {"$set": update_fields},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadOut(**serialize_doc(res))


@router.delete("/{lead_id}", response_model=MessageResponse)
async def delete_lead(lead_id: str, db=Depends(get_db), _=Depends(require_admin)):
    try:
        oid = ObjectId(lead_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid lead ID")

    res = await db.leads.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return MessageResponse(message="Lead deleted successfully")
