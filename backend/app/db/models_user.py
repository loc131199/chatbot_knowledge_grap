from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from backend.app.db.db_postgres import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)

    password = Column(String, nullable=False)
    password_hash = Column(String, nullable=True)

    role = Column(String(20), default="user")
    create_at = Column(DateTime, default=datetime.utcnow)
