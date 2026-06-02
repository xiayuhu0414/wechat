from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from app.core.config import BASE_DIR, DATA_DIR, settings


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def encode_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def decode_json(value: str | None, default: Any = None) -> Any:
    if value is None:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def get_app_setting(key: str, default: Any = None) -> Any:
    with connect() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    return decode_json(row["value"], default)


def get_app_settings(prefix: str) -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT key, value FROM app_settings WHERE key LIKE ?",
            (f"{prefix}%",),
        ).fetchall()
    return {row["key"]: decode_json(row["value"]) for row in rows}


def set_app_setting(key: str, value: Any) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)",
            (key, encode_json(value), utc_now()),
        )


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    settings.ensure_dirs()
    conn = sqlite3.connect(settings.database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                status TEXT NOT NULL,
                payload TEXT NOT NULL,
                result TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT
            );

            CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS autoreply_rules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                target TEXT NOT NULL,
                target_type TEXT NOT NULL,
                keyword TEXT NOT NULL,
                reply TEXT NOT NULL,
                at_only INTEGER NOT NULL DEFAULT 0,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS friends_cache (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                wx_number TEXT,
                remark TEXT,
                phone TEXT,
                region TEXT,
                raw TEXT NOT NULL DEFAULT '{}',
                last_synced_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS groups_cache (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                member_count INTEGER,
                raw TEXT NOT NULL DEFAULT '{}',
                last_synced_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS contact_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_type TEXT NOT NULL CHECK(target_type IN ('friend', 'group')),
                target_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(target_type, target_id, tag)
            );

            CREATE TABLE IF NOT EXISTS group_members_cache (
                id TEXT PRIMARY KEY,
                group_id TEXT NOT NULL,
                group_name TEXT NOT NULL,
                name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                raw TEXT NOT NULL DEFAULT '{}',
                last_synced_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS customer_imports (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                path TEXT NOT NULL,
                sheet_name TEXT,
                mapping TEXT NOT NULL DEFAULT '{}',
                row_count INTEGER NOT NULL DEFAULT 0,
                imported_count INTEGER NOT NULL DEFAULT 0,
                updated_count INTEGER NOT NULL DEFAULT 0,
                skipped_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS customers (
                id TEXT PRIMARY KEY,
                number TEXT NOT NULL,
                normalized_number TEXT NOT NULL UNIQUE,
                greetings TEXT,
                remark TEXT,
                raw TEXT NOT NULL DEFAULT '{}',
                source_filename TEXT,
                source_sheet TEXT,
                source_row INTEGER,
                import_id TEXT,
                add_status TEXT NOT NULL DEFAULT 'pending',
                last_add_task_id TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_friends_cache_name ON friends_cache(name);
            CREATE INDEX IF NOT EXISTS idx_friends_cache_display_name ON friends_cache(display_name);
            CREATE INDEX IF NOT EXISTS idx_groups_cache_name ON groups_cache(name);
            CREATE INDEX IF NOT EXISTS idx_contact_tags_target ON contact_tags(target_type, target_id);
            CREATE INDEX IF NOT EXISTS idx_contact_tags_tag ON contact_tags(tag);
            CREATE INDEX IF NOT EXISTS idx_group_members_cache_group ON group_members_cache(group_id);
            CREATE INDEX IF NOT EXISTS idx_group_members_cache_name ON group_members_cache(name);
            CREATE INDEX IF NOT EXISTS idx_customers_number ON customers(normalized_number);
            CREATE INDEX IF NOT EXISTS idx_customers_add_status ON customers(add_status);
            CREATE INDEX IF NOT EXISTS idx_customers_import_id ON customers(import_id);
            """
        )
    migrate_legacy_contact_cache()


def normalize_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return _dedupe_tags(value)
    if isinstance(value, str):
        if not value.strip() or value.strip() == "无":
            return []
        text = value
        for separator in (";", "；", ",", "，", "|", "、", "\n", "\t"):
            text = text.replace(separator, ";")
        return _dedupe_tags(text.split(";"))
    return _dedupe_tags([str(value)])


def _dedupe_tags(values: Any) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()
    for value in values:
        tag = str(value).strip()
        if tag and tag not in seen:
            tags.append(tag)
            seen.add(tag)
    return tags


def _friend_id(name: str) -> str:
    return f"friend:{name}"


def _group_id(name: str) -> str:
    return f"group:{name}"


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "无":
        return None
    return text


def _name_from_friend(item: dict[str, Any]) -> str:
    return str(
        _clean_text(item.get("name"))
        or _clean_text(item.get("remark"))
        or _clean_text(item.get("备注"))
        or _clean_text(item.get("display_name"))
        or _clean_text(item.get("昵称"))
        or ""
    ).strip()


def _name_from_group(item: dict[str, Any]) -> str:
    return str(item.get("name") or item.get("display_name") or item.get("群名") or "").strip()


def _set_tags(conn: sqlite3.Connection, target_type: str, target_id: str, tags: list[str]) -> None:
    now = utc_now()
    conn.execute("DELETE FROM contact_tags WHERE target_type = ? AND target_id = ?", (target_type, target_id))
    conn.executemany(
        "INSERT OR IGNORE INTO contact_tags (target_type, target_id, tag, created_at) VALUES (?, ?, ?, ?)",
        [(target_type, target_id, tag, now) for tag in normalize_tags(tags)],
    )


def _tags_by_target(conn: sqlite3.Connection, target_type: str, target_ids: list[str]) -> dict[str, list[str]]:
    if not target_ids:
        return {}
    placeholders = ",".join("?" for _ in target_ids)
    rows = conn.execute(
        f"""
        SELECT target_id, tag
        FROM contact_tags
        WHERE target_type = ? AND target_id IN ({placeholders})
        ORDER BY tag ASC
        """,
        [target_type, *target_ids],
    ).fetchall()
    result: dict[str, list[str]] = {target_id: [] for target_id in target_ids}
    for row in rows:
        result.setdefault(row["target_id"], []).append(row["tag"])
    return result


def upsert_friend_cache(item: dict[str, Any]) -> None:
    now = utc_now()
    name = _name_from_friend(item)
    if not name:
        return
    contact_id = _friend_id(name)
    display_name = _clean_text(item.get("display_name")) or _clean_text(item.get("昵称")) or name
    remark = _clean_text(item.get("remark")) or _clean_text(item.get("备注"))
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO friends_cache
            (id, name, display_name, wx_number, remark, phone, region, raw, last_synced_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                display_name = excluded.display_name,
                wx_number = excluded.wx_number,
                remark = excluded.remark,
                phone = excluded.phone,
                region = excluded.region,
                raw = excluded.raw,
                last_synced_at = excluded.last_synced_at,
                updated_at = excluded.updated_at
            """,
            (
                contact_id,
                name,
                display_name,
                _clean_text(item.get("wx_number")) or _clean_text(item.get("微信号")),
                remark,
                _clean_text(item.get("phone")) or _clean_text(item.get("电话")),
                _clean_text(item.get("region")) or _clean_text(item.get("地区")),
                encode_json(item),
                now,
                now,
            ),
        )
        if "tags" in item or "标签" in item:
            _set_tags(conn, "friend", contact_id, normalize_tags(item.get("tags") or item.get("标签")))


def upsert_group_cache(item: dict[str, Any]) -> None:
    now = utc_now()
    name = _name_from_group(item)
    if not name:
        return
    contact_id = _group_id(name)
    display_name = str(item.get("display_name") or item.get("群名") or name)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO groups_cache
            (id, name, display_name, member_count, raw, last_synced_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                display_name = excluded.display_name,
                member_count = COALESCE(excluded.member_count, groups_cache.member_count),
                raw = excluded.raw,
                last_synced_at = excluded.last_synced_at,
                updated_at = excluded.updated_at
            """,
            (
                contact_id,
                name,
                display_name,
                item.get("member_count"),
                encode_json(item),
                now,
                now,
            ),
        )
        if "tags" in item or "标签" in item:
            _set_tags(conn, "group", contact_id, normalize_tags(item.get("tags") or item.get("标签")))


def upsert_contact_cache(contact_type: str, item: dict[str, Any]) -> None:
    if contact_type == "friend":
        upsert_friend_cache(item)
    elif contact_type == "group":
        upsert_group_cache(item)
    else:
        raise ValueError(f"Unsupported contact type: {contact_type}")


def update_contact_tags(contact_type: str, name: str, tags: list[str]) -> dict[str, Any]:
    if contact_type not in {"friend", "group"}:
        raise ValueError("contact_type must be friend or group")
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("name is required")
    contact_id = _friend_id(clean_name) if contact_type == "friend" else _group_id(clean_name)
    if contact_type == "friend":
        upsert_friend_cache({"name": clean_name, "display_name": clean_name})
    else:
        upsert_group_cache({"name": clean_name, "display_name": clean_name})
    with connect() as conn:
        _set_tags(conn, contact_type, contact_id, tags)
    return {"type": contact_type, "name": clean_name, "tags": normalize_tags(tags)}


def list_contact_tags(contact_type: str | None = None) -> list[str]:
    sql = "SELECT DISTINCT tag FROM contact_tags WHERE 1=1"
    params: list[Any] = []
    if contact_type:
        sql += " AND target_type = ?"
        params.append(contact_type)
    sql += " ORDER BY tag ASC"
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [row["tag"] for row in rows]


def upsert_group_members_cache(group_name: str, members: list[Any]) -> int:
    clean_group_name = group_name.strip()
    if not clean_group_name:
        return 0
    group_id = _group_id(clean_group_name)
    now = utc_now()
    rows: list[tuple[str, str, str, str, str, str, str, str]] = []
    seen: set[str] = set()
    for index, member in enumerate(members):
        raw = member
        if isinstance(member, dict):
            name = (
                _clean_text(member.get("name"))
                or _clean_text(member.get("display_name"))
                or _clean_text(member.get("群昵称"))
                or _clean_text(member.get("昵称"))
                or f"成员{index + 1}"
            )
            display_name = _clean_text(member.get("display_name")) or _clean_text(member.get("群昵称")) or _clean_text(member.get("昵称")) or name
        else:
            name = _clean_text(member) or f"成员{index + 1}"
            display_name = name
        member_id = f"{group_id}:{name}"
        if member_id in seen:
            continue
        seen.add(member_id)
        rows.append((member_id, group_id, clean_group_name, name, display_name, encode_json(raw), now, now))
    with connect() as conn:
        conn.execute("DELETE FROM group_members_cache WHERE group_id = ?", (group_id,))
        conn.executemany(
            """
            INSERT INTO group_members_cache
            (id, group_id, group_name, name, display_name, raw, last_synced_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)


def list_group_members_cache(group_name: str) -> list[dict[str, Any]]:
    group_id = _group_id(group_name.strip())
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM group_members_cache
            WHERE group_id = ?
            ORDER BY name ASC
            """,
            (group_id,),
        ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["raw"] = decode_json(item.get("raw"), {})
        items.append(item)
    return items


def list_friends_cache(keyword: str | None = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM friends_cache WHERE 1=1"
    params: list[Any] = []
    if keyword:
        sql += " AND (name LIKE ? OR display_name LIKE ? OR remark LIKE ? OR wx_number LIKE ? OR phone LIKE ? OR region LIKE ?)"
        like = f"%{keyword}%"
        params.extend([like, like, like, like, like, like])
    sql += " ORDER BY name ASC"
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        tags = _tags_by_target(conn, "friend", [row["id"] for row in rows])
    return [_friend_row_to_dict(row, tags.get(row["id"], [])) for row in rows]


def list_groups_cache(keyword: str | None = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM groups_cache WHERE 1=1"
    params: list[Any] = []
    if keyword:
        sql += " AND (name LIKE ? OR display_name LIKE ?)"
        like = f"%{keyword}%"
        params.extend([like, like])
    sql += " ORDER BY name ASC"
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        tags = _tags_by_target(conn, "group", [row["id"] for row in rows])
    return [_group_row_to_dict(row, tags.get(row["id"], [])) for row in rows]


def list_contact_cache(contact_type: str | None = None, keyword: str | None = None) -> list[dict[str, Any]]:
    if contact_type == "friend":
        return list_friends_cache(keyword)
    if contact_type == "group":
        return list_groups_cache(keyword)
    return [*list_friends_cache(keyword), *list_groups_cache(keyword)]


def normalize_customer_number(value: Any) -> str:
    text = _clean_text(value) or ""
    if text.endswith(".0"):
        text = text[:-2]
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits


def create_customer_import(
    import_id: str,
    filename: str,
    path: str,
    sheet_name: str | None,
    mapping: dict[str, Any],
    row_count: int,
    imported_count: int,
    updated_count: int,
    skipped_count: int,
) -> dict[str, Any]:
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO customer_imports
            (id, filename, path, sheet_name, mapping, row_count, imported_count, updated_count, skipped_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                import_id,
                filename,
                path,
                sheet_name,
                encode_json(mapping),
                row_count,
                imported_count,
                updated_count,
                skipped_count,
                now,
            ),
        )
    return {
        "id": import_id,
        "filename": filename,
        "path": path,
        "sheet_name": sheet_name,
        "mapping": mapping,
        "row_count": row_count,
        "imported_count": imported_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "created_at": now,
    }


def upsert_customers(records: list[dict[str, Any]]) -> dict[str, int]:
    imported = 0
    updated = 0
    skipped = 0
    now = utc_now()
    with connect() as conn:
        for record in records:
            normalized = normalize_customer_number(record.get("number"))
            if not normalized:
                skipped += 1
                continue
            existing = conn.execute(
                "SELECT id FROM customers WHERE normalized_number = ?",
                (normalized,),
            ).fetchone()
            customer_id = f"customer:{normalized}"
            conn.execute(
                """
                INSERT INTO customers
                (id, number, normalized_number, greetings, remark, raw, source_filename, source_sheet, source_row, import_id, add_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                ON CONFLICT(normalized_number) DO UPDATE SET
                    number = excluded.number,
                    greetings = COALESCE(NULLIF(excluded.greetings, ''), customers.greetings),
                    remark = COALESCE(NULLIF(excluded.remark, ''), customers.remark),
                    raw = excluded.raw,
                    source_filename = excluded.source_filename,
                    source_sheet = excluded.source_sheet,
                    source_row = excluded.source_row,
                    import_id = excluded.import_id,
                    updated_at = excluded.updated_at
                """,
                (
                    customer_id,
                    str(record.get("number") or normalized),
                    normalized,
                    _clean_text(record.get("greetings")),
                    _clean_text(record.get("remark")),
                    encode_json(record.get("raw") or {}),
                    _clean_text(record.get("source_filename")),
                    _clean_text(record.get("source_sheet")),
                    record.get("source_row"),
                    record.get("import_id"),
                    now,
                    now,
                ),
            )
            if existing:
                updated += 1
            else:
                imported += 1
    return {"imported_count": imported, "updated_count": updated, "skipped_count": skipped}


def list_customers(
    keyword: str | None = None,
    add_status: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM customers WHERE 1=1"
    params: list[Any] = []
    if keyword:
        sql += " AND (number LIKE ? OR normalized_number LIKE ? OR greetings LIKE ? OR remark LIKE ? OR raw LIKE ?)"
        like = f"%{keyword}%"
        params.extend([like, like, like, like, like])
    if add_status:
        sql += " AND add_status = ?"
        params.append(add_status)
    sql += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_customer_row_to_dict(row) for row in rows]


def count_customers(keyword: str | None = None, add_status: str | None = None) -> int:
    sql = "SELECT COUNT(*) AS count FROM customers WHERE 1=1"
    params: list[Any] = []
    if keyword:
        sql += " AND (number LIKE ? OR normalized_number LIKE ? OR greetings LIKE ? OR remark LIKE ? OR raw LIKE ?)"
        like = f"%{keyword}%"
        params.extend([like, like, like, like, like])
    if add_status:
        sql += " AND add_status = ?"
        params.append(add_status)
    with connect() as conn:
        row = conn.execute(sql, params).fetchone()
    return int(row["count"] if row else 0)


def list_customers_by_ids(customer_ids: list[str]) -> list[dict[str, Any]]:
    if not customer_ids:
        return []
    placeholders = ",".join("?" for _ in customer_ids)
    with connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM customers WHERE id IN ({placeholders}) ORDER BY updated_at DESC",
            customer_ids,
        ).fetchall()
    return [_customer_row_to_dict(row) for row in rows]


def set_customer_add_status(
    customer_id: str,
    add_status: str,
    task_id: str | None = None,
    error: str | None = None,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE customers
            SET add_status = ?, last_add_task_id = COALESCE(?, last_add_task_id), last_error = ?, updated_at = ?
            WHERE id = ?
            """,
            (add_status, task_id, error, utc_now(), customer_id),
        )


def update_customer_greetings(
    greetings: str,
    customer_ids: list[str] | None = None,
    keyword: str | None = None,
    add_status: str | None = None,
) -> dict[str, int]:
    sql = "UPDATE customers SET greetings = ?, updated_at = ? WHERE 1=1"
    params: list[Any] = [greetings, utc_now()]
    if customer_ids:
        placeholders = ",".join("?" for _ in customer_ids)
        sql += f" AND id IN ({placeholders})"
        params.extend(customer_ids)
    else:
        if keyword:
            sql += " AND (number LIKE ? OR normalized_number LIKE ? OR greetings LIKE ? OR remark LIKE ? OR raw LIKE ?)"
            like = f"%{keyword}%"
            params.extend([like, like, like, like, like])
        if add_status:
            sql += " AND add_status = ?"
            params.append(add_status)
    with connect() as conn:
        cursor = conn.execute(sql, params)
        return {"updated": int(cursor.rowcount if cursor.rowcount is not None else 0)}


def update_customer(customer_id: str, values: dict[str, Any]) -> dict[str, Any]:
    allowed = {"number", "greetings", "remark", "add_status"}
    updates = {key: values[key] for key in allowed if key in values}
    if not updates:
        raise ValueError("No fields to update")
    if "number" in updates:
        normalized = normalize_customer_number(updates["number"])
        if not normalized:
            raise ValueError("number is required")
        updates["normalized_number"] = normalized
    updates["updated_at"] = utc_now()
    assignments = ", ".join(f"{key} = ?" for key in updates)
    params = list(updates.values()) + [customer_id]
    with connect() as conn:
        try:
            conn.execute(f"UPDATE customers SET {assignments} WHERE id = ?", params)
        except sqlite3.IntegrityError as exc:
            raise ValueError("number already exists") from exc
        row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    if row is None:
        raise KeyError(customer_id)
    return _customer_row_to_dict(row)


def _customer_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["raw"] = decode_json(item.get("raw"), {})
    return item


def clear_friends_cache() -> dict[str, int]:
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) AS count FROM friends_cache").fetchone()["count"]
        conn.execute("DELETE FROM contact_tags WHERE target_type = 'friend'")
        conn.execute("DELETE FROM friends_cache")
    return {"deleted": int(count)}


def clear_groups_cache() -> dict[str, int]:
    with connect() as conn:
        group_count = conn.execute("SELECT COUNT(*) AS count FROM groups_cache").fetchone()["count"]
        member_count = conn.execute("SELECT COUNT(*) AS count FROM group_members_cache").fetchone()["count"]
        conn.execute("DELETE FROM contact_tags WHERE target_type = 'group'")
        conn.execute("DELETE FROM group_members_cache")
        conn.execute("DELETE FROM groups_cache")
    return {"deleted": int(group_count), "members_deleted": int(member_count)}


def _friend_row_to_dict(row: sqlite3.Row, tags: list[str]) -> dict[str, Any]:
    item = dict(row)
    item["type"] = "friend"
    item["member_count"] = None
    item["tags"] = tags
    item["raw"] = decode_json(item.get("raw"), {})
    if item.get("remark") == item.get("name"):
        item["remark"] = None
    return item


def _group_row_to_dict(row: sqlite3.Row, tags: list[str]) -> dict[str, Any]:
    item = dict(row)
    item["type"] = "group"
    item["wx_number"] = None
    item["remark"] = None
    item["phone"] = None
    item["region"] = None
    item["tags"] = tags
    item["raw"] = decode_json(item.get("raw"), {})
    return item


def _legacy_database_candidates() -> list[Path]:
    candidates = [
        settings.database_path,
        BASE_DIR / "data" / "app.db",
        BASE_DIR / "dist" / "autoWechat Console" / "data" / "app.db",
        BASE_DIR.parent / "data" / "app.db",
        BASE_DIR.parent.parent / "data" / "app.db",
    ]
    result: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            key = str(candidate.resolve())
        except OSError:
            key = str(candidate)
        if key not in seen:
            result.append(candidate)
            seen.add(key)
    return result


def migrate_legacy_contact_cache() -> None:
    if settings.database_path != DATA_DIR / "app.db":
        candidates = [settings.database_path]
    else:
        candidates = _legacy_database_candidates()
    for path in candidates:
        if path.exists():
            _migrate_contacts_cache_from(path)


def _migrate_contacts_cache_from(path: Path) -> None:
    legacy: sqlite3.Connection | None = None
    try:
        legacy = sqlite3.connect(path)
        legacy.row_factory = sqlite3.Row
        table = legacy.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'contacts_cache'"
        ).fetchone()
        if not table:
            return
        rows = legacy.execute("SELECT * FROM contacts_cache").fetchall()
    except sqlite3.Error:
        return
    finally:
        if legacy is not None:
            legacy.close()

    for row in rows:
        item = dict(row)
        raw = decode_json(item.get("raw"), {})
        if isinstance(raw, dict):
            raw.update(item)
            item = raw
        item["tags"] = decode_json(item.get("tags"), normalize_tags(item.get("tags")))
        if item.get("type") == "friend":
            upsert_friend_cache(item)
        elif item.get("type") == "group":
            upsert_group_cache(item)


def row_to_task(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "type": row["type"],
        "status": row["status"],
        "payload": decode_json(row["payload"], {}),
        "result": decode_json(row["result"], None),
        "error": row["error"],
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
    }
