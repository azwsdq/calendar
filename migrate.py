from sqlalchemy import create_engine, text

DATABASE_URL="postgresql+psycopg2://postgres:mysecretpassword@localhost:8080/postgres"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE events ADD COLUMN date_end DATE"))
        conn.commit()
        print("✅ Колонка date_end добавлена успешно!")
    except Exception as e:
        conn.rollback()  # ← сбрасываем сломанную транзакцию
        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
            print("ℹ️ Колонка date_end уже существует.")
        else:
            print(f"❌ Ошибка при добавлении date_end: {e}")

    try:
        conn.execute(text("ALTER TABLE events ADD COLUMN priority VARCHAR DEFAULT 'Medium'"))
        conn.commit()
        print("✅ Колонка priority добавлена успешно!")
    except Exception as e:
        conn.rollback()  # ← сбрасываем сломанную транзакцию
        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
            print("ℹ️ Колонка priority уже существует.")
        else:
            print(f"❌ Ошибка при добавлении priority: {e}")

    try:
        conn.execute(text("ALTER TABLE events ADD COLUMN deadline_time TIME"))
        conn.commit()
        print("✅ Колонка deadline_time добавлена!")
    except Exception as e:
        conn.rollback()  # ← сбрасываем сломанную транзакцию
        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
            print("ℹ️ Колонка deadline_time уже существует.")
        else:
            print(f"❌ Ошибка: {e}")