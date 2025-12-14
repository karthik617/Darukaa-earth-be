import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import DATABASE_URL


class Base(DeclarativeBase):
    pass


URI = DATABASE_URL
IS_TESTING = os.getenv("PYTEST_RUNNING") == "1"
if IS_TESTING:
    URI = "sqlite:///./test.db"
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

engine = create_engine(URI, connect_args=connect_args, future=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
