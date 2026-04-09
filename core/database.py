import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from .utils import get_data_dir

DB_PATH = get_data_dir() / "life_stats.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Настройка движка
# check_same_thread=False важен для Streamlit, так как он многопоточный
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},
    echo=False 
)

# Создание фабрики сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Создает все таблицы, если их еще нет."""
    from .models import Base
    Base.metadata.create_all(bind=engine)
    print(f"База данных проверена/создана: {DB_PATH}")

def get_session():
    """Возвращает новую сессию БД."""
    return SessionLocal()