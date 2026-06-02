from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core import db
from app.routers.deps import require_token
from app.schemas.models import BatchAddCustomersRequest, BatchCustomerGreetingsRequest, CustomerImportRequest, CustomerUpdateRequest
from app.services import customer_importer
from app.tasks.manager import task_manager


router = APIRouter(prefix="/api/customers", tags=["customers"], dependencies=[Depends(require_token)])


@router.post("/imports/preview")
async def preview_import(file: UploadFile = File(...)) -> dict:
    try:
        saved = customer_importer.save_upload(file)
        return customer_importer.preview_file(saved["path"])
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/imports/preview")
def preview_existing_import(path: str, sheet_name: str | None = None) -> dict:
    try:
        return customer_importer.preview_file(path, sheet_name=sheet_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/imports")
def commit_import(payload: CustomerImportRequest) -> dict:
    if not payload.mapping.get("number"):
        raise HTTPException(status_code=422, detail="number column is required")
    try:
        return customer_importer.import_file(payload.path, payload.sheet_name, payload.mapping)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
def list_customers(
    keyword: str | None = None,
    add_status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    safe_page = max(1, page)
    safe_page_size = min(max(1, page_size), 500)
    total = db.count_customers(keyword=keyword, add_status=add_status)
    items = db.list_customers(
        keyword=keyword,
        add_status=add_status,
        limit=safe_page_size,
        offset=(safe_page - 1) * safe_page_size,
    )
    return {"items": items, "total": total, "page": safe_page, "page_size": safe_page_size}


@router.post("/batch-add")
async def batch_add_customers(payload: BatchAddCustomersRequest) -> dict:
    customer_ids = payload.customer_ids
    if not customer_ids:
        rows = db.list_customers(keyword=payload.keyword, add_status=payload.add_status, limit=10000)
        customer_ids = [row["id"] for row in rows]
    if not customer_ids:
        raise HTTPException(status_code=422, detail="No customers selected")
    return await task_manager.enqueue(
        "customers.add_friends",
        {
            "customer_ids": customer_ids,
            "chat_only": payload.chat_only,
            "is_maximize": payload.is_maximize,
            "close_weixin": payload.close_weixin,
        },
    )


@router.patch("/greetings")
def batch_update_greetings(payload: BatchCustomerGreetingsRequest) -> dict:
    if not payload.customer_ids and not payload.keyword and not payload.add_status:
        raise HTTPException(status_code=422, detail="Select customers or provide a filter")
    return db.update_customer_greetings(
        greetings=payload.greetings,
        customer_ids=payload.customer_ids,
        keyword=payload.keyword,
        add_status=payload.add_status,
    )


@router.patch("/{customer_id}")
def update_customer(customer_id: str, payload: CustomerUpdateRequest) -> dict:
    try:
        return db.update_customer(customer_id, payload.model_dump(exclude_unset=True))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Customer not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
