# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# .env betöltése
load_dotenv()

SQL_HOST = os.getenv("SQL_HOST")
SQL_PORT = int(os.getenv("SQL_PORT", "3306"))
SQL_DATABASE = os.getenv("SQL_DATABASE")
SQL_USER = os.getenv("SQL_USER")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")

# URL.create escapes user/password safely (handles special characters like &)
SQLALCHEMY_DATABASE_URL = URL.create(
    "mysql+pymysql",
    username=SQL_USER,
    password=SQL_PASSWORD,
    host=SQL_HOST,
    port=SQL_PORT,
    database=SQL_DATABASE,
    query={"charset": "utf8mb4"},
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
