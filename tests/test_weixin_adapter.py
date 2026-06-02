from __future__ import annotations

from app.adapters.weixin_adapter import WeixinAdapter
from app.core import db


class FakeContacts:
    def get_friends_detail(self, is_json=False, close_weixin=False):
        raise LookupError("profile_view hidden")

    def get_friends_name(self, close_weixin=False):
        return ["Alice", "Bob"]

    def get_friend_profile(self, friend, close_weixin=False):
        if friend == "Bob":
            raise LookupError("not found")
        return {"昵称": "Alice Nick", "备注": "Alice", "微信号": "alice_wx", "电话": "13800138000"}


class FakeWx:
    Contacts = FakeContacts()


def test_detail_sync_falls_back_to_single_friend_profiles(monkeypatch, tmp_path):
    monkeypatch.setattr(db.settings, "database_path", tmp_path / "app.db")
    db.init_db()

    adapter = WeixinAdapter()
    adapter._module = FakeWx()
    adapter._defaults_applied = True

    result = adapter.get_friends(detail=True)
    friends = {friend["name"]: friend for friend in db.list_friends_cache()}

    assert result["mode"] == "fallback_one_by_one"
    assert result["total"] == 2
    assert result["updated"] == 1
    assert result["failed"] == 1
    assert friends["Alice"]["display_name"] == "Alice Nick"
    assert friends["Alice"]["wx_number"] == "alice_wx"
    assert friends["Bob"]["display_name"] == "Bob"
