from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from  sqlalchemy.orm import sessionmaker

# 這裡我們使用 SQLite，它會產生一個名為 sql_app.db 的檔案，不需要安裝額外數據庫
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()