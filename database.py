import aiosqlite
import os
from contextlib import asynccontextmanager

def get_db_path():
    return os.environ.get("DB_PATH", "/data/chores.db")

@asynccontextmanager
async def get_connection():
    conn = await aiosqlite.connect(get_db_path())
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()

async def init_db():
    async with get_connection() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                chore_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS banned_users (
                user_id INTEGER PRIMARY KEY
            )
            """
        )
        await conn.commit()

async def add_chore(user_id: int, username: str | None, chore_text: str) -> int:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "INSERT INTO chores (user_id, username, chore_text) VALUES (?, ?, ?)",
            (user_id, username, chore_text),
        )
        await conn.commit()
        return cursor.lastrowid

async def get_chores(user_id: int, limit: int = 20) -> list[dict]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT id, chore_text, created_at FROM chores WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def clear_chores(user_id: int) -> int:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "DELETE FROM chores WHERE user_id = ?",
            (user_id,),
        )
        await conn.commit()
        return cursor.rowcount

async def is_banned(user_id: int) -> bool:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT 1 FROM banned_users WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return row is not None

async def ban_user(user_id: int):
    async with get_connection() as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)",
            (user_id,),
        )
        await conn.commit()

async def unban_user(user_id: int):
    async with get_connection() as conn:
        await conn.execute(
            "DELETE FROM banned_users WHERE user_id = ?",
            (user_id,),
        )
        await conn.commit()

async def get_stats() -> dict:
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT COUNT(*) as count FROM chores")
        total = await cursor.fetchone()
        cursor = await conn.execute("SELECT COUNT(DISTINCT user_id) as count FROM chores")
        users = await cursor.fetchone()
        return {
            "total_chores": total["count"],
            "active_users": users["count"],
        }
