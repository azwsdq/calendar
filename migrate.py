from sqlalchemy import create_engine, text


engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    try:
        # Добавляем колонку date_end
        conn.execute(text("ALTER TABLE events ADD COLUMN date_end DATE"))
        conn.commit()
        print("✅ Колонка date_end добавлена успешно!")
    except Exception as e:
        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
            print("ℹ️ Колонка date_end уже существует.")
        else:
            print(f"❌ Ошибка при добавлении date_end: {e}")

    try:
        # Добавляем колонку priority (на всякий случай)
        conn.execute(text("ALTER TABLE events ADD COLUMN priority VARCHAR DEFAULT 'Medium'"))
        conn.commit()
        print("✅ Колонка priority добавлена успешно!")
    except Exception as e:
        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
            print("️ Колонка priority уже существует.")
        else:
            print(f"❌ Ошибка при добавлении priority: {e}")