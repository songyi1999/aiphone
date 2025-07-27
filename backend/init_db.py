import sqlite3
from pathlib import Path

# 创建数据库文件和连接
DB_FILE = Path("knowledge_base.db")
DB_FILE.parent.mkdir(exist_ok=True)

# 创建数据库连接
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# 创建用户表
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# 创建知识条目表
cursor.execute("""
CREATE TABLE IF NOT EXISTS knowledge_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT,
    location TEXT,
    latitude REAL,
    longitude REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id)
)
""")

# 创建分类表
cursor.execute("""
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id)
)
""")

# 创建知识条目与分类的关联表
cursor.execute("""
CREATE TABLE IF NOT EXISTS item_categories (
    item_id INTEGER,
    category_id INTEGER,
    FOREIGN KEY (item_id) REFERENCES knowledge_items (id),
    FOREIGN KEY (category_id) REFERENCES categories (id),
    PRIMARY KEY (item_id, category_id)
)
""")

# 创建会议录音表
cursor.execute("""
CREATE TABLE IF NOT EXISTS meeting_recordings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    title TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id)
)
""")

# 提交更改并关闭连接
conn.commit()
conn.close()

print("数据库初始化完成")