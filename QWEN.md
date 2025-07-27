# 个人知识库项目 - Qwen Code Context

## 项目概述
构建一个支持语音转文本、会议录音、定位、知识分类存储、RAG检索和AI对话的个人知识库系统。

## 技术栈
- 前端：Vue 3 + TypeScript + Router + Pinia + Vitest + ESLint + Prettier
- 后端：Python + FastAPI + Uvicorn
- 语音处理：SpeechRecognition + PyAudio
- 数据库：SQLite
- RAG引擎：LangChain + Chroma
- 地理定位：HTML5 Geolocation API + Geopy
- AI接口：OpenAI兼容接口
- 用户认证：JWT
- 部署：Docker
- UI设计：移动端友好的自定义界面

## 功能模块

### 1. 用户界面 (前端)
- 知识录入界面（文本/语音）√
- 知识浏览与搜索界面
- 分类管理界面
- 会议录音界面
- AI对话界面
- 地理位置标记功能 √

### 2. 后端服务
- 用户认证服务（JWT）
- 知识管理服务
- 语音识别服务 √
- 会议录音处理服务
- 地理信息服务 √
- RAG检索服务（LangChain + Chroma）
- AI对话服务（OpenAI兼容接口）

### 3. 数据存储
- 知识条目存储（SQLite）
- 分类信息存储（SQLite）
- 语音/音频文件存储
- 地理位置数据存储（SQLite）
- 用户信息存储（SQLite）
- 向量数据存储（Chroma）

## 用户需求确认

1. 数据库：SQLite
2. AI接口：OpenAI兼容的自有接口
3. RAG框架：LangChain
4. 向量数据库：Chroma
5. 部署方式：Docker
6. 用户认证：JWT
7. 界面设计：移动端友好的自定义界面
8. 知识库分类：支持自定义分类，可以针对特定文件进行分类
9. 语言支持：默认中文，无需多语言支持

## 开发计划

### 第一阶段：基础架构搭建
1. 初始化前端Vue 3项目 √
2. 初始化后端FastAPI项目 √
3. 设计数据库模型
4. 实现基本的CRUD API接口 √

### 第二阶段：核心功能开发
1. 实现语音转文本功能 √
2. 实现会议录音功能
3. 实现知识分类存储
4. 实现地理位置标记功能 √

### 第三阶段：高级功能集成
1. 集成RAG检索系统（LangChain + Chroma）
2. 实现AI对话功能（OpenAI兼容接口）
3. 实现用户认证（JWT）
4. 优化搜索和查询性能

### 第四阶段：完善与测试
1. 完善移动端用户界面
2. 进行全面测试
3. 编写Docker配置文件
4. 准备部署文档

## 注意事项
1. 隐私保护：确保用户数据安全
2. 性能优化：优化语音处理和检索速度
3. 兼容性：确保在不同移动设备上正常运行