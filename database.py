# database.py
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# ==========================================
# ⚙️ 資料庫連線設定 (請填入前端給你的資訊)
# ==========================================
# 建議寫在環境變數或 config 檔，這裡方便測試先寫死
DB_USER = "root"          # 請修改
DB_PASSWORD = "password"  # 請修改
DB_HOST = "localhost"     # 請修改
DB_PORT = "3306"          # 請修改
DB_NAME = "ai_interview_db" # 請修改

# 組合連線字串: mysql+pymysql://user:password@host:port/dbname
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    pool_recycle=3600, # MySQL 連線會逾時，設定自動回收
    pool_pre_ping=True # 每次連線前先 ping 一下確認活著
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# 🗂️ 資料表模型定義 (對應需求書)
# ==========================================

# 1. 履歷表 (唯讀：我們只負責讀，前端負責寫入)
class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), index=True)
    filename = Column(String(255))
    content = Column(JSON) # 存放履歷 JSON 結構
    created_at = Column(DateTime, default=datetime.now)

# 2. 公司資料表 (讀寫：爬蟲會寫入，Init 會讀取)
class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(100), index=True)
    position = Column(String(100), index=True)
    content = Column(Text) # 存放爬蟲文字結果
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# 3. 面試 Session 表 (核心：我們負責讀寫)
class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    
    session_id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(50), index=True)
    current_stage = Column(String(20))
    
    # 對話紀錄
    history = Column(JSON, default=list)
    
    # 備份當時的 Context (避免履歷被刪除後面試壞掉)
    resume_snapshot = Column(JSON)
    company_snapshot = Column(Text)
    
    # AI 交接筆記 (Handoff Notes)
    summary_phone = Column(JSON, nullable=True)
    summary_whiteboard = Column(JSON, nullable=True)
    summary_manager = Column(JSON, nullable=True)
    summary_hr = Column(JSON, nullable=True)
    
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 初始化 (建立資料表)
# 注意：如果是 MySQL，通常建議由資料庫管理員先建好 Table，
# 但這行指令會嘗試自動建立不存在的表，開發階段很方便。
def init_db():
    Base.metadata.create_all(bind=engine)

# database.py 新增這段
class FeedbackReport(Base):
    __tablename__ = "feedback_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), index=True) # 建議設外鍵 ForeignKey("interview_sessions.session_id")
    stage = Column(String(20))   # phone, whiteboard, manager, overall
    report_type = Column(String(10)) # single, overall
    content = Column(JSON)       # 存前端要顯示的結構化資料
    score = Column(Integer, nullable=True) # 0-100 分
    created_at = Column(DateTime, default=datetime.now)
