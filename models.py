from sqlalchemy import Integer, String, Column, Date
from database import Base

class event(Base):
    __tablename__ = "events"
    #разметка таблицы для хранения событий
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    date = Column(Date)
    description = Column(String, nullable=False)