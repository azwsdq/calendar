from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from urllib.parse import quote_plus
import os

<<<<<<< HEAD
SQLALCHEMY_DATABASE_URL = "sqlite:///calendar.db"
=======
load_dotenv()

# Можно задать готовую строку подключения DATABASE_URL,
# либо собрать её из DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME.
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
>>>>>>> 413a800 (Добавление поддержки PostgreSQL в database.py и обновление README.md с инструкциями по настройке БД)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
