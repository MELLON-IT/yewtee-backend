import socketio
from fastapi import FastAPI, Depends, HTTPException, Body
from sqlalchemy.orm import Session, joinedload
import models
import schemas
from database import SessionLocal, engine
from fastapi.middleware.cors import CORSMiddleware
from typing import List

# 1. 初始化資料庫結構
models.Base.metadata.create_all(bind=engine)

# 2. 建立 FastAPI 實例
app = FastAPI()

# 3. CORS 設置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. 提供給 FastAPI 依賴注入的 db 連線
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 5. 統一初始化資料函式
def init_db():
    db = SessionLocal()
    try:
        if db.query(models.ColumnModel).count() == 0:
            db.add_all([
                models.ColumnModel(title="待辦中", position=1),
                models.ColumnModel(title="進行中", position=2),
                models.ColumnModel(title="已完成", position=3)
            ])
            db.commit()

        test_users = [
            ("admin", "admin123", "Admin"),
            ("stephen", "123", "Stephen"),
            ("bernie", "123", "Bernie"),
            ("jenny", "123", "Jenny")
        ]

        for username, password, full_name in test_users:
            user_exists = db.query(models.UserModel).filter(models.UserModel.username == username).first()
            if not user_exists:
                new_user = models.UserModel(
                    username=username, 
                    hashed_password=password, 
                    full_name=full_name
                )
                db.add(new_user)
                print(f"User {username} created!")
        db.commit()
    except Exception as e:
        print(f"❌ 初始化錯誤: {e}")
    finally:
        db.close()

# 執行初始化
init_db()

# 6. Socket.io 服務
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins="*")
sio_app = socketio.ASGIApp(sio)

# ---------------- 路由開始 ----------------

@app.get("/")
def read_root():
    return {"message": "後端已啟動，API 正常運作中"}

@app.get("/check-db")
def check_db():
    db = SessionLocal()
    try:
        users = db.query(models.UserModel).all()
        return {"count": len(users), "users": [u.username for u in users]}
    finally:
        db.close()

@app.post("/login")
def login(data: dict = Body(...)):
    db = SessionLocal()
    try:
        username = data.get("username")
        password = data.get("password")
        user = db.query(models.UserModel).filter(models.UserModel.username == username).first()
        if not user or user.hashed_password != password:
            raise HTTPException(status_code=400, detail="帳號或密碼錯誤")
        return {
            "username": user.username,
            "full_name": user.full_name,
            "role": "admin" if user.username == "admin" else "user"
        }
    finally:
        db.close()

@app.get("/board", response_model=List[schemas.ColumnSchema])
async def get_board(db: Session = Depends(get_db)):
    columns = db.query(models.ColumnModel).options(
        joinedload(models.ColumnModel.tasks)
    ).order_by(models.ColumnModel.position).all()
    return columns

@app.post("/tasks")
async def create_task(content: str, column_id: int, db: Session = Depends(get_db)):
    new_task = models.TaskModel(content=content, column_id=column_id)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    await sio.emit("board_updated", {"message": f"新增任務: {content}"})
    return new_task

@app.put("/tasks/{task_id}")
async def update_task(
    task_id: int,
    column_id: int = None,
    content: str = None,
    description: str = None,
    db: Session = Depends(get_db)
):
    task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if column_id is not None: task.column_id = column_id
    if content is not None: task.content = content
    if description is not None: task.description = description
    db.commit()
    db.refresh(task)
    await sio.emit("board_updated", {"message": f"任務 #{task_id} 已更新"})
    return task

@app.delete("/clear-all")
def clear_all(db: Session = Depends(get_db)):
    db.query(models.TaskModel).delete()
    db.query(models.ColumnModel).delete()
    db.commit()
    return {"message": "看板已徹底清空"}

# 最後掛載 Socket.io (放在最後)
app.mount("/socket.io", sio_app)