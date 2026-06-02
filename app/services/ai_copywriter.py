from __future__ import annotations

import json
import re
from typing import Any

import httpx
from fastapi import HTTPException

from app.services.ai_config import get_ai_config


def _build_user_prompt(payload: dict[str, Any]) -> str:
    tone = payload.get("tone") or "自然真诚"
    length = payload.get("length") or "中等"
    count = payload.get("count") or 3
    emoji = "可以少量使用 emoji" if payload.get("include_emoji") else "不要使用 emoji"
    marketing = "可带轻度转化引导，但不要硬广" if payload.get("marketing") else "不要写成广告"
    return (
        f"请根据用户描述生成 {count} 条微信朋友圈文案。\n"
        f"用户描述：{payload.get('description')}\n"
        f"语气：{tone}\n"
        f"长度：{length}\n"
        f"要求：{emoji}；{marketing}；每条独立完整；不要出现编号。\n"
        "只返回 JSON 字符串数组，例如：[\"文案一\", \"文案二\"]。"
    )


def _parse_copies(content: str, count: int) -> list[str]:
    text = content.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()][:count]
        if isinstance(parsed, dict):
            values = parsed.get("copies") or parsed.get("items") or []
            if isinstance(values, list):
                return [str(item).strip() for item in values if str(item).strip()][:count]
    except json.JSONDecodeError:
        pass

    lines = [
        re.sub(r"^\s*(?:\d+[\.)、]|[-*])\s*", "", line).strip().strip('"')
        for line in re.split(r"\n+", text)
    ]
    return [line for line in lines if line][:count]


async def generate_moments_copy(payload: dict[str, Any]) -> dict[str, Any]:
    config = get_ai_config(include_secret=True)
    if not config["api_key"]:
        raise HTTPException(status_code=400, detail="请先在系统配置中填写 DeepSeek API Key")

    url = f"{config['base_url']}/chat/completions"
    count = int(payload.get("count") or 3)
    request_body = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": config["system_prompt"]},
            {"role": "user", "content": _build_user_prompt(payload)},
        ],
        "temperature": config["temperature"],
        "max_tokens": config["max_tokens"],
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=config["timeout_seconds"]) as client:
            response = await client.post(url, json=request_body, headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500] if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"DeepSeek 请求失败：{detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"DeepSeek 连接失败：{exc}") from exc

    data = response.json()
    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    copies = _parse_copies(content, count)
    if not copies:
        raise HTTPException(status_code=502, detail="DeepSeek 返回内容为空或无法解析")
    return {"copies": copies, "raw": content, "model": config["model"]}
