from __future__ import annotations

from fastapi import APIRouter, Depends

from app.adapters.weixin_adapter import weixin_adapter
from app.routers.deps import require_token
from app.schemas.models import UiaCompatLaunchRequest
from app.services.uia_enhancer import launch_wechat_compat, probe_wechat_alternative_ui, uia_enhancer


router = APIRouter(prefix="/api/wechat", tags=["wechat"], dependencies=[Depends(require_token)])


@router.get("/status")
def status() -> dict:
    return weixin_adapter.status()


@router.get("/uia/status")
def uia_status() -> dict:
    return uia_enhancer.status()


@router.post("/uia/probe")
def uia_probe() -> dict:
    return uia_enhancer.probe(save_screenshot=True)


@router.post("/uia/probe-alternative")
def uia_probe_alternative() -> dict:
    return probe_wechat_alternative_ui()


@router.post("/uia/start")
def uia_start() -> dict:
    return uia_enhancer.start()


@router.post("/uia/stop")
def uia_stop() -> dict:
    return uia_enhancer.stop()


@router.post("/uia/launch-compat")
def uia_launch_compat(payload: UiaCompatLaunchRequest) -> dict:
    result = launch_wechat_compat(
        restart=payload.restart,
        exe_path=payload.exe_path,
        wait_seconds=payload.wait_seconds,
        probe_timeout_seconds=payload.probe_timeout_seconds,
        probe_interval_seconds=payload.probe_interval_seconds,
        prewarm_uia=payload.prewarm_uia,
    )
    if result.get("ok"):
        uia_enhancer.start()
        result["uia"] = uia_enhancer.status()
    return result
