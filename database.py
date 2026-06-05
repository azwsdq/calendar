from sqlalchemy import create_engine, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from urllib.parse import quote_plus
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME")

    if not all([db_user, db_password, db_name]):
        raise ValueError("PostgreSQL config is missing. Set DATABASE_URL or DB_USER/DB_PASSWORD/DB_NAME.")

    encoded_password = quote_plus(db_password)
    DATABASE_URL = f"postgresql+psycopg2://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations():
    """
    Автоматически добавляет недостающие колонки в таблицу events.
    Проверяет существование колонки перед добавлением.
    """
    inspector = inspect(engine)

    # Проверяем, существует ли таблица events
    if not inspector.has_table("events"):
        print("[MIGRATION] Таблица 'events' не существует, пропускаем миграцию")
        return

    # Получаем список существующих колонок
    columns = [col['name'] for col in inspector.get_columns("events")]

    # Добавляем deadline_time, если её нет
    if "deadline_time" not in columns:
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE events ADD COLUMN deadline_time TIME"))
                conn.commit()
                print("[MIGRATION] Добавлена колонка 'deadline_time' в таблицу events")
            except Exception as e:
                conn.rollback()
                print(f"[MIGRATION] Ошибка при добавлении колонки: {e}")
    else:
        print("[MIGRATION] Колонка 'deadline_time' уже существует")