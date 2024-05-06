from sqlalchemy import Boolean, Column, Integer, String

from .database import Base

class APIKeys(Base):
    __tablename__ = "api_keys"

    value = Column(String, primary_key=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

class Config(Base):
    __tablename__ = "config"
    name = Column(String, primary_key=True)
    value = Column(Integer)

