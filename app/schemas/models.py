from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskResponse(BaseModel):
    id: str
    type: str
    status: str
    payload: dict[str, Any]
    result: Any | None = None
    error: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    logs: list[dict[str, Any]] = Field(default_factory=list)


class SendMessagesRequest(BaseModel):
    targets: list[str] = Field(min_length=1)
    messages: list[str] = Field(min_length=1)
    at_members: list[str] = Field(default_factory=list)
    send_delay: float | None = None
    search_pages: int | None = None
    is_maximize: bool | None = None
    close_weixin: bool | None = None


class SendFilesRequest(BaseModel):
    targets: list[str] = Field(min_length=1)
    files: list[str] = Field(min_length=1)
    messages: list[str] = Field(default_factory=list)
    messages_first: bool = False
    send_delay: float | None = None
    search_pages: int | None = None
    is_maximize: bool | None = None
    close_weixin: bool | None = None


class ContactsRequest(BaseModel):
    detail: bool = False


class GroupMembersRequest(BaseModel):
    group_name: str


class TagsRequest(BaseModel):
    tags: list[str] = Field(default_factory=list)


class AutoreplyRuleRequest(BaseModel):
    name: str
    target: str
    target_type: Literal["friend", "group"] = "friend"
    keyword: str
    reply: str
    at_only: bool = False
    enabled: bool = True


class AutoreplyStartRequest(BaseModel):
    target: str
    duration: str = "1min"
    rules: list[dict[str, Any]] = Field(default_factory=list)
    at_only: bool = False


class AutoreplyStopRequest(BaseModel):
    task_id: str


class MomentsPostRequest(BaseModel):
    text: str = ""
    medias: list[str] = Field(default_factory=list)


class MomentsCopyRequest(BaseModel):
    description: str = Field(min_length=2)
    tone: str = "自然真诚"
    length: Literal["短", "中等", "长"] = "中等"
    count: int = Field(default=3, ge=1, le=5)
    include_emoji: bool = False
    marketing: bool = False


class WechatSettingsRequest(BaseModel):
    is_maximize: bool | None = None
    close_weixin: bool | None = None
    search_pages: int | None = Field(default=None, ge=0)
    send_delay: float | None = Field(default=None, ge=0)
    load_delay: float | None = Field(default=None, ge=0)


class UiaSettingsRequest(BaseModel):
    enabled: bool | None = None
    interval_seconds: float | None = Field(default=None, ge=2, le=300)
    max_nodes: int | None = Field(default=None, ge=50, le=5000)
    save_screenshot_on_probe: bool | None = None
    use_dotnet_watcher: bool | None = None


class UiaCompatLaunchRequest(BaseModel):
    restart: bool = False
    exe_path: str | None = None
    wait_seconds: float = Field(default=3, ge=0, le=30)
    probe_timeout_seconds: float = Field(default=0, ge=0, le=120)
    probe_interval_seconds: float = Field(default=2, ge=0.5, le=30)
    prewarm_uia: bool = True


class AiSettingsRequest(BaseModel):
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)
    timeout_seconds: float | None = Field(default=None, ge=1, le=300)
    system_prompt: str | None = None


class CustomerImportRequest(BaseModel):
    path: str
    sheet_name: str | None = None
    mapping: dict[str, str | None]


class BatchAddCustomersRequest(BaseModel):
    customer_ids: list[str] = Field(default_factory=list)
    keyword: str | None = None
    add_status: str | None = None
    chat_only: bool = False
    is_maximize: bool | None = None
    close_weixin: bool | None = None


class BatchCustomerGreetingsRequest(BaseModel):
    greetings: str
    customer_ids: list[str] = Field(default_factory=list)
    keyword: str | None = None
    add_status: str | None = None


class CustomerUpdateRequest(BaseModel):
    number: str | None = None
    greetings: str | None = None
    remark: str | None = None
    add_status: Literal["pending", "adding", "added", "failed"] | None = None
