# bot.py
import asyncio
from datetime import datetime
from typing import Optional, List, Dict

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove
from aiogram.client.bot import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

from config import BOT_TOKEN, DB_PATH
from database import (
    init_db, get_or_create_user, get_user_token,
    add_event, get_events_by_date, get_all_user_events,
    delete_event, get_event, update_event
)
from keyboards import (
    create_calendar_keyboard, create_event_keyboard,
    create_events_list_keyboard, create_cancel_keyboard
)
from utils import parse_date, parse_time, format_date_human

# === Создаём сессию (без trust_env) ===
session = AiohttpSession()

bot = Bot(
    token=BOT_TOKEN,
    session=session,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()


# === FSM States ===

class AddEvent(StatesGroup):
    title = State()
    description = State()
    date = State()
    time = State()


class EditEvent(StatesGroup):
    event_id = State()
    title = State()
    description = State()
    date = State()
    time = State()


# === Команды бота ===

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_token = await get_or_create_user(message.from_user.id)

    await message.answer(
        f"Привет, {message.from_user.first_name}!\n\n"
        "Команды:\n"
        "/calendar - Открыть календарь\n"
        "/add - Добавить событие\n"
        "/events - Все события\n"
        "/help - Помощь"
    )


@dp.message(Command("calendar"))
async def cmd_calendar(message: types.Message):
    user_token = await get_user_token(message.from_user.id)
    if not user_token:
        user_token = await get_or_create_user(message.from_user.id)

    now = datetime.now()
    keyboard = create_calendar_keyboard(now.year, now.month)
    await message.answer("Выберите дату:", reply_markup=keyboard)


@dp.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext):
    user_token = await get_user_token(message.from_user.id)
    if not user_token:
        user_token = await get_or_create_user(message.from_user.id)

    await state.update_data(user_token=user_token)
    await message.answer("Введите название события:", reply_markup=create_cancel_keyboard())
    await state.set_state(AddEvent.title)


@dp.message(Command("events"))
async def cmd_events(message: types.Message):
    user_token = await get_user_token(message.from_user.id)
    if not user_token:
        await message.answer("У вас пока нет событий.")
        return

    events = await get_all_user_events(user_token)
    if not events:
        await message.answer("У вас пока нет событий.")
        return

    text = "Ваши события:\n\n"
    for event in events:
        text += f"- {event['title']}\n"
        date_obj = datetime.strptime(event['event_date'], '%Y-%m-%d')
        date_display = date_obj.strftime('%d-%m-%Y')
        text += f"  Дата: {date_display}"
        if event['event_time']:
            text += f" Время: {event['event_time']}"
        text += "\n\n"

    await message.answer(text[:4096])


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
Помощь по боту

Команды:
/start - Запустить бота
/calendar - Открыть календарь
/add - Добавить событие
/events - Показать все события
/help - Эта справка

Как использовать:
1. Откройте календарь командой /calendar
2. Выберите дату для просмотра событий
3. Добавьте событие через + Создать событие
4. Управляйте событиями через кнопки
    """
    await message.answer(help_text)


# === Callback handlers ===

@dp.callback_query(F.data == "cancel")
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Отменено.")
    await callback.answer()


@dp.callback_query(F.data.startswith("prev_") | F.data.startswith("next_"))
async def navigate_calendar(callback: types.CallbackQuery):
    action, year, month = callback.data.split('_')
    year, month = int(year), int(month)
    keyboard = create_calendar_keyboard(year, month)
    await callback.message.edit_text(f"Календарь: {month}/{year}", reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data.startswith("day_"))
async def select_day(callback: types.CallbackQuery):
    user_token = await get_user_token(callback.from_user.id)
    if not user_token:
        user_token = await get_or_create_user(callback.from_user.id)

    date = callback.data.split('_', 1)[1]
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    date_display = date_obj.strftime('%d-%m-%Y')
    events = await get_events_by_date(user_token, date)

    text = f"События на {date_display}:\n\n"
    if events:
        for event in events:
            text += f"- {event['title']}\n"
            if event['event_time']:
                text += f"  Время: {event['event_time']}\n"
            if event['description']:
                text += f"  Описание: {event['description']}\n"
            text += "\n"
    else:
        text += "Нет событий на этот день."

    keyboard = create_calendar_keyboard(int(date[:4]), int(date[5:7]))
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data == "add_event")
async def add_event_callback(callback: types.CallbackQuery, state: FSMContext):
    user_token = await get_user_token(callback.from_user.id)
    if not user_token:
        user_token = await get_or_create_user(callback.from_user.id)

    await state.update_data(user_token=user_token)
    await callback.message.answer("Введите название события:", reply_markup=create_cancel_keyboard())
    await state.set_state(AddEvent.title)
    await callback.answer()


@dp.callback_query(F.data == "back_calendar")
async def back_calendar(callback: types.CallbackQuery):
    now = datetime.now()
    keyboard = create_calendar_keyboard(now.year, now.month)
    await callback.message.edit_text("Выберите дату:", reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data == "help_info")
async def help_info(callback: types.CallbackQuery):
    help_text = """
Помощь по боту

Команды:
/start - Запустить бота
/calendar - Открыть календарь
/add - Добавить событие
/events - Показать все события
/help - Эта справка
    """
    await callback.message.answer(help_text)
    await callback.answer()


@dp.callback_query(F.data == "all_events")
async def all_events_callback(callback: types.CallbackQuery):
    user_token = await get_user_token(callback.from_user.id)
    if not user_token:
        await callback.answer("У вас пока нет событий.", show_alert=True)
        return

    events = await get_all_user_events(user_token)
    if not events:
        await callback.answer("У вас пока нет событий.", show_alert=True)
        return

    text = "Ваши события:\n\n"
    for event in events:
        text += f"- {event['title']}\n"
        date_obj = datetime.strptime(event['event_date'], '%Y-%m-%d')
        date_display = date_obj.strftime('%d-%m-%Y')
        text += f"  Дата: {date_display}"
        if event['event_time']:
            text += f" Время: {event['event_time']}"
        text += "\n\n"

    keyboard = create_events_list_keyboard(events)
    await callback.message.answer(text[:4096], reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data.startswith("view_"))
async def view_event(callback: types.CallbackQuery):
    user_token = await get_user_token(callback.from_user.id)
    if not user_token:
        user_token = await get_or_create_user(callback.from_user.id)

    event_id = int(callback.data.split('_', 1)[1])
    event = await get_event(event_id, user_token)

    if event:
        text = f"{event['title']}\n"
        date_obj = datetime.strptime(event['event_date'], '%Y-%m-%d')
        date_display = date_obj.strftime('%d-%m-%Y')
        text += f"Дата: {date_display}\n"
        if event['event_time']:
            text += f"Время: {event['event_time']}\n"
        if event['description']:
            text += f"Описание: {event['description']}\n"
        keyboard = create_event_keyboard(event_id)
        await callback.message.answer(text, reply_markup=keyboard)
    else:
        await callback.answer("Событие не найдено.", show_alert=True)
    await callback.answer()


@dp.callback_query(F.data.startswith("delete_"))
async def delete_event_callback(callback: types.CallbackQuery):
    user_token = await get_user_token(callback.from_user.id)
    if not user_token:
        user_token = await get_or_create_user(callback.from_user.id)

    event_id = int(callback.data.split('_', 1)[1])
    success = await delete_event(event_id, user_token)

    if success:
        await callback.message.answer("Событие удалено.")
    else:
        await callback.answer("Ошибка удаления.", show_alert=True)
    await callback.answer()


@dp.callback_query(F.data.startswith("edit_"))
async def edit_event_callback(callback: types.CallbackQuery, state: FSMContext):
    user_token = await get_user_token(callback.from_user.id)
    if not user_token:
        user_token = await get_or_create_user(callback.from_user.id)

    event_id = int(callback.data.split('_', 1)[1])
    await state.update_data(event_id=event_id, user_token=user_token)
    await callback.message.answer("Введите новое название:", reply_markup=create_cancel_keyboard())
    await state.set_state(EditEvent.title)
    await callback.answer()


# === FSM: Добавление события ===

@dp.message(AddEvent.title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите описание (или /skip):", reply_markup=create_cancel_keyboard())
    await state.set_state(AddEvent.description)


@dp.message(AddEvent.description)
async def process_description(message: types.Message, state: FSMContext):
    description = '' if message.text == '/skip' else message.text
    await state.update_data(description=description)
    await message.answer(
        "Введите дату в любом формате:\n"
        "Примеры: 25.12.2024, 25 декабря 2024, сегодня, завтра",
        reply_markup=create_cancel_keyboard()
    )
    await state.set_state(AddEvent.date)


@dp.message(AddEvent.date)
async def process_date(message: types.Message, state: FSMContext):
    parsed = parse_date(message.text)

    if not parsed:
        await message.answer(
            "Не удалось распознать дату.\n\n"
            "Примеры правильных форматов:\n"
            "- 25.12.2024\n"
            "- 25-12-2024\n"
            "- 25 декабря 2024\n"
            "- 25 дек 2024\n"
            "- сегодня / завтра",
            reply_markup=create_cancel_keyboard()
        )
        return

    await state.update_data(date=parsed)
    await message.answer(
        f"Дата: {format_date_human(parsed)}\n\n"
        "Введите время (или /skip):\n"
        "Примеры: 14:30, 14.30, 2:30pm, сейчас",
        reply_markup=create_cancel_keyboard()
    )
    await state.set_state(AddEvent.time)


@dp.message(AddEvent.time)
async def process_time(message: types.Message, state: FSMContext):
    if message.text.lower() == '/skip':
        event_time = None
    else:
        parsed = parse_time(message.text)
        if not parsed:
            await message.answer(
                "Не удалось распознать время.\n\n"
                "Примеры: 14:30, 14.30, 2:30pm, 1430, сейчас",
                reply_markup=create_cancel_keyboard()
            )
            return
        event_time = parsed

    data = await state.get_data()
    user_token = data.get('user_token')

    if not user_token:
        user_token = await get_user_token(message.from_user.id)
        if not user_token:
            user_token = await get_or_create_user(message.from_user.id)

    await add_event(
        user_token=user_token,
        title=data['title'],
        description=data.get('description', ''),
        event_date=data['date'],
        event_time=event_time
    )

    response = f"Событие добавлено!\n"
    response += f"Дата: {format_date_human(data['date'])}"
    if event_time:
        response += f" Время: {event_time}"

    await message.answer(response, reply_markup=ReplyKeyboardRemove())
    await state.clear()


# === FSM: Редактирование события ===

@dp.message(EditEvent.title)
async def process_edit_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите новое описание (или /skip):", reply_markup=create_cancel_keyboard())
    await state.set_state(EditEvent.description)


@dp.message(EditEvent.description)
async def process_edit_description(message: types.Message, state: FSMContext):
    description = None if message.text == '/skip' else message.text
    await state.update_data(description=description)
    await message.answer("Введите новую дату (или /skip):", reply_markup=create_cancel_keyboard())
    await state.set_state(EditEvent.date)


@dp.message(EditEvent.date)
async def process_edit_date(message: types.Message, state: FSMContext):
    if message.text == '/skip':
        await state.update_data(date=None)
    else:
        parsed = parse_date(message.text)
        if not parsed:
            await message.answer("Неверный формат. Используйте /skip или введите дату:")
            return
        await state.update_data(date=parsed)
    await message.answer("Введите новое время (или /skip):", reply_markup=create_cancel_keyboard())
    await state.set_state(EditEvent.time)


@dp.message(EditEvent.time)
async def process_edit_time(message: types.Message, state: FSMContext):
    if message.text.lower() == '/skip':
        event_time = None
    else:
        parsed = parse_time(message.text)
        if not parsed:
            await message.answer("Неверный формат. Используйте /skip:")
            return
        event_time = parsed

    data = await state.get_data()
    updates = {}
    if data.get('title'):
        updates['title'] = data['title']
    if data.get('description') is not None:
        updates['description'] = data['description']
    if data.get('date'):
        updates['event_date'] = data['date']
    if event_time is not None:
        updates['event_time'] = event_time

    if updates:
        await update_event(data['event_id'], data['user_token'], **updates)
        await message.answer("Событие обновлено!", reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer("Нет изменений.")
    await state.clear()


# === Запуск ===

async def main():
    print("Инициализация базы данных...")
    await init_db()

    print("Запуск бота...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print(f"Webhook: {e}")

    print("Бот запущен! Жду сообщения...")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("Остановка бота")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())