from __future__ import annotations

from fastapi import Header, HTTPException

from app.core.config import settings


def require_token(x_autowechat_token: str | None = Header(default=None)) -> None:
    if settings.api_token and x_autowechat_token != settings.api_token:
        raise HTTPException(status_code=401, detail="Invalid autoWechat token")

