# utils/token_generator.py
import secrets
import hashlib
from datetime import datetime


def generate_user_token(telegram_id: int) -> str:
    """
    Генерирует уникальный токен для пользователя на основе Telegram ID.
    Формат: USR-{telegram_id}-{random_32_chars}

    Пример: USR-123456789-aB3dE5fG7hI9jK1lM3nO5pQ7rS9tU1vW
    """
    random_part = secrets.token_urlsafe(24)  # 192 бита случайности
    return f"USR-{telegram_id}-{random_part}"


def verify_token_format(token: str) -> bool:
    """Проверяет формат токена"""
    if not token:
        return False
    import re
    pattern = r'^USR-\d{6,}-[A-Za-z0-9_-]{20,}$'
    return bool(re.match(pattern, token))


def extract_telegram_id(token: str) -> int:
    """Извлекает Telegram ID из токена"""
    if not token or not token.startswith('USR-'):
        return 0
    parts = token.split('-')
    if len(parts) >= 2:
        try:
            return int(parts[1])
        except ValueError:
            return 0
    return 0