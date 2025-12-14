# schemas.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Task 2: 初始化面試 (純讀檔版) ---
class InitInterviewRequest(BaseModel):
    user_id: str
    
    # 前端直接告訴後端要讀哪兩個檔案
    resume_filename: str   # ex: "resume_Sunny.json"
    company_filename: str  # ex: "覺揚_軟體工程師_2025.txt"
    
    selected_stages: List[str]

class InitInterviewResponse(BaseModel):
    session_id: str
    stages_sorted: List[str]
    message: str
    loaded_resume: str
    loaded_company: str

# --- 新增: 爬蟲專用 API ---
class CrawlCompanyRequest(BaseModel):
    company: str
    position: str

class CrawlCompanyResponse(BaseModel):
    message: str
    company_filename: str # 回傳檔名給前端，讓前端下次 call init 用
    file_path: str
    preview: str

# --- Next (不變) ---
class NextQuestionRequest(BaseModel):
    session_id: str
    user_answer: Optional[str] = None

class NextQuestionResponse(BaseModel):
    stage: str
    question: str
    is_stage_finished: bool

# --- Save (不變) ---
class SaveStageRequest(BaseModel):
    session_id: str
    stage: str

class SaveStageResponse(BaseModel):
    message: str
    record_id: str
    next_stage: Optional[str]

# --- Delete & Records (不變) ---
class DeleteRecordRequest(BaseModel):
    user_id: str

class RecordResponse(BaseModel):
    record_id: str
    json_path: str
    created_at: datetime