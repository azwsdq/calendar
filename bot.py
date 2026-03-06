import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove
from datetime import datetime
from config import BOT_TOKEN
from database import init_db, add_event, get_events_by_date, get_events_by_month, delete_event, get_event, update_event, get_all_user_events
from keyboards import create_calendar_keyboard, create_event_keyboard, create_events_list_keyboard, create_cancel_keyboard


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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

user_states = {}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я календарь-бот.\n\n"
        "📅 /calendar - Открыть календарь\n"
        "➕ /add - Добавить событие\n"
        "📋 /events - Все события\n"
        "❓ /help - Помощь"
    )

@dp.message(Command("calendar"))
async def cmd_calendar(message: types.Message):
    now = datetime.now()
    keyboard = create_calendar_keyboard(now.year, now.month)
    await message.answer("📅 Выберите дату:", reply_markup=keyboard)

@dp.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext):
    await message.answer("Введите название события:", reply_markup=create_cancel_keyboard())
    await state.set_state(AddEvent.title)

@dp.message(Command("events"))
async def cmd_events(message: types.Message):
    events = await get_all_user_events(message.from_user.id)
    if not events:
        await message.answer("📭 У вас пока нет событий.")
        return
    text = "📋 Ваши события:\n\n"
    for event in events:
        text += f"📌 {event['title']}\n"
        date_obj = datetime.strptime(event['event_date'], '%Y-%m-%d')
        date_display = date_obj.strftime('%d-%m-%Y')
        text += f"📅 {date_display}"
        if event['event_time']:
            text += f" ⏰ {event['event_time']}"
        text += "\n\n"
    await message.answer(text[:4096])

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
🤖 **Помощь по боту**

📅 **Команды:**
/start - Запустить бота
/calendar - Открыть календарь
/add - Добавить событие
/events - Показать все события
/help - Эта справка

📝 **Как использовать:**
1. Откройте календарь командой /calendar
2. Выберите дату для просмотра событий
3. Добавьте событие через ➕ Добавить
4. Управляйте событиями через кнопки
    """
    await message.answer(help_text)

@dp.callback_query(F.data == "cancel")
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Отменено.")
    await callback.answer()

@dp.callback_query(F.data.startswith("prev_") | F.data.startswith("next_"))
async def navigate_calendar(callback: types.CallbackQuery):
    action, year, month = callback.data.split('_')
    year, month = int(year), int(month)
    keyboard = create_calendar_keyboard(year, month)
    await callback.message.edit_text(f"📅 Календарь: {month}/{year}", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("day_"))
async def select_day(callback: types.CallbackQuery):
    date = callback.data.split('_', 1)[1]
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    date_display = date_obj.strftime('%d-%m-%Y')
    events = await get_events_by_date(callback.from_user.id, date)
    text = f"📅 События на {date_display}:\n\n"
    if events:
        for event in events:
            text += f"📌 {event['title']}\n"
            if event['event_time']:
                text += f"⏰ {event['event_time']}\n"
            if event['description']:
                text += f"📝 {event['description']}\n"
            text += "\n"
    else:
        text += "Нет событий на этот день."
    keyboard = create_calendar_keyboard(int(date[:4]), int(date[5:7]))
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "add_event")
async def add_event_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название события:", reply_markup=create_cancel_keyboard())
    await state.set_state(AddEvent.title)
    await callback.answer()

@dp.callback_query(F.data == "back_calendar")
async def back_calendar(callback: types.CallbackQuery):
    now = datetime.now()
    keyboard = create_calendar_keyboard(now.year, now.month)
    await callback.message.edit_text("📅 Выберите дату:", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("view_"))
async def view_event(callback: types.CallbackQuery):
    event_id = int(callback.data.split('_', 1)[1])
    event = await get_event(event_id, callback.from_user.id)
    if event:
        text = f"📌 {event['title']}\n"
        date_obj = datetime.strptime(event['event_date'], '%Y-%m-%d')
        date_display = date_obj.strftime('%d-%m-%Y')
        text += f"📅 {date_display}\n"
        if event['event_time']:
            text += f"⏰ {event['event_time']}\n"
        if event['description']:
            text += f"📝 {event['description']}\n"
        keyboard = create_event_keyboard(event_id)
        await callback.message.answer(text, reply_markup=keyboard)
    else:
        await callback.answer("Событие не найдено.", show_alert=True)
    await callback.answer()

@dp.callback_query(F.data.startswith("delete_"))
async def delete_event_callback(callback: types.CallbackQuery):
    event_id = int(callback.data.split('_', 1)[1])
    success = await delete_event(event_id, callback.from_user.id)
    if success:
        await callback.message.answer("🗑️ Событие удалено.")
    else:
        await callback.answer("Ошибка удаления.", show_alert=True)
    await callback.answer()

@dp.callback_query(F.data.startswith("edit_"))
async def edit_event_callback(callback: types.CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split('_', 1)[1])
    await state.update_data(event_id=event_id)
    await callback.message.answer("Введите новое название:", reply_markup=create_cancel_keyboard())
    await state.set_state(EditEvent.title)
    await callback.answer()

@dp.message(AddEvent.title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите описание (или /skip):", reply_markup=create_cancel_keyboard())
    await state.set_state(AddEvent.description)

@dp.message(EditEvent.title)
async def process_edit_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите новое описание (или /skip):", reply_markup=create_cancel_keyboard())
    await state.set_state(EditEvent.description)

@dp.message(AddEvent.description)
async def process_description(message: types.Message, state: FSMContext):
    if message.text == '/skip':
        description = ''
    else:
        description = message.text
    await state.update_data(description=description)
    await message.answer("Введите дату (ДД-ММ-ГГГГ):", reply_markup=create_cancel_keyboard())
    await state.set_state(AddEvent.date)

@dp.message(EditEvent.description)
async def process_edit_description(message: types.Message, state: FSMContext):
    if message.text == '/skip':
        description = None
    else:
        description = message.text
    await state.update_data(description=description)
    await message.answer("Введите новую дату (ДД-ММ-ГГГГ) или /skip:", reply_markup=create_cancel_keyboard())
    await state.set_state(EditEvent.date)

@dp.message(AddEvent.date)
async def process_date(message: types.Message, state: FSMContext):
    try:
        date_obj = datetime.strptime(message.text, '%d-%m-%Y')
        date_str = date_obj.strftime('%Y-%m-%d')
        await state.update_data(date=date_str)
        await message.answer("Введите время (ЧЧ:ММ) или /skip:", reply_markup=create_cancel_keyboard())
        await state.set_state(AddEvent.time)
    except:
        await message.answer("Неверный формат. Используйте ДД-ММ-ГГГГ:")

@dp.message(EditEvent.date)
async def process_edit_date(message: types.Message, state: FSMContext):
    if message.text == '/skip':
        await state.update_data(date=None)
    else:
        try:
            date_obj = datetime.strptime(message.text, '%d-%m-%Y')
            date_str = date_obj.strftime('%Y-%m-%d')
            await state.update_data(date=date_str)
        except:
            await message.answer("Неверный формат. Используйте ДД-ММ-ГГГГ или /skip:")
            return
    await message.answer("Введите новое время (ЧЧ:ММ) или /skip:", reply_markup=create_cancel_keyboard())
    await state.set_state(EditEvent.time)

@dp.message(AddEvent.time)
async def process_time(message: types.Message, state: FSMContext):
    if message.text == '/skip':
        time = None
    else:
        try:
            datetime.strptime(message.text, '%H:%M')
            time = message.text
        except:
            await message.answer("Неверный формат. Используйте ЧЧ:ММ или /skip:")
            return
    data = await state.get_data()
    await add_event(
        user_id=message.from_user.id,
        title=data['title'],
        description=data['description'],
        event_date=data['date'],
        event_time=time
    )
    await message.answer("✅ Событие добавлено!", reply_markup=ReplyKeyboardRemove())
    await state.clear()

@dp.message(EditEvent.time)
async def process_edit_time(message: types.Message, state: FSMContext):
    if message.text == '/skip':
        time = None
    else:
        try:
            datetime.strptime(message.text, '%H:%M')
            time = message.text
        except:
            await message.answer("Неверный формат. Используйте ЧЧ:ММ или /skip:")
            return
    data = await state.get_data()
    updates = {}
    if data.get('title'):
        updates['title'] = data['title']
    if data.get('description') is not None:
        updates['description'] = data['description']
    if data.get('date'):
        updates['event_date'] = data['date']
    if time is not None:
        updates['event_time'] = time
    if updates:
        await update_event(data['event_id'], message.from_user.id, **updates)
        await message.answer("✅ Событие обновлено!", reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer("❌ Нет изменений.")
    await state.clear()

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())