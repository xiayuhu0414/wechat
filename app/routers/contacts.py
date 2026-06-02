from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core import db
from app.routers.deps import require_token
from app.schemas.models import TagsRequest
from app.tasks.manager import task_manager


router = APIRouter(prefix="/api/contacts", tags=["contacts"], dependencies=[Depends(require_token)])


@router.get("/friends")
async def friends(detail: bool = False) -> dict:
    return await task_manager.enqueue("contacts.friends", {"detail": detail})


@router.get("/groups")
async def groups() -> dict:
    return await task_manager.enqueue("contacts.groups", {})


@router.get("/groups/{name}/members")
async def group_members(name: str) -> dict:
    return await task_manager.enqueue("contacts.group_members", {"group_name": name})


@router.get("/cache")
def cached_contacts(type: str | None = None, keyword: str | None = None) -> list[dict]:
    return db.list_contact_cache(type, keyword)


@router.get("/tags")
def contact_tags(type: str | None = None) -> list[str]:
    return db.list_contact_tags(type)


@router.get("/friends/cache")
def cached_friends(keyword: str | None = None) -> list[dict]:
    return db.list_friends_cache(keyword)


@router.delete("/friends/cache")
def clear_cached_friends() -> dict:
    return db.clear_friends_cache()


@router.get("/groups/cache")
def cached_groups(keyword: str | None = None) -> list[dict]:
    return db.list_groups_cache(keyword)


@router.delete("/groups/cache")
def clear_cached_groups() -> dict:
    return db.clear_groups_cache()


@router.post("/friends/{name}/detail")
async def friend_detail(name: str) -> dict:
    return await task_manager.enqueue("contacts.friend_detail", {"friend_name": name})


@router.get("/groups/{name}/members/cache")
def cached_group_members(name: str) -> list[dict]:
    return db.list_group_members_cache(name)


@router.put("/friends/{name}/tags")
def update_friend_tags(name: str, payload: TagsRequest) -> dict:
    return db.update_contact_tags("friend", name, payload.tags)


@router.put("/groups/{name}/tags")
def update_group_tags(name: str, payload: TagsRequest) -> dict:
    return db.update_contact_tags("group", name, payload.tags)
