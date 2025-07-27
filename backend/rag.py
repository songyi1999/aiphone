import os
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain_openai import OpenAI
from langchain.docstore.document import Document
import sqlite3
from pathlib import Path
import openai

# OpenAI配置
OPENAI_API_KEY = "your-openai-api-key"
openai.api_key = OPENAI_API_KEY

# Chroma数据库路径
CHROMA_DB_PATH = "./chroma_db"

class RAGSystem:
    def __init__(self):
        # 初始化嵌入模型
        self.embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        
        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # 初始化LLM
        self.llm = OpenAI(
            openai_api_key=OPENAI_API_KEY,
            temperature=0.7,
            max_tokens=500
        )
        
        # 初始化Chroma向量数据库
        self.vectorstore = Chroma(
            persist_directory=CHROMA_DB_PATH,
            embedding_function=self.embeddings
        )
    
    def add_knowledge(self, knowledge_items):
        """将知识条目添加到向量数据库中"""
        documents = []
        ids = []
        
        for item in knowledge_items:
            # 创建文档对象
            doc = Document(
                page_content=f"标题: {item['title']}\n内容: {item['content']}\n分类: {item['category']}",
                metadata={
                    "id": item['id'],
                    "title": item['title'],
                    "category": item['category'],
                    "user_id": item['user_id']
                }
            )
            documents.append(doc)
            ids.append(str(item['id']))
        
        # 分割文档
        split_docs = self.text_splitter.split_documents(documents)
        split_ids = [f"{doc.metadata['id']}-{i}" for i, doc in enumerate(split_docs)]
        
        # 将文档添加到向量数据库
        self.vectorstore.add_documents(split_docs, ids=split_ids)
        
        return {"message": f"成功添加 {len(split_docs)} 个文档到向量数据库"}
    
    def query_knowledge(self, query, user_id=None):
        """使用RAG查询知识"""
        # 执行检索
        results = self.vectorstore.similarity_search(query, k=4)  # 返回最相关的4个结果
        
        # 获取上下文
        context = "\n\n".join([doc.page_content for doc in results])
        
        # 构建提示
        prompt = f"基于以下上下文回答问题:\n\n{context}\n\n问题: {query}\n\n回答:"
        
        # 生成回答
        response = self.llm.invoke(prompt)
        
        return {
            "query": query,
            "response": response,
            "sources": [
                {
                    "title": doc.metadata.get("title", ""),
                    "category": doc.metadata.get("category", ""),
                    "content": doc.page_content
                } 
                for doc in results
            ]
        }

# 全局RAG系统实例
rag_system = None

def initialize_rag_system():
    """初始化RAG系统"""
    global rag_system
    if rag_system is None:
        rag_system = RAGSystem()
    return rag_system

def get_knowledge_items_from_db():
    """从SQLite数据库获取所有知识条目"""
    DB_FILE = Path("knowledge_base.db")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM knowledge_items")
    items = cursor.fetchall()
    conn.close()
    
    # 转换为字典列表
    return [dict(item) for item in items]