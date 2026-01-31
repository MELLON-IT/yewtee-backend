from pydantic import BaseModel
from typing import List, Optional

# 任務的模型
class TaskBase(BaseModel):
    id: int
    content: str
    column_id: int

    class Config:
        from_attributes = True

# 欄位的模型
class ColumnSchema(BaseModel):
    id: int
    title: str
    tasks: List[TaskBase] = []

    class Config:
        from_attributes = True