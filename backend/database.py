import aiosqlite
from datetime import datetime
from typing import List, Optional, Dict

DB_PATH = '../calendar.db'


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица событий
        await db.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_token TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                event_date DATE NOT NULL,
                event_time TIME
            )
        ''')

        # Таблица пользователей (только telegram_id и user_token)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                user_token TEXT UNIQUE NOT NULL
            )
        ''')

        # Таблица настроек (только timezone и notifications)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_token TEXT PRIMARY KEY,
                timezone TEXT DEFAULT 'UTC',
                notifications_enabled INTEGER DEFAULT 1
            )
        ''')

        await db.commit()


async def get_or_create_user(telegram_id: int) -> str:
    """Получает или создаёт пользователя, возвращает токен"""
    from utils import generate_user_token

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Проверяем, есть ли пользователь
        cursor = await db.execute('''
            SELECT user_token FROM users WHERE telegram_id = ?
        ''', (telegram_id,))
        row = await cursor.fetchone()

        if row:
            return row['user_token']

        # Создаём нового пользователя
        user_token = generate_user_token(telegram_id)

        await db.execute('''
            INSERT INTO users (telegram_id, user_token)
            VALUES (?, ?)
        ''', (telegram_id, user_token))

        # Создаём настройки по умолчанию
        await db.execute('''
            INSERT INTO user_settings (user_token, timezone, notifications_enabled)
            VALUES (?, ?, ?)
        ''', (user_token, 'UTC', 1))

        await db.commit()
        return user_token


async def get_user_by_token(token: str) -> Optional[Dict]:
    """Получает пользователя по токену"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM users WHERE user_token = ?
        ''', (token,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_token(telegram_id: int) -> Optional[str]:
    """Получает токен пользователя по Telegram ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT user_token FROM users WHERE telegram_id = ?
        ''', (telegram_id,))
        row = await cursor.fetchone()
        return row['user_token'] if row else None


# === Функции для событий ===

async def add_event(user_token: str, title: str, description: str,
                    event_date: str, event_time: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO events (user_token, title, description, event_date, event_time)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_token, title, description, event_date, event_time))
        await db.commit()
        return cursor.lastrowid


async def get_events_by_date(user_token: str, date: str) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM events 
            WHERE user_token = ? AND event_date = ?
            ORDER BY event_time
        ''', (user_token, date))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_events_by_month(user_token: str, year: int, month: int) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM events 
            WHERE user_token = ? 
            AND strftime('%Y', event_date) = ? 
            AND strftime('%m', event_date) = ?
            ORDER BY event_date, event_time
        ''', (user_token, str(year), str(month).zfill(2)))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def delete_event(event_id: int, user_token: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            DELETE FROM events WHERE id = ? AND user_token = ?
        ''', (event_id, user_token))
        await db.commit()
        return cursor.rowcount > 0


async def update_event(event_id: int, user_token: str, **kwargs) -> bool:
    if not kwargs:
        return False
    set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
    values = list(kwargs.values()) + [event_id, user_token]
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(f'''
            UPDATE events SET {set_clause} 
            WHERE id = ? AND user_token = ?
        ''', values)
        await db.commit()
        return cursor.rowcount > 0


async def get_event(event_id: int, user_token: str) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM events WHERE id = ? AND user_token = ?
        ''', (event_id, user_token))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_all_user_events(user_token: str) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM events WHERE user_token = ?
            ORDER BY event_date, event_time
        ''', (user_token,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# === Функции для настроек ===

async def get_user_settings(user_token: str) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM user_settings WHERE user_token = ?
        ''', (user_token,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_user_settings(user_token: str, **kwargs) -> bool:
    if not kwargs:
        return False
    set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
    values = list(kwargs.values()) + [user_token]
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(f'''
            UPDATE user_settings SET {set_clause} 
            WHERE user_token = ?
        ''', values)
        await db.commit()
        return cursor.rowcount > 0