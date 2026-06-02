from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _data_dir() -> Path:
    explicit = os.getenv("AUTOWECHAT_DATA_DIR")
    if explicit:
        return Path(explicit)
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "autoWechat"
    return BASE_DIR / "data"


def _resource_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return BASE_DIR


BASE_DIR = _base_dir()
RESOURCE_DIR = _resource_dir()
DATA_DIR = _data_dir()


@dataclass
class AppSettings:
    app_name: str = "autoWechat Console"
    host: str = os.getenv("AUTOWECHAT_HOST", "127.0.0.1")
    port: int = int(os.getenv("AUTOWECHAT_PORT", "8000"))
    api_token: str | None = os.getenv("AUTOWECHAT_TOKEN") or None
    database_path: Path = DATA_DIR / "app.db"
    uploads_dir: Path = DATA_DIR / "uploads"
    exports_dir: Path = DATA_DIR / "exports"
    logs_dir: Path = DATA_DIR / "logs"
    diagnostics_dir: Path = DATA_DIR / "diagnostics"
    frontend_dist: Path = RESOURCE_DIR / "frontend" / "dist"
    default_is_maximize: bool = False
    default_close_weixin: bool = False
    default_search_pages: int = 5
    default_send_delay: float = 0.2
    default_load_delay: float = 3.5

    def ensure_dirs(self) -> None:
        for path in (self.uploads_dir, self.exports_dir, self.logs_dir, self.diagnostics_dir, self.database_path.parent):
            path.mkdir(parents=True, exist_ok=True)


settings = AppSettings()
