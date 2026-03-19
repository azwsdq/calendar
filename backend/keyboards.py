# keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
from calendar import monthrange


def create_calendar_keyboard(year: int, month: int) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру календаря на указанный месяц"""
    builder = InlineKeyboardBuilder()

    # Заголовок с месяцем и годом
    month_name = datetime(year, month, 1).strftime('%B %Y')
    builder.button(text=f"Календарь: {month_name}", callback_data="ignore")

    # Навигация по месяцам
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    builder.button(text="<", callback_data=f"prev_{prev_year}_{prev_month}")

    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    builder.button(text=">", callback_data=f"next_{next_year}_{next_month}")
    builder.adjust(1, 2)

    # Дни недели
    days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    for day in days:
        builder.button(text=day, callback_data="ignore")

    # Дни месяца
    first_day, num_days = monthrange(year, month)
    start_day = (first_day - 1) % 7

    for _ in range(start_day):
        builder.button(text=" ", callback_data="ignore")

    for day in range(1, num_days + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        builder.button(text=str(day), callback_data=f"day_{date_str}")
    builder.adjust(7)

    # Кнопки действий
    builder.button(text="+ Создать событие", callback_data="add_event")
    builder.button(text="Все события", callback_data="all_events")
    builder.button(text="Помощь", callback_data="help_info")
    builder.adjust(3)

    return builder.as_markup()


def create_event_keyboard(event_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для управления событием"""
    builder = InlineKeyboardBuilder()
    builder.button(text="Изменить", callback_data=f"edit_{event_id}")
    builder.button(text="Удалить", callback_data=f"delete_{event_id}")
    builder.adjust(2)
    return builder.as_markup()


def create_events_list_keyboard(events: list) -> InlineKeyboardMarkup:
    """Клавиатура со списком событий"""
    builder = InlineKeyboardBuilder()
    for event in events[:10]:
        date_obj = datetime.strptime(event['event_date'], '%Y-%m-%d')
        date_display = date_obj.strftime('%d-%m-%Y')
        event_text = f"{event['title'][:15]} ({date_display})"
        builder.button(text=event_text, callback_data=f"view_{event['id']}")
    builder.adjust(1)
    builder.button(text="Назад в календарь", callback_data="back_calendar")
    return builder.as_markup()


def create_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    builder = InlineKeyboardBuilder()
    builder.button(text="Отмена", callback_data="cancel")
    return builder.as_markup()