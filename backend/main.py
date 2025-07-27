from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import speech_recognition as sr
import os
import uuid
from geopy.geocoders import Nominatim

app = FastAPI(title="个人知识库API", description="个人知识库后端API服务")

# 添加CORS中间件以允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据模型定义
class KnowledgeItem(BaseModel):
    id: Optional[int] = None
    title: str
    content: str
    category: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

# 模拟数据存储
knowledge_items = [
    KnowledgeItem(id=1, title="项目规划", content="这是项目的初步规划文档", category="项目", location="办公室"),
    KnowledgeItem(id=2, title="技术选型", content="前端使用Vue3，后端使用FastAPI", category="技术", location="家里")
]

# 用于存储上传的音频文件的目录
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 地理编码器
geolocator = Nominatim(user_agent="knowledge_base_app")

# API路由
@app.get("/")
def read_root():
    return {"message": "欢迎使用个人知识库API"}

@app.get("/knowledge")
def get_knowledge_items():
    return knowledge_items

@app.get("/knowledge/{item_id}")
def get_knowledge_item(item_id: int):
    for item in knowledge_items:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="知识条目未找到")

@app.post("/knowledge")
def create_knowledge_item(item: KnowledgeItem):
    # 简单实现，实际应保存到数据库
    new_id = max([item.id for item in knowledge_items]) + 1 if knowledge_items else 1
    item.id = new_id
    
    # 如果提供了经纬度，获取地址信息
    if item.latitude is not None and item.longitude is not None:
        try:
            location = geolocator.reverse(f"{item.latitude}, {item.longitude}")
            item.location = location.address
        except Exception as e:
            print(f"地理编码错误: {e}")
    
    knowledge_items.append(item)
    return item

@app.put("/knowledge/{item_id}")
def update_knowledge_item(item_id: int, updated_item: KnowledgeItem):
    for i, item in enumerate(knowledge_items):
        if item.id == item_id:
            updated_item.id = item_id
            
            # 如果提供了经纬度，获取地址信息
            if updated_item.latitude is not None and updated_item.longitude is not None:
                try:
                    location = geolocator.reverse(f"{updated_item.latitude}, {updated_item.longitude}")
                    updated_item.location = location.address
                except Exception as e:
                    print(f"地理编码错误: {e}")
            
            knowledge_items[i] = updated_item
            return updated_item
    raise HTTPException(status_code=404, detail="知识条目未找到")

@app.delete("/knowledge/{item_id}")
def delete_knowledge_item(item_id: int):
    for i, item in enumerate(knowledge_items):
        if item.id == item_id:
            del knowledge_items[i]
            return {"message": "删除成功"}
    raise HTTPException(status_code=404, detail="知识条目未找到")

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    # 保存上传的音频文件
    file_extension = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)