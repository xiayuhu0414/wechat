from __future__ import annotations

from app.core import db
from app.tasks.manager import task_manager


def test_friends_and_groups_use_separate_cache_tables(monkeypatch, tmp_path):
    monkeypatch.setattr(db.settings, "database_path", tmp_path / "app.db")
    db.init_db()

    db.upsert_friend_cache({"name": "Alice", "display_name": "Alice", "tags": ["vip"]})
    db.upsert_group_cache({"name": "Team", "display_name": "Team", "member_count": 3, "tags": ["work"]})

    friends = db.list_friends_cache()
    groups = db.list_groups_cache()
    combined = db.list_contact_cache()

    assert friends[0]["type"] == "friend"
    assert friends[0]["tags"] == ["vip"]
    assert groups[0]["type"] == "group"
    assert groups[0]["member_count"] == 3
    assert groups[0]["tags"] == ["work"]
    assert {item["type"] for item in combined} == {"friend", "group"}


def test_contact_tags_can_be_replaced(monkeypatch, tmp_path):
    monkeypatch.setattr(db.settings, "database_path", tmp_path / "app.db")
    db.init_db()

    db.update_contact_tags("friend", "Alice", ["first", "second"])
    db.update_contact_tags("friend", "Alice", ["second"])

    assert db.list_friends_cache()[0]["tags"] == ["second"]
    assert db.list_contact_tags("friend") == ["second"]


def test_duplicate_friend_name_and_remark_is_hidden(monkeypatch, tmp_path):
    monkeypatch.setattr(db.settings, "database_path", tmp_path / "app.db")
    db.init_db()

    db.upsert_friend_cache({"name": "Alice", "display_name": "Alice Nick", "remark": "Alice"})

    friend = db.list_friends_cache()[0]
    assert friend["name"] == "Alice"
    assert friend["display_name"] == "Alice Nick"
    assert friend["remark"] is None


def test_group_members_are_cached_separately(monkeypatch, tmp_path):
    monkeypatch.setattr(db.settings, "database_path", tmp_path / "app.db")
    db.init_db()

    count = db.upsert_group_members_cache("Team", ["Alice", "Bob", "Alice"])
    members = db.list_group_members_cache("Team")

    assert count == 2
    assert [member["name"] for member in members] == ["Alice", "Bob"]


def test_clear_friend_and_group_caches_are_separate(monkeypatch, tmp_path):
    monkeypatch.setattr(db.settings, "database_path", tmp_path / "app.db")
    db.init_db()

    db.upsert_friend_cache({"name": "Alice", "display_name": "Alice", "tags": ["vip"]})
    db.upsert_group_cache({"name": "Team", "display_name": "Team", "tags": ["work"]})
    db.upsert_group_members_cache("Team", ["Alice"])

    friend_result = db.clear_friends_cache()

    assert friend_result == {"deleted": 1}
    assert db.list_friends_cache() == []
    assert len(db.list_groups_cache()) == 1
    assert db.list_contact_tags("friend") == []
    assert db.list_contact_tags("group") == ["work"]

    group_result = db.clear_groups_cache()

    assert group_result == {"deleted": 1, "members_deleted": 1}
    assert db.list_groups_cache() == []
    assert db.list_group_members_cache("Team") == []
    assert db.list_contact_tags("group") == []


def test_task_statistics_are_grouped_by_category(monkeypatch, tmp_path):
    monkeypatch.setattr(db.settings, "database_path", tmp_path / "app.db")
    db.init_db()

    with db.connect() as conn:
        conn.execute(
            "INSERT INTO tasks (id, type, status, payload, created_at, started_at, finished_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("1", "message.send", "success", "{}", "2026-05-31T10:00:00Z", "2026-05-31T10:00:00Z", "2026-05-31T10:00:02Z"),
        )
        conn.execute(
            "INSERT INTO tasks (id, type, status, payload, created_at, error) VALUES (?, ?, ?, ?, ?, ?)",
            ("2", "contacts.groups", "failed", "{}", "2026-05-31T10:01:00Z", "boom"),
        )

    stats = task_manager.statistics()

    assert stats["summary"]["total"] == 2
    assert stats["summary"]["success_rate"] == 50
    categories = {row["key"]: row for row in stats["categories"]}
    assert categories["message"]["success"] == 1
    assert categories["contacts"]["failed"] == 1
