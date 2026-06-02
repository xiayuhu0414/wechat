from __future__ import annotations

from typing import Any

from app.core import db


DEFAULT_AI_CONFIG: dict[str, Any] = {
    "base_url": "https://api.deepseek.com",
    "api_key": "",
    "model": "deepseek-v4-flash",
    "temperature": 0.7,
    "max_tokens": 600,
    "timeout_seconds": 60,
    "system_prompt": (
        "你是一个擅长微信朋友圈文案的中文文案助手。"
        "输出要自然、克制、有生活感，避免夸张营销腔。"
    ),
}


def _setting_key(key: str) -> str:
    return f"ai.{key}"


def _normalize_config(values: dict[str, Any]) -> dict[str, Any]:
    config = {**DEFAULT_AI_CONFIG, **values}
    config["base_url"] = str(config.get("base_url") or DEFAULT_AI_CONFIG["base_url"]).strip().rstrip("/")
    config["model"] = str(config.get("model") or DEFAULT_AI_CONFIG["model"]).strip()
    config["api_key"] = str(config.get("api_key") or "").strip()
    config["system_prompt"] = str(config.get("system_prompt") or DEFAULT_AI_CONFIG["system_prompt"]).strip()
    config["temperature"] = float(
        DEFAULT_AI_CONFIG["temperature"] if config.get("temperature") is None else config["temperature"]
    )
    config["max_tokens"] = int(
        DEFAULT_AI_CONFIG["max_tokens"] if config.get("max_tokens") is None else config["max_tokens"]
    )
    config["timeout_seconds"] = float(
        DEFAULT_AI_CONFIG["timeout_seconds"] if config.get("timeout_seconds") is None else config["timeout_seconds"]
    )
    return config


def get_ai_config(*, include_secret: bool = False) -> dict[str, Any]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT key, value FROM app_settings WHERE key LIKE 'ai.%'"
        ).fetchall()
    stored = {row["key"][3:]: db.decode_json(row["value"]) for row in rows}
    config = _normalize_config(stored)
    if include_secret:
        return config
    return {
        key: value
        for key, value in config.items()
        if key != "api_key"
    } | {"api_key_set": bool(config["api_key"])}


def update_ai_config(values: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key in DEFAULT_AI_CONFIG:
        if key not in values:
            continue
        value = values[key]
        if key == "api_key" and not str(value or "").strip():
            continue
        clean[key] = value

    if clean:
        normalized = _normalize_config(clean)
        now = db.utc_now()
        with db.connect() as conn:
            for key in clean:
                conn.execute(
                    "INSERT OR REPLACE INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)",
                    (_setting_key(key), db.encode_json(normalized[key]), now),
                )
    return get_ai_config(include_secret=False)
