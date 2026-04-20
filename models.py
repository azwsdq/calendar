from sqlalchemy import Integer, String, Column, Date, ForeignKey
from database import Base

class event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    date = Column(Date)
    description = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)