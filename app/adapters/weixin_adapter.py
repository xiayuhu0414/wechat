from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any, Callable

from app.core import db
from app.core.config import RESOURCE_DIR, settings


PYWECHAT_SOURCE = RESOURCE_DIR / "pywechat"


class WeixinAdapter:
    """Thin, lazy wrapper around pyweixin.

    The import is delayed so the web app can start and tests can run even when
    WeChat or UI Automation dependencies are not ready.
    """

    def __init__(self) -> None:
        self._module: Any | None = None
        self._defaults_applied = False

    @property
    def wx(self) -> Any:
        if self._module is None:
            source = str(PYWECHAT_SOURCE)
            if source not in sys.path:
                sys.path.insert(0, source)
            self._module = importlib.import_module("pyweixin")
        if not self._defaults_applied:
            config = self._module.GlobalConfig
            config.is_maximize = settings.default_is_maximize
            config.close_weixin = settings.default_close_weixin
            config.search_pages = settings.default_search_pages
            config.send_delay = settings.default_send_delay
            config.load_delay = settings.default_load_delay
            self._defaults_applied = True
        return self._module

    def apply_settings(self, values: dict[str, Any]) -> dict[str, Any]:
        config = self.wx.GlobalConfig
        mapping = {
            "is_maximize": bool,
            "close_weixin": bool,
            "search_pages": int,
            "send_delay": float,
            "load_delay": float,
        }
        for key, caster in mapping.items():
            if key in values and values[key] is not None:
                setattr(config, key, caster(values[key]))
        return self.get_settings()

    def get_settings(self) -> dict[str, Any]:
        config = self.wx.GlobalConfig
        return {
            "is_maximize": config.is_maximize,
            "close_weixin": config.close_weixin,
            "search_pages": config.search_pages,
            "send_delay": config.send_delay,
            "load_delay": config.load_delay,
            "version": config.Version,
            "language": config.language,
        }

    def status(self) -> dict[str, Any]:
        try:
            tools = self.wx.Tools
            return {
                "adapter": "pyweixin",
                "available": True,
                "running": bool(tools.is_weixin_running()),
                "version": self.wx.GlobalConfig.Version,
                "language": self.wx.GlobalConfig.language,
                "settings": self.get_settings(),
            }
        except Exception as exc:
            return {
                "adapter": "pyweixin",
                "available": False,
                "running": False,
                "error": str(exc),
            }

    def send_messages(self, targets: list[str], messages: list[str], options: dict[str, Any]) -> dict[str, Any]:
        sent: list[str] = []
        for target in targets:
            self.wx.Messages.send_messages_to_friend(
                friend=target,
                messages=messages,
                at_members=options.get("at_members", []),
                send_delay=options.get("send_delay"),
                search_pages=options.get("search_pages"),
                is_maximize=options.get("is_maximize"),
                close_weixin=options.get("close_weixin"),
            )
            sent.append(target)
        return {"sent_targets": sent, "message_count": len(messages)}

    def send_files(self, targets: list[str], files: list[str], options: dict[str, Any]) -> dict[str, Any]:
        valid_files = [str(Path(path)) for path in files if Path(path).is_file()]
        if not valid_files:
            raise ValueError("没有可发送的有效文件")
        sent: list[str] = []
        for target in targets:
            self.wx.Files.send_files_to_friend(
                friend=target,
                files=valid_files,
                with_messages=bool(options.get("messages")),
                messages=options.get("messages", []),
                messages_first=bool(options.get("messages_first", False)),
                send_delay=options.get("send_delay"),
                is_maximize=options.get("is_maximize"),
                close_weixin=options.get("close_weixin"),
            )
            sent.append(target)
        return {"sent_targets": sent, "file_count": len(valid_files)}

    def _friend_cache_item(self, profile: dict[str, Any], name_hint: str | None = None) -> dict[str, Any]:
        remark = self._none_if_empty(profile.get("备注"))
        nickname = self._none_if_empty(profile.get("昵称"))
        name = self._none_if_empty(name_hint) or remark or nickname
        return {
            "name": name,
            "display_name": nickname or name,
            "remark": remark,
            "wx_number": self._none_if_empty(profile.get("微信号")),
            "phone": self._none_if_empty(profile.get("电话")),
            "region": self._none_if_empty(profile.get("地区")),
            "tags": profile.get("标签"),
            **profile,
        }

    @staticmethod
    def _none_if_empty(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text == "无":
            return None
        return text

    def get_friends(self, detail: bool = False) -> Any:
        if detail:
            try:
                friends = self.wx.Contacts.get_friends_detail(is_json=False, close_weixin=False)
            except Exception as exc:
                return self._get_friends_detail_one_by_one(exc)
            if isinstance(friends, str):
                friends = []
            for friend in friends:
                if isinstance(friend, dict):
                    db.upsert_friend_cache(self._friend_cache_item(friend))
            return friends
        names = self.wx.Contacts.get_friends_name(close_weixin=False)
        for name in names:
            db.upsert_friend_cache({"name": name, "display_name": name})
        return names

    def _get_friends_detail_one_by_one(self, primary_error: Exception) -> dict[str, Any]:
        names = self.wx.Contacts.get_friends_name(close_weixin=False)
        updated: list[str] = []
        failed: list[dict[str, str]] = []
        for name in names:
            clean_name = str(name).strip()
            if not clean_name:
                continue
            db.upsert_friend_cache({"name": clean_name, "display_name": clean_name})
            try:
                profile = self.wx.Contacts.get_friend_profile(friend=clean_name, close_weixin=False)
                if not isinstance(profile, dict):
                    raise ValueError("返回内容不是好友详情")
                db.upsert_friend_cache(self._friend_cache_item(profile, name_hint=clean_name))
                updated.append(clean_name)
            except Exception as exc:
                failed.append({"name": clean_name, "error": str(exc)})
        return {
            "mode": "fallback_one_by_one",
            "primary_error": str(primary_error),
            "total": len(names),
            "updated": len(updated),
            "failed": len(failed),
            "failed_items": failed,
        }

    def get_friend_detail(self, friend_name: str) -> dict[str, Any]:
        profile = self.wx.Contacts.get_friend_profile(friend=friend_name, close_weixin=False)
        if not isinstance(profile, dict):
            raise ValueError(f"无法获取好友详情: {friend_name}")
        db.upsert_friend_cache(self._friend_cache_item(profile, name_hint=friend_name))
        return profile

    def get_groups(self) -> Any:
        groups = self.wx.Contacts.get_recent_groups(close_weixin=False)
        for group in groups:
            if isinstance(group, (list, tuple)):
                name = str(group[0])
                member_count = None
                if len(group) > 1 and str(group[1]).isdigit():
                    member_count = int(group[1])
                db.upsert_group_cache({"name": name, "display_name": name, "member_count": member_count})
            else:
                name = str(group)
                db.upsert_group_cache({"name": name, "display_name": name})
        return groups

    def get_group_members(self, group_name: str) -> Any:
        members = self.wx.Contacts.get_groupMembers_info(group=group_name, close_weixin=False)
        member_count = db.upsert_group_members_cache(group_name, members if isinstance(members, list) else [])
        db.upsert_group_cache(
            {"name": group_name, "display_name": group_name, "raw_members": members, "member_count": member_count},
        )
        return members

    def post_moments(self, text: str, medias: list[str]) -> dict[str, Any]:
        self.wx.Moments.post_moments(text=text, medias=medias, close_weixin=False)
        return {"posted": True, "media_count": len(medias)}

    def start_autoreply(self, target: str, duration: str, rules: list[dict[str, Any]], at_only: bool) -> dict[str, Any]:
        def reply_callback(new_message: str, contexts: list[str] | None = None) -> str | None:
            for rule in rules:
                if rule.get("enabled", True) and rule.get("keyword", "") in new_message:
                    return rule.get("reply")
            return None

        dialog_window = self.wx.Navigator.open_seperate_dialog_window(
            friend=target,
            window_minimize=True,
            close_weixin=False,
        )
        result = self.wx.AutoReply.auto_reply_to_friend(
            dialog_window=dialog_window,
            duration=duration,
            callback=reply_callback,
            close_dialog_window=True,
        )
        return {"target": target, "result": result, "at_only": at_only}

    def add_customer_friends(self, customer_ids: list[str], options: dict[str, Any]) -> dict[str, Any]:
        customers = db.list_customers_by_ids(customer_ids)
        results: list[dict[str, Any]] = []
        success_count = 0
        failed_count = 0
        task_id = options.get("_task_id")
        for customer in customers:
            db.set_customer_add_status(customer["id"], "adding", task_id=task_id, error=None)
            try:
                self.wx.FriendSettings.add_new_friend(
                    number=customer["number"],
                    greetings=customer.get("greetings"),
                    remark=customer.get("remark"),
                    chat_only=bool(options.get("chat_only", False)),
                    is_maximize=options.get("is_maximize"),
                    close_weixin=options.get("close_weixin"),
                )
                db.set_customer_add_status(customer["id"], "added", task_id=task_id, error=None)
                results.append({"id": customer["id"], "number": customer["number"], "status": "added"})
                success_count += 1
            except Exception as exc:
                message = str(exc)
                db.set_customer_add_status(customer["id"], "failed", task_id=task_id, error=message)
                results.append({"id": customer["id"], "number": customer["number"], "status": "failed", "error": message})
                failed_count += 1
        return {"total": len(customers), "success": success_count, "failed": failed_count, "results": results}

    def dispatch(self, task_type: str, payload: dict[str, Any]) -> Any:
        from app.services.uia_enhancer import get_uia_config, uia_enhancer

        if get_uia_config()["enabled"]:
            uia_enhancer.start()
        handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "message.send": lambda p: self.send_messages(p["targets"], p["messages"], p),
            "file.send": lambda p: self.send_files(p["targets"], p["files"], p),
            "contacts.friends": lambda p: self.get_friends(bool(p.get("detail", False))),
            "contacts.friend_detail": lambda p: self.get_friend_detail(p["friend_name"]),
            "contacts.groups": lambda p: self.get_groups(),
            "contacts.group_members": lambda p: self.get_group_members(p["group_name"]),
            "moments.post": lambda p: self.post_moments(p.get("text", ""), p.get("medias", [])),
            "autoreply.start": lambda p: self.start_autoreply(p["target"], p.get("duration", "1min"), p.get("rules", []), bool(p.get("at_only", False))),
            "customers.add_friends": lambda p: self.add_customer_friends(p.get("customer_ids", []), p),
        }
        if task_type not in handlers:
            raise ValueError(f"未知任务类型: {task_type}")
        return handlers[task_type](payload)


weixin_adapter = WeixinAdapter()
