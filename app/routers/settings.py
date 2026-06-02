from __future__ import annotations

from fastapi import APIRouter, Depends

from app.adapters.weixin_adapter import weixin_adapter
from app.core import db
from app.routers.deps import require_token
from app.schemas.models import AiSettingsRequest, UiaSettingsRequest, WechatSettingsRequest
from app.services.ai_config import get_ai_config, update_ai_config
from app.services.uia_enhancer import uia_enhancer, update_uia_config


router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_token)])


@router.get("/wechat")
def get_wechat_settings() -> dict:
    return weixin_adapter.get_settings()


@router.post("/wechat")
def update_wechat_settings(payload: WechatSettingsRequest) -> dict:
    values = {key: value for key, value in payload.model_dump().items() if value is not None}
    updated = weixin_adapter.apply_settings(values)
    now = db.utc_now()
    with db.connect() as conn:
        for key, value in values.items():
            conn.execute(
                "INSERT OR REPLACE INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)",
                (f"wechat.{key}", db.encode_json(value), now),
            )
    return updated


@router.get("/ai")
def get_ai_settings() -> dict:
    return get_ai_config(include_secret=False)


@router.post("/ai")
def update_ai_settings(payload: AiSettingsRequest) -> dict:
    values = {key: value for key, value in payload.model_dump().items() if value is not None}
    return update_ai_config(values)


@router.get("/uia")
def get_uia_settings() -> dict:
    return uia_enhancer.status()


@router.post("/uia")
def update_uia_settings(payload: UiaSettingsRequest) -> dict:
    values = {key: value for key, value in payload.model_dump().items() if value is not None}
    config = update_uia_config(values)
    if "enabled" in values:
        uia_enhancer.configure_from_settings()
    return {"config": config, **uia_enhancer.status()}
