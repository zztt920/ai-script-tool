"""任务仓库 — 封装 task / script 的数据库 CRUD 操作。"""

import json
import uuid
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from db import get_connection

log = logging.getLogger("adapter.repository")

LOCAL_TZ = timezone(timedelta(hours=8))


class TaskRepository:
    """任务持久化操作。"""

    @staticmethod
    def create(title: str = "", author: str = "", config: dict = None, db_path: str = None) -> dict:
        task_id = str(uuid.uuid4())
        now = datetime.now(LOCAL_TZ).isoformat()
        with get_connection(db_path) as conn:
            conn.execute(
                """INSERT INTO task (id, title, author, status, config, created_at, updated_at)
                   VALUES (?, ?, ?, 'pending', ?, ?, ?)""",
                (task_id, title, author, json.dumps(config or {}, ensure_ascii=False), now, now),
            )
        return {"id": task_id, "status": "pending", "created_at": now}

    @staticmethod
    def update_status(task_id: str, status: str, db_path: str = None, **kwargs) -> dict:
        now = datetime.now(LOCAL_TZ).isoformat()
        fields = ["status = ?", "updated_at = ?"]
        values = [status, now]
        if "error_message" in kwargs:
            fields.append("error_message = ?")
            values.append(kwargs["error_message"])
        if "total_scenes" in kwargs:
            fields.append("total_scenes = ?")
            values.append(kwargs["total_scenes"])
        if "processed_chapters" in kwargs:
            fields.append("processed_chapters = ?")
            values.append(kwargs["processed_chapters"])
        if "total_chapters" in kwargs:
            fields.append("total_chapters = ?")
            values.append(kwargs["total_chapters"])
        if "current_step" in kwargs:
            fields.append("current_step = ?")
            values.append(kwargs["current_step"])
        if "ai_calls" in kwargs:
            fields.append("ai_calls = ?")
            values.append(kwargs["ai_calls"])
        if status == "completed":
            fields.append("completed_at = ?")
            values.append(now)
        values.append(task_id)
        with get_connection(db_path) as conn:
            conn.execute(f"UPDATE task SET {', '.join(fields)} WHERE id = ?", values)
        return {"task_id": task_id, "status": status}

    @staticmethod
    def get(task_id: str, db_path: str = None) -> Optional[dict]:
        with get_connection(db_path) as conn:
            row = conn.execute("SELECT * FROM task WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        return dict(row)

    @staticmethod
    def list(status: str = None, page: int = 1, page_size: int = 20, db_path: str = None) -> dict:
        offset = (page - 1) * page_size
        with get_connection(db_path) as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM task WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (status, page_size, offset),
                ).fetchall()
                total = conn.execute("SELECT COUNT(*) FROM task WHERE status = ?", (status,)).fetchone()[0]
            else:
                rows = conn.execute(
                    "SELECT * FROM task ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (page_size, offset),
                ).fetchall()
                total = conn.execute("SELECT COUNT(*) FROM task").fetchone()[0]
        return {"items": [dict(r) for r in rows], "total": total, "page": page, "page_size": page_size}

    @staticmethod
    def save_chapters(task_id: str, chapters: list, db_path: str = None):
        """批量保存章节。"""
        with get_connection(db_path) as conn:
            conn.execute("DELETE FROM task_chapter WHERE task_id = ?", (task_id,))
            rows = [
                (str(uuid.uuid4()), task_id, ch.index, ch.title, ch.content, len(ch.content))
                for ch in chapters
            ]
            conn.executemany(
                "INSERT INTO task_chapter (id, task_id, chapter_index, title, content, char_count) VALUES (?,?,?,?,?,?)",
                rows,
            )
            conn.execute("UPDATE task SET total_chapters = ?, updated_at = ? WHERE id = ?",
                         (len(chapters), datetime.now(LOCAL_TZ).isoformat(), task_id))

    @staticmethod
    def delete(task_id: str, db_path: str = None):
        """删除任务及关联数据（外键 CASCADE 自动删除 chapters/script/scenes/beats）。"""
        with get_connection(db_path) as conn:
            conn.execute("DELETE FROM task WHERE id = ?", (task_id,))


class ScriptRepository:
    """剧本持久化操作。"""

    @staticmethod
    def create(task_id: str, script_dict: dict, yaml_path: str = "", db_path: str = None) -> dict:
        script_id = str(uuid.uuid4())
        meta = script_dict.get("meta", {})
        total_scenes = len(script_dict.get("scenes", []))
        total_beats = sum(len(s.get("beats", [])) for s in script_dict.get("scenes", []))
        now = datetime.now(LOCAL_TZ).isoformat()

        with get_connection(db_path) as conn:
            conn.execute(
                """INSERT INTO script (id, task_id, yaml_path, meta, total_scenes, total_beats, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (script_id, task_id, yaml_path, json.dumps(meta, ensure_ascii=False),
                 total_scenes, total_beats, now),
            )
            # 存储 scenes 和 beats
            for scene in script_dict.get("scenes", []):
                sid = f"scene_{script_id}_{scene['scene_id']}"
                conn.execute(
                    """INSERT INTO scene (id, script_id, scene_number, episode, location, time_of_day, interior_exterior,
                       scene_function, emotional_tone, summary, source_chapter)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (sid, script_id, scene["scene_id"], scene.get("episode", 1),
                     scene.get("scene_heading", {}).get("location", ""),
                     scene.get("scene_heading", {}).get("time", "日"),
                     scene.get("scene_heading", {}).get("interior_exterior", "内"),
                     scene.get("scene_function", ""), scene.get("emotional_tone", ""),
                     scene.get("summary", ""),
                     scene.get("source_reference", {}).get("novel_chapter", 0)),
                )
                for j, beat in enumerate(scene.get("beats", [])):
                    bid = str(uuid.uuid4())  # 始终用 UUID 确保全局唯一
                    conn.execute(
                        """INSERT INTO beat (id, scene_id, sequence, beat_type, character_id, content,
                           subtext, emotion, parenthetical, camera_hint)
                           VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (bid, sid, j + 1,
                         beat.get("beat_type", ""), beat.get("character_id", ""),
                         beat.get("content", ""), beat.get("subtext", ""),
                         beat.get("emotion", ""), beat.get("parenthetical", ""),
                         beat.get("camera_hint", "")),
                    )
        return {"id": script_id, "task_id": task_id, "total_scenes": total_scenes}

    @staticmethod
    def get_by_task(task_id: str, db_path: str = None) -> Optional[dict]:
        with get_connection(db_path) as conn:
            row = conn.execute("SELECT * FROM script WHERE task_id = ?", (task_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def save_validation(script_id: str, report: dict, db_path: str = None):
        with get_connection(db_path) as conn:
            conn.execute("UPDATE script SET validation_report = ? WHERE id = ?",
                         (json.dumps(report, ensure_ascii=False), script_id))
