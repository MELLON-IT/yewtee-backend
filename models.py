from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


# 1. 用戶模型
class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String)  # 例如: Stephen, Jenny
    hashed_password = Column(String)


# 2. 看板欄位模型 (父表)
class ColumnModel(Base):
    __tablename__ = "columns"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)

    # 建議改名為 position，避開 SQL 保留字 'order'
    position = Column(Integer, default=0)

    tasks = relationship("TaskModel", back_populates="column")


# 3. 任務模型 (子表)
class TaskModel(Base):
    __tablename__ = "tasks"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    description = Column(String, nullable=True)

    # 關聯一：屬於哪個看板欄位
    column_id = Column(Integer, ForeignKey("columns.id"))
    column = relationship("ColumnModel", back_populates="tasks")

    # 關聯二：屬於哪個用戶 (如果你需要這功能)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)