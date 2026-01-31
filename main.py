import socketio
from fastapi import FastAPI, Depends, HTTPException, Body
from sqlalchemy.orm import Session, joinedload
import models
import schemas
from database import SessionLocal, engine
from fastapi.middleware.cors import CORSMiddleware
from typing import List

# 1. 建立 Socket.io 服務
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins="*")
sio_app = socketio.ASGIApp(sio)

app = FastAPI()

# 2. CORS 設置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 測試時先用 *，之後再改回你的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 掛載 Socket.io
app.mount("/socket.io", sio_app)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 自動建立資料表
models.Base.metadata.create_all(bind=engine)

# --- 路由開始 ---

@app.get("/")
def read_root():
    return {"message": "後端已啟動"}

@app.post("/login")
def login(data: dict = Body(...), db: Session = Depends(get_db)):
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

@app.on_event("startup")
@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    try:
        # 1. 欄位初始化 (保持不變)
        if db.query(models.ColumnModel).count() == 0:
            db.add_all([
                models.ColumnModel(title="待辦中", position=1),
                models.ColumnModel(title="進行中", position=2),
                models.ColumnModel(title="已完成", position=3)
            ])
            db.commit()

        # 2. 四個測試帳號初始化
        test_users = [
            {"u": "admin", "n": "Admin", "p": "1234"},
            {"u": "stephen", "n": "Stephen", "p": "1234"},
            {"u": "bernie", "n": "Bernie", "p": "1234"},
            {"u": "jenny", "n": "Jenny", "p": "1234"}
        ]

        for user_data in test_users:
            if db.query(models.UserModel).filter(models.UserModel.username == user_data["u"]).count() == 0:
                new_user = models.UserModel(
                    username=user_data["u"],
                    full_name=user_data["n"],
                    hashed_password=user_data["p"]
                )
                db.add(new_user)

        db.commit()
        print("✅ 四個測試帳號 (admin, stephen, bernie, jenny) 已就緒！")

    except Exception as e:
        print(f"❌ 初始化發生錯誤: {e}")
    finally:
        db.close()

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

@app.get("/board", response_model=List[schemas.ColumnSchema])
async def get_board(db: Session = Depends(get_db)):
    # 按照 position 排序，確保看板順序固定
    columns = db.query(models.ColumnModel).options(
        joinedload(models.ColumnModel.tasks)
    ).order_by(models.ColumnModel.position).all()
    return columns

@app.delete("/clear-all")
def clear_all(db: Session = Depends(get_db)):
    db.query(models.TaskModel).delete()
    db.query(models.ColumnModel).delete()
    db.commit()
    return {"message": "看板已徹底清空"}