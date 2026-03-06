import aiosqlite
from datetime import datetime
from typing import List, Optional, Dict

DB_PATH = 'calendar.db'

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                event_date DATE NOT NULL,
                event_time TIME,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                timezone TEXT DEFAULT 'UTC',
                notifications_enabled INTEGER DEFAULT 1
            )
        ''')
        await db.commit()

async def add_event(user_id: int, title: str, description: str,
                    event_date: str, event_time: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO events (user_id, title, description, event_date, event_time)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, title, description, event_date, event_time))
        await db.commit()
        return cursor.lastrowid

async def get_events_by_date(user_id: int, date: str) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM events 
            WHERE user_id = ? AND event_date = ?
            ORDER BY event_time
        ''', (user_id, date))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_events_by_month(user_id: int, year: int, month: int) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM events 
            WHERE user_id = ? 
            AND strftime('%Y', event_date) = ? 
            AND strftime('%m', event_date) = ?
            ORDER BY event_date, event_time
        ''', (user_id, str(year), str(month).zfill(2)))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def delete_event(event_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            DELETE FROM events WHERE id = ? AND user_id = ?
        ''', (event_id, user_id))
        await db.commit()
        return cursor.rowcount > 0

async def update_event(event_id: int, user_id: int, **kwargs) -> bool:
    if not kwargs:
        return False
    set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
    values = list(kwargs.values()) + [event_id, user_id]
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(f'''
            UPDATE events SET {set_clause} 
            WHERE id = ? AND user_id = ?
        ''', values)
        await db.commit()
        return cursor.rowcount > 0

async def get_event(event_id: int, user_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM events WHERE id = ? AND user_id = ?
        ''', (event_id, user_id))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_all_user_events(user_id: int) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM events WHERE user_id = ?
            ORDER BY event_date, event_time
        ''', (user_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
