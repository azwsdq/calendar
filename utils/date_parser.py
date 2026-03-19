# utils/date_parser.py
from datetime import datetime, timedelta
from typing import Optional
import re

MONTHS_RU = {
    'январь': 1, 'февраль': 2, 'март': 3, 'апрель': 4, 'май': 5, 'июнь': 6,
    'июль': 7, 'август': 8, 'сентябрь': 9, 'октябрь': 10, 'ноябрь': 11, 'декабрь': 12,
    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6,
    'июля': 7, 'августа': 8, 'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12,
    'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'май': 5, 'июн': 6,
    'июл': 7, 'авг': 8, 'сен': 9, 'сент': 9, 'окт': 10, 'ноя': 11, 'дек': 12,
    '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
    '7': 7, '8': 8, '9': 9, '10': 10, '11': 11, '12': 12,
}

RELATIVE_DATES = {
    'сегодня': 0, 'сейчас': 0, 'текущий': 0,
    'завтра': 1, 'следующий': 1,
    'послезавтра': 2,
    'вчера': -1,
}


def parse_date(date_str: str, base_date: Optional[datetime] = None) -> Optional[str]:
    if not date_str:
        return None

    base_date = base_date or datetime.now()
    date_str = date_str.strip().lower()

    if date_str in RELATIVE_DATES:
        result_date = base_date + timedelta(days=RELATIVE_DATES[date_str])
        return result_date.strftime('%Y-%m-%d')

    parsers = [_parse_iso, _parse_with_separators, _parse_with_month_name, _parse_short_year]

    for parser in parsers:
        result = parser(date_str, base_date)
        if result:
            return result

    return None


def _parse_iso(date_str: str, base_date: datetime) -> Optional[str]:
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        return None


def _parse_with_separators(date_str: str, base_date: datetime) -> Optional[str]:
    normalized = re.sub(r'[\s/\-\\.]+', '.', date_str.strip())
    parts = normalized.split('.')
    if len(parts) != 3:
        return None
    try:
        day, month, year = map(int, parts)
        if year < 100:
            year += 2000 if year < 50 else 1900
        dt = datetime(year, month, day)
        return dt.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return None


def _parse_with_month_name(date_str: str, base_date: datetime) -> Optional[str]:
    date_str = re.sub(r'\s+', ' ', date_str.strip())
    pattern = r'^(\d{1,2})\s+([а-яё]+)\s+(\d{2,4})$'
    match = re.match(pattern, date_str)
    if not match:
        return None
    try:
        day = int(match.group(1))
        month_name = match.group(2).lower()
        year = int(match.group(3))
        month = MONTHS_RU.get(month_name)
        if not month:
            return None
        if year < 100:
            year += 2000 if year < 50 else 1900
        dt = datetime(year, month, day)
        return dt.strftime('%Y-%m-%d')
    except (ValueError, TypeError, KeyError):
        return None


def _parse_short_year(date_str: str, base_date: datetime) -> Optional[str]:
    normalized = re.sub(r'[\s/\-\\.]+', '.', date_str.strip())
    parts = normalized.split('.')
    if len(parts) != 3:
        return None
    try:
        day, month, year = map(int, parts)
        if year < 100:
            year += 2000 if year < 50 else 1900
        dt = datetime(year, month, day)
        return dt.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return None


def parse_time(time_str: str) -> Optional[str]:
    if not time_str:
        return None

    original = time_str.strip().lower()

    if original in ['сейчас', 'текущее', 'ноу', 'now', 'щас']:
        return datetime.now().strftime('%H:%M')

    russian_pattern = r'^(\d{1,2})\s*ч\.?\s*(\d{1,2})\s*м\.?$'
    match = re.match(russian_pattern, original)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        if 0 <= hour < 24 and 0 <= minute < 60:
            return f"{hour:02d}:{minute:02d}"

    time_str = re.sub(r'\s*(часов?|минут?|ч\.?|м\.?)\s*', ' ', original)
    time_str = ' '.join(time_str.split())
    time_str = time_str.strip()

    match = re.match(r'^(\d{1,2}):(\d{2})\s*(am|pm)?$', time_str)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        period = match.group(3)
        if period:
            if period == 'pm' and hour < 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
        if 0 <= hour < 24 and 0 <= minute < 60:
            return f"{hour:02d}:{minute:02d}"

    match = re.match(r'^(\d{1,2})[\.\s](\d{2})\s*(am|pm)?$', time_str)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        period = match.group(3)
        if period:
            if period == 'pm' and hour < 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
        if 0 <= hour < 24 and 0 <= minute < 60:
            return f"{hour:02d}:{minute:02d}"

    match = re.match(r'^(\d{4})$', time_str)
    if match:
        value = int(match.group(1))
        hour, minute = value // 100, value % 100
        if 0 <= hour < 24 and 0 <= minute < 60:
            return f"{hour:02d}:{minute:02d}"

    return None


def format_date_human(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        month_names = ['', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                       'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
        return f"{dt.day} {month_names[dt.month]} {dt.year}"
    except ValueError:
        return date_str