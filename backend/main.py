from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import speech_recognition as sr
import os
import uuid
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import sqlite3
from pathlib import Path
import openai
from rag import initialize_rag_system, get_knowledge_items_from_db

# JWT配置
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OpenAI配置
OPENAI_API_KEY = "your-openai-api-key"
openai.api_key = OPENAI_API_KEY

app = FastAPI(title="个人知识库API", description="个人知识库后端API服务")

# 初始化RAG系统
rag_system = initialize_rag_system()

# 添加CORS中间件以允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2密码Bearer令牌
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 数据模型定义
class User(BaseModel):
    id: Optional[int] = None
    username: str
    email: str
    hashed_password: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class KnowledgeItem(BaseModel):
    id: Optional[int] = None
    title: str
    content: str
    category: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    user_id: Optional[int] = None

class Category(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    user_id: Optional[int] = None

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

# 数据库文件路径
DB_FILE = Path("knowledge_base.db")

# 地理编码器
geolocator = Nominatim(user_agent="knowledge_base_app")

# 工具函数
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# RAG相关API
@app.post("/rag/initialize")
def initialize_rag():
    """初始化RAG系统并加载所有知识条目"""
    try:
        # 从数据库获取所有知识条目
        knowledge_items = get_knowledge_items_from_db()
        
        # 添加到向量数据库
        result = rag_system.add_knowledge(knowledge_items)
        
        return {"message": "RAG系统初始化成功", "details": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"初始化RAG系统时出错: {e}")

@app.post("/rag/query")
def query_rag(query: str, user_id: Optional[int] = None):
    """使用RAG查询知识"""
    try:
        result = rag_system.query_knowledge(query, user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG查询时出错: {e}")

@app.post("/rag/update")
def update_rag():
    """更新RAG向量数据库（重新加载所有知识条目）"""
    try:
        # 从数据库获取所有知识条目
        knowledge_items = get_knowledge_items_from_db()
        
        # 添加到向量数据库
        result = rag_system.add_knowledge(knowledge_items)
        
        return {"message": "RAG向量数据库更新成功", "details": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新RAG向量数据库时出错: {e}")

# 用户相关API
@app.post("/users/", response_model=User)
def create_user(user: UserCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查用户是否已存在
    cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (user.username, user.email))
    existing_user = cursor.fetchone()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名或邮箱已存在")
    
    # 创建新用户
    hashed_password = get_password_hash(user.password)
    cursor.execute(
        "INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)",
        (user.username, user.email, hashed_password)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    
    return User(id=user_id, username=user.username, email=user.email)

@app.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 验证用户
    cursor.execute("SELECT * FROM users WHERE username = ?", (form_data.username,))
    user_row = cursor.fetchone()
    conn.close()
    
    if not user_row or not verify_password(form_data.password, user_row['hashed_password']):
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_row['username']}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# 知识条目相关API
@app.get("/knowledge")
def get_knowledge_items():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM knowledge_items")
    items = cursor.fetchall()
    conn.close()
    
    # 转换为KnowledgeItem对象列表
    knowledge_items = [
        KnowledgeItem(
            id=item['id'],
            title=item['title'],
            content=item['content'],
            category=item['category'],
            location=item['location'],
            latitude=item['latitude'],
            longitude=item['longitude'],
            user_id=item['user_id']
        )
        for item in items
    ]
    
    return knowledge_items

@app.get("/knowledge/{item_id}")
def get_knowledge_item(item_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM knowledge_items WHERE id = ?", (item_id,))
    item = cursor.fetchone()
    conn.close()
    
    if not item:
        raise HTTPException(status_code=404, detail="知识条目未找到")
    
    return KnowledgeItem(
        id=item['id'],
        title=item['title'],
        content=item['content'],
        category=item['category'],
        location=item['location'],
        latitude=item['latitude'],
        longitude=item['longitude'],
        user_id=item['user_id']
    )

@app.post("/knowledge")
def create_knowledge_item(item: KnowledgeItem):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 如果提供了经纬度，获取地址信息
    location_str = item.location
    if item.latitude is not None and item.longitude is not None:
        try:
            location = geolocator.reverse(f"{item.latitude}, {item.longitude}")
            location_str = location.address
        except Exception as e:
            print(f"地理编码错误: {e}")
    
    cursor.execute(
        "INSERT INTO knowledge_items (title, content, category, location, latitude, longitude, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (item.title, item.content, item.category, location_str, item.latitude, item.longitude, item.user_id)
    )
    conn.commit()
    item_id = cursor.lastrowid
    conn.close()
    
    return KnowledgeItem(
        id=item_id,
        title=item.title,
        content=item.content,
        category=item.category,
        location=location_str,
        latitude=item.latitude,
        longitude=item.longitude,
        user_id=item.user_id
    )

@app.put("/knowledge/{item_id}")
def update_knowledge_item(item_id: int, updated_item: KnowledgeItem):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查条目是否存在
    cursor.execute("SELECT * FROM knowledge_items WHERE id = ?", (item_id,))
    existing_item = cursor.fetchone()
    if not existing_item:
        conn.close()
        raise HTTPException(status_code=404, detail="知识条目未找到")
    
    # 如果提供了经纬度，获取地址信息
    location_str = updated_item.location
    if updated_item.latitude is not None and updated_item.longitude is not None:
        try:
            location = geolocator.reverse(f"{updated_item.latitude}, {updated_item.longitude}")
            location_str = location.address
        except Exception as e:
            print(f"地理编码错误: {e}")
    
    cursor.execute(
        "UPDATE knowledge_items SET title=?, content=?, category=?, location=?, latitude=?, longitude=?, user_id=? WHERE id=?",
        (updated_item.title, updated_item.content, updated_item.category, location_str, 
         updated_item.latitude, updated_item.longitude, updated_item.user_id, item_id)
    )
    conn.commit()
    conn.close()
    
    return KnowledgeItem(
        id=item_id,
        title=updated_item.title,
        content=updated_item.content,
        category=updated_item.category,
        location=location_str,
        latitude=updated_item.latitude,
        longitude=updated_item.longitude,
        user_id=updated_item.user_id
    )

@app.delete("/knowledge/{item_id}")
def delete_knowledge_item(item_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查条目是否存在
    cursor.execute("SELECT * FROM knowledge_items WHERE id = ?", (item_id,))
    existing_item = cursor.fetchone()
    if not existing_item:
        conn.close()
        raise HTTPException(status_code=404, detail="知识条目未找到")
    
    cursor.execute("DELETE FROM knowledge_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    
    return {"message": "删除成功"}

# 分类相关API
@app.get("/categories")
def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    conn.close()
    
    # 转换为Category对象列表
    category_list = [
        Category(
            id=category['id'],
            name=category['name'],
            description=category['description'],
            user_id=category['user_id']
        )
        for category in categories
    ]
    
    return category_list

@app.post("/categories")
def create_category(category: Category):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO categories (name, description, user_id) VALUES (?, ?, ?)",
        (category.name, category.description, category.user_id)
    )
    conn.commit()
    category_id = cursor.lastrowid
    conn.close()
    
    return Category(
        id=category_id,
        name=category.name,
        description=category.description,
        user_id=category.user_id
    )

@app.delete("/categories/{category_id}")
def delete_category(category_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查分类是否存在
    cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
    existing_category = cursor.fetchone()
    if not existing_category:
        conn.close()
        raise HTTPException(status_code=404, detail="分类未找到")
    
    # 删除关联的知识条目
    cursor.execute("DELETE FROM knowledge_items WHERE category = ?", (existing_category['name'],))
    
    # 删除分类
    cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    conn.close()
    
    return {"message": "分类删除成功"}

# 语音识别API
@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    # 保存上传的音频文件
    file_extension = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join("uploads", filename)
    os.makedirs("uploads", exist_ok=True)
    
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    # 使用SpeechRecognition进行语音识别
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(file_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="zh-CN")
        # 删除临时文件
        os.remove(file_path)
        return {"text": text}
    except sr.UnknownValueError:
        raise HTTPException(status_code=400, detail="无法识别音频内容")
    except sr.RequestError as e:
        raise HTTPException(status_code=500, detail=f"语音识别服务错误: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理音频文件时出错: {e}")

# 会议录音上传API
@app.post("/meeting-recordings")
async def upload_meeting_recording(file: UploadFile = File(...)):
    # 保存上传的会议录音文件
    file_extension = file.filename.split(".")[-1]
    filename = f"meeting_{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join("uploads", filename)
    os.makedirs("uploads", exist_ok=True)
    
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    return {"message": "会议录音上传成功", "filename": filename}

@app.get("/meeting-recordings")
def get_meeting_recordings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM meeting_recordings")
    recordings = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": recording["id"],
            "filename": recording["filename"],
            "title": recording["title"],
            "description": recording["description"],
            "created_at": recording["created_at"],
            "user_id": recording["user_id"]
        }
        for recording in recordings
    ]

@app.post("/meeting-recordings/{recording_id}")
def update_meeting_recording(recording_id: int, title: str, description: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查录音是否存在
    cursor.execute("SELECT * FROM meeting_recordings WHERE id = ?", (recording_id,))
    existing_recording = cursor.fetchone()
    if not existing_recording:
        conn.close()
        raise HTTPException(status_code=404, detail="会议录音未找到")
    
    # 更新录音信息
    cursor.execute(
        "UPDATE meeting_recordings SET title=?, description=? WHERE id=?",
        (title, description, recording_id)
    )
    conn.commit()
    conn.close()
    
    return {"message": "会议录音信息更新成功"}

@app.delete("/meeting-recordings/{recording_id}")
def delete_meeting_recording(recording_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查录音是否存在
    cursor.execute("SELECT * FROM meeting_recordings WHERE id = ?", (recording_id,))
    existing_recording = cursor.fetchone()
    if not existing_recording:
        conn.close()
        raise HTTPException(status_code=404, detail="会议录音未找到")
    
    # 删除录音文件
    file_path = os.path.join("uploads", existing_recording["filename"])
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # 删除数据库记录
    cursor.execute("DELETE FROM meeting_recordings WHERE id = ?", (recording_id,))
    conn.commit()
    conn.close()
    
    return {"message": "会议录音删除成功"}

# AI对话API
@app.post("/chat")
async def chat_completion(request: ChatRequest):
    try:
        # 调用OpenAI API进行对话
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[msg.dict() for msg in request.messages],
            max_tokens=500,
            temperature=0.7
        )
        
        # 返回AI的回复
        return {"response": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI对话服务错误: {e}")

@app.get("/")
def read_root():
    return {"message": "欢迎使用个人知识库API"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)