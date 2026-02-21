from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///db.sqlite3" #todo: Потом поменять


engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}) # если SQLite - оставить, для других баз данных - удалить
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) # Создаем сессию для работы с базой данных
Base = declarative_base() # Создаем базовый класс для моделей, который будет использоваться для создания таблиц в базе данных

#фнкция для получения сессии базы данных
def get_db():
    db = SessionLocal() # Создаем новую сессию для работы с базой данных
    try:
        yield db # Возвращаем сессию для использования в маршрутах FastAPI
    finally:
        db.close() # Закрываем сессию после использования, чтобы освободить ресурсы