"""数据库初始化与连接管理。"""

import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DEFAULT_DB_PATH = str(Path(__file__).parent.parent / "data" / "script_tool.db")


@contextmanager
def get_connection(db_path: str = None):
    """获取 SQLite 连接（上下文管理器）。"""
    path = db_path or os.getenv("SCRIPT_DB_PATH", DEFAULT_DB_PATH)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str = None):
    """初始化数据库表。"""
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        # 现有表格的迁移
        try:
            conn.execute("ALTER TABLE task ADD COLUMN current_step TEXT DEFAULT ''")
        except Exception:
            pass  # 列已存在
        # 插入状态枚举
        conn.executemany(
            "INSERT OR IGNORE INTO task_status (id, label) VALUES (?, ?)",
            [("pending", "待处理"), ("processing", "处理中"), ("completed", "已完成"), ("failed", "失败")],
        )


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS task_status (
    id    TEXT PRIMARY KEY,
    label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task (
    id                  TEXT PRIMARY KEY,
    title               TEXT NOT NULL DEFAULT '',
    author              TEXT NOT NULL DEFAULT '',
    status              TEXT NOT NULL DEFAULT 'pending' REFERENCES task_status(id),
    script_type         TEXT NOT NULL DEFAULT 'tv_series',
    ai_model            TEXT NOT NULL DEFAULT 'deepseek-v4-flash',
    config              TEXT DEFAULT '{}',
    total_chapters      INTEGER DEFAULT 0,
    processed_chapters  INTEGER DEFAULT 0,
    total_scenes        INTEGER DEFAULT 0,
    current_step        TEXT DEFAULT '',
    error_message       TEXT,
    ai_cost             REAL DEFAULT 0.0,
    ai_calls            INTEGER DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at        TEXT
);

CREATE INDEX IF NOT EXISTS idx_task_status  ON task(status);
CREATE INDEX IF NOT EXISTS idx_task_created ON task(created_at);

CREATE TABLE IF NOT EXISTS task_chapter (
    id             TEXT PRIMARY KEY,
    task_id        TEXT NOT NULL REFERENCES task(id) ON DELETE CASCADE,
    chapter_index  INTEGER NOT NULL,
    title          TEXT NOT NULL DEFAULT '',
    content        TEXT NOT NULL DEFAULT '',
    char_count     INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tc_task          ON task_chapter(task_id, chapter_index);
CREATE UNIQUE INDEX IF NOT EXISTS uq_tc_task_chapter ON task_chapter(task_id, chapter_index);

CREATE TABLE IF NOT EXISTS script (
    id                TEXT PRIMARY KEY,
    task_id           TEXT NOT NULL UNIQUE REFERENCES task(id) ON DELETE CASCADE,
    yaml_path         TEXT,
    meta              TEXT DEFAULT '{}',
    script_version    TEXT DEFAULT '0.1.0',
    total_scenes      INTEGER DEFAULT 0,
    total_beats       INTEGER DEFAULT 0,
    validation_report TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scene (
    id                TEXT PRIMARY KEY,
    script_id         TEXT NOT NULL REFERENCES script(id) ON DELETE CASCADE,
    scene_number      INTEGER NOT NULL,
    episode           INTEGER DEFAULT 1,
    location          TEXT NOT NULL DEFAULT '',
    time_of_day       TEXT NOT NULL DEFAULT '日',
    interior_exterior TEXT NOT NULL DEFAULT '内',
    scene_function    TEXT DEFAULT '',
    emotional_tone    TEXT DEFAULT '',
    summary           TEXT DEFAULT '',
    source_chapter    INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_scene_script ON scene(script_id, scene_number);

CREATE TABLE IF NOT EXISTS beat (
    id            TEXT PRIMARY KEY,
    scene_id      TEXT NOT NULL REFERENCES scene(id) ON DELETE CASCADE,
    sequence      INTEGER NOT NULL,
    beat_type     TEXT NOT NULL DEFAULT 'description',
    character_id  TEXT DEFAULT '',
    content       TEXT NOT NULL DEFAULT '',
    subtext       TEXT DEFAULT '',
    emotion       TEXT DEFAULT '',
    parenthetical TEXT DEFAULT '',
    camera_hint   TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_beat_scene ON beat(scene_id, sequence);

-- 用户表
CREATE TABLE IF NOT EXISTS user (
    id             TEXT PRIMARY KEY,
    username       TEXT NOT NULL UNIQUE,
    email          TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    nickname       TEXT DEFAULT '',
    avatar_url     TEXT DEFAULT '',
    role           TEXT NOT NULL DEFAULT 'user',
    status         TEXT NOT NULL DEFAULT 'active',
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at     TEXT NOT NULL DEFAULT (datetime('now')),
    last_login_at  TEXT
);

CREATE INDEX IF NOT EXISTS idx_user_username ON user(username);
CREATE INDEX IF NOT EXISTS idx_user_email ON user(email);

-- 用户角色枚举
CREATE TABLE IF NOT EXISTS user_role (
    id    TEXT PRIMARY KEY,
    label TEXT NOT NULL
);

INSERT OR IGNORE INTO user_role (id, label) VALUES 
    ('admin', '管理员'), 
    ('user', '普通用户');

-- 用户状态枚举
CREATE TABLE IF NOT EXISTS user_status (
    id    TEXT PRIMARY KEY,
    label TEXT NOT NULL
);

INSERT OR IGNORE INTO user_status (id, label) VALUES 
    ('active', '活跃'), 
    ('inactive', '未激活'), 
    ('banned', '封禁');
"""
