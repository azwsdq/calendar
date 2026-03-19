import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncpg
import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from config import DATABASE_URL, AUTH_TOKEN_TTL

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                user_token TEXT UNIQUE NOT NULL,
                first_name TEXT,
                username TEXT
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                user_token TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                event_date DATE NOT NULL,
                event_time TIME
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_token TEXT PRIMARY KEY,
                timezone TEXT DEFAULT 'UTC',
                notifications_enabled BOOLEAN DEFAULT TRUE
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS auth_tokens (
                token TEXT PRIMARY KEY,
                user_token TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE
            )
        ''')


# === Пользователи ===

async def get_or_create_user(telegram_id: int, first_name: str = None, username: str = None) -> str:
    from utils import generate_user_token

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT user_token FROM users WHERE telegram_id = $1', telegram_id
        )
        if row:
            # Обновляем имя/username если изменились
            if first_name or username:
                await conn.execute(
                    'UPDATE users SET first_name = COALESCE($1, first_name), username = COALESCE($2, username) WHERE telegram_id = $3',
                    first_name, username, telegram_id
                )
            return row['user_token']

        user_token = generate_user_token(telegram_id)
        await conn.execute(
            'INSERT INTO users (telegram_id, user_token, first_name, username) VALUES ($1, $2, $3, $4)',
            telegram_id, user_token, first_name, username
        )
        await conn.execute(
            'INSERT INTO user_settings (user_token) VALUES ($1)',
            user_token
        )
        return user_token


async def get_user_by_token(token: str) -> Optional[Dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM users WHERE user_token = $1', token)
        return dict(row) if row else None


async def get_user_token(telegram_id: int) -> Optional[str]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT user_token FROM users WHERE telegram_id = $1', telegram_id
        )
        return row['user_token'] if row else None


# === Авторизация на сайте ===

async def create_auth_token(user_token: str) -> str:
    """Создаёт одноразовый токен для входа на сайт"""
    pool = await get_pool()
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(seconds=AUTH_TOKEN_TTL)

    async with pool.acquire() as conn:
        # Удаляем старые неиспользованные токены этого пользователя
        await conn.execute(
            'DELETE FROM auth_tokens WHERE user_token = $1', user_token
        )
        await conn.execute(
            'INSERT INTO auth_tokens (token, user_token, expires_at) VALUES ($1, $2, $3)',
            token, user_token, expires_at
        )
    return token


async def verify_auth_token(token: str) -> Optional[str]:
    """Проверяет токен и возвращает user_token. Токен одноразовый."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT user_token, expires_at, used FROM auth_tokens WHERE token = $1',
            token
        )
        if not row:
            return None
        if row['used']:
            return None
        if row['expires_at'] < datetime.utcnow():
            await conn.execute('DELETE FROM auth_tokens WHERE token = $1', token)
            return None

        # Помечаем как использованный
        await conn.execute(
            'UPDATE auth_tokens SET used = TRUE WHERE token = $1', token
        )
        return row['user_token']


# === События ===

async def add_event(user_token: str, title: str, description: str,
                    event_date: str, event_time: str) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO events (user_token, title, description, event_date, event_time)
            VALUES ($1, $2, $3, $4::date, $5::time)
            RETURNING id
        ''', user_token, title, description, event_date, event_time)
        return row['id']


async def get_events_by_date(user_token: str, date: str) -> List[Dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT id, user_token, title, description,
                   event_date::text AS event_date,
                   event_time::text AS event_time
            FROM events
            WHERE user_token = $1 AND event_date = $2::date
            ORDER BY event_time
        ''', user_token, date)
        return [dict(r) for r in rows]


async def get_events_by_month(user_token: str, year: int, month: int) -> List[Dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT id, user_token, title, description,
                   event_date::text AS event_date,
                   event_time::text AS event_time
            FROM events
            WHERE user_token = $1
              AND EXTRACT(YEAR FROM event_date) = $2
              AND EXTRACT(MONTH FROM event_date) = $3
            ORDER BY event_date, event_time
        ''', user_token, year, month)
        return [dict(r) for r in rows]


async def delete_event(event_id: int, user_token: str) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            'DELETE FROM events WHERE id = $1 AND user_token = $2',
            event_id, user_token
        )
        return result == 'DELETE 1'


async def update_event(event_id: int, user_token: str, **kwargs) -> bool:
    if not kwargs:
        return False
    pool = await get_pool()

    # Строим SET clause с нумерованными параметрами
    set_parts = []
    values = []
    idx = 1
    for key, value in kwargs.items():
        cast = ''
        if key == 'event_date':
            cast = '::date'
        elif key == 'event_time':
            cast = '::time'
        set_parts.append(f"{key} = ${idx}{cast}")
        values.append(value)
        idx += 1

    values.append(event_id)
    values.append(user_token)

    query = f"UPDATE events SET {', '.join(set_parts)} WHERE id = ${idx} AND user_token = ${idx + 1}"

    async with pool.acquire() as conn:
        result = await conn.execute(query, *values)
        return result == 'UPDATE 1'


async def get_event(event_id: int, user_token: str) -> Optional[Dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT id, user_token, title, description,
                   event_date::text AS event_date,
                   event_time::text AS event_time
            FROM events WHERE id = $1 AND user_token = $2
        ''', event_id, user_token)
        return dict(row) if row else None


async def get_all_user_events(user_token: str) -> List[Dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT id, user_token, title, description,
                   event_date::text AS event_date,
                   event_time::text AS event_time
            FROM events WHERE user_token = $1
            ORDER BY event_date, event_time
        ''', user_token)
        return [dict(r) for r in rows]


# === Настройки ===

async def get_user_settings(user_token: str) -> Optional[Dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT * FROM user_settings WHERE user_token = $1', user_token
        )
        return dict(row) if row else None


async def update_user_settings(user_token: str, **kwargs) -> bool:
    if not kwargs:
        return False
    pool = await get_pool()

    set_parts = []
    values = []
    idx = 1
    for key, value in kwargs.items():
        set_parts.append(f"{key} = ${idx}")
        values.append(value)
        idx += 1
    values.append(user_token)

    query = f"UPDATE user_settings SET {', '.join(set_parts)} WHERE user_token = ${idx}"
    async with pool.acquire() as conn:
        result = await conn.execute(query, *values)
        return result == 'UPDATE 1'
