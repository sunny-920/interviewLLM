# fastapi_app.py
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List, Optional, Dict, Any
import uuid
import json
import os

# 資料庫與模型
from database import init_db, get_db, InterviewSession, InterviewStageRecord, Resume, Company, FeedbackReport
import schemas
import utils

# 核心邏輯：面試官 AI
from interview_llm.core import llm_engine

# 核心邏輯：爬蟲
from interview_llm.crawler import run_crawler

# 核心邏輯：內部交接筆記生成器
from interview_llm.handoff_generator import HandoffGenerator

# 核心邏輯：使用者回饋分析器 (請確保這些檔案存在於 interview_llm/analyzers/)
from interview_llm.analyzers import (
    analyze_telephone, 
    analyze_whiteboard, 
    analyze_manager, 
    analyze_hr,       # 👈 新增：HR 分析
    analyze_overall   # 大回饋分析
)

app = FastAPI(title="InterviewLLM API (MySQL Integration)")

# 初始化資料庫 (若由 DBA 建表可省略)
init_db()

# 初始化 AI 生成器
handoff_gen = HandoffGenerator()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 🛠️ 工具 API：資料準備 (寫入 MySQL)
# ==========================================

@app.post("/users/upload_resume", response_model=schemas.UploadResumeResponse)
async def upload_resume(user_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上傳履歷 JSON 到 MySQL"""
    if not file.filename.endswith(".json"):
        raise HTTPException(400, "Only JSON allowed")
    
    content_bytes = await file.read()
    try:
        content_json = json.loads(content_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON format")

    new_resume = Resume(
        user_id=user_id,
        filename=file.filename,
        content=content_json
    )
    db.add(new_resume)
    db.commit()
    return {"filename": file.filename, "file_path": "DB_RECORD", "message": "Resume saved to MySQL"}

@app.post("/tools/crawl", response_model=schemas.CrawlCompanyResponse)
async def crawl_company_info(req: schemas.CrawlCompanyRequest, db: Session = Depends(get_db)):
    """爬蟲並存入 MySQL"""
    # 1. 爬蟲
    crawl_result = await run_crawler(req.company, req.position)
    content_str = crawl_result.get("summary", json.dumps(crawl_result, ensure_ascii=False))

    # 2. 存入 DB
    new_company = Company(
        company_name=req.company,
        position=req.position,
        content=content_str
    )
    db.add(new_company)
    db.commit()

    return {
        "message": "Crawling successful",
        "company_filename": req.company, # 這裡回傳公司名當作 Key
        "file_path": "DB_RECORD",
        "preview": content_str[:100] + "..."
    }

# ==========================================
# 🚀 面試流程 API
# ==========================================

@app.post("/interview/init", response_model=schemas.InitInterviewResponse)
def init_interview(req: schemas.InitInterviewRequest, db: Session = Depends(get_db)):
    """初始化：從 MySQL 讀取履歷與公司資料，建立 Session"""
    session_id = str(uuid.uuid4())
    sorted_stages = utils.sort_stages(req.selected_stages)

    # 1. 撈履歷
    resume = db.query(Resume).filter(Resume.user_id == req.user_id, Resume.filename == req.resume_filename).first()
    if not resume: raise HTTPException(404, "Resume not found in DB")

    # 2. 撈公司 (這裡簡化用名稱搜尋，實際可依 ID)
    company = db.query(Company).filter(Company.company_name == req.company_filename).first()
    company_context = company.content if company else "（無公司資料）"

    # 3. 建立 Session
    new_session = InterviewSession(
        session_id=session_id,
        user_id=req.user_id,
        current_stage=sorted_stages[0],
        stages_list=sorted_stages, # 需在 Model 支援 JSON List
        history=[],
        resume_snapshot=resume.content,
        company_snapshot=company_context,
        # 初始化交接筆記
        summary_phone=None,
        summary_whiteboard=None,
        summary_manager=None,
        summary_hr=None
    )
    db.add(new_session)
    db.commit()

    return {
        "session_id": session_id,
        "stages_sorted": sorted_stages,
        "message": "Initialized from MySQL",
        "loaded_resume": resume.filename,
        "loaded_company": company.company_name if company else "None"
    }

@app.post("/interview/next", response_model=schemas.NextQuestionResponse)
def next_question(req: schemas.NextQuestionRequest, db: Session = Depends(get_db)):
    """對話：注入交接筆記 (Handoff RAG)"""
    session = db.query(InterviewSession).filter_by(session_id=req.session_id).first()
    if not session: raise HTTPException(404, "Session not found")

    # 1. 收集之前的交接筆記 (Handoff RAG)
    # 這是給「內部 AI 面試官」看的，讓他知道上一關發生什麼事
    previous_summaries = {}
    if session.summary_phone: previous_summaries["Phone Stage"] = session.summary_phone
    if session.summary_whiteboard: previous_summaries["Whiteboard Stage"] = session.summary_whiteboard
    if session.summary_manager: previous_summaries["Manager Stage"] = session.summary_manager

    session_context = {
        "resume": session.resume_snapshot,
        "company_info": session.company_snapshot,
        "history": session.history,
        "current_stage": session.current_stage,
        "previous_summaries": previous_summaries # 👈 關鍵注入
    }

    # 2. 記錄使用者回答
    if req.user_answer:
        session.history.append({"role": "user", "content": req.user_answer})

    # 3. AI 生成回應
    ai_question = llm_engine.next_question(session_context, req.user_answer)
    session.history.append({"role": "assistant", "content": ai_question})
    
    flag_modified(session, "history")
    db.commit()

    # 4. 判斷結束
    end_keywords = ["再見", "掰掰", "bye", "結束", "感謝您", "interview concluded"]
    is_finished = any(k in ai_question.lower() for k in end_keywords)

    return {"stage": session.current_stage, "question": ai_question, "is_stage_finished": is_finished}

@app.post("/interview/save", response_model=schemas.SaveStageResponse)
def save_stage_record(req: schemas.SaveStageRequest, db: Session = Depends(get_db)):
    """存檔：生成交接筆記 (Handoff) 並切換關卡"""
    session = db.query(InterviewSession).filter_by(session_id=req.session_id).first()
    if not session: raise HTTPException(404, "Session not found")

    # 1. 生成交接筆記 (Internal Handoff Note)
    # 這是給「下一位面試官」看的
    print(f"📝 生成 {req.stage} 交接筆記中...")
    handoff_note = handoff_gen.generate_summary(req.stage, session.history)
    
    if req.stage == "phone": session.summary_phone = handoff_note
    elif req.stage == "whiteboard": session.summary_whiteboard = handoff_note
    elif req.stage == "manager": session.summary_manager = handoff_note
    elif req.stage == "hr": session.summary_hr = handoff_note
    
    # 2. 歸檔歷史紀錄 (存入 InterviewStageRecord 表)
    # 假設我們把 JSON 直接存進 DB，或者存成檔案再存路徑
    # 這裡示範存入 DB (需有 content JSON 欄位)
    new_record = InterviewStageRecord(
        record_id=str(uuid.uuid4()),
        user_id=session.user_id,
        session_id=session.session_id,
        stage=req.stage,
        content=session.history # 假設你的 Model 有這個欄位
    )
    db.add(new_record)

    # 3. 切換下一關
    next_stage_name = None
    try:
        # stages_list 若存為 JSON 字串需解析，若用 SQLAlchemy JSON 類型則直接用
        stages = session.stages_list if isinstance(session.stages_list, list) else json.loads(session.stages_list)
        current_idx = stages.index(req.stage)
        if current_idx + 1 < len(stages):
            next_stage_name = stages[current_idx + 1]
            session.current_stage = next_stage_name
            session.history = [] # 清空對話
            flag_modified(session, "history")
        else:
            session.is_completed = True
    except ValueError:
        pass

    db.commit()
    return {"message": "Saved & Handoff Generated", "record_id": new_record.record_id, "next_stage": next_stage_name}


# ==========================================
# 📊 分析 API：使用者回饋 (User Feedback)
# ==========================================

@app.post("/interview/analyze", response_model=schemas.AnalyzeResponse)
def generate_analysis(req: schemas.AnalyzeRequest, db: Session = Depends(get_db)):
    """
    生成給使用者看的回饋報告。
    支援各階段 (phone, whiteboard, manager, hr) 與 overall。
    """
    session = db.query(InterviewSession).filter_by(session_id=req.session_id).first()
    if not session: raise HTTPException(404, "Session not found")

    resume = session.resume_snapshot
    company = session.company_snapshot
    
    analyzer = None
    result_json = {}
    score = None

    # 1. 選擇分析器
    if req.stage == "phone":
        analyzer = analyze_telephone.TelephoneAnalyzer()
        # 小回饋只看當前階段的 history (注意：save 後 history 會清空，需從 StageRecord 撈)
        # 這裡假設前端在 save 之前呼叫，或者我們去撈 StageRecord
        record = db.query(InterviewStageRecord).filter_by(session_id=req.session_id, stage="phone").first()
        history_to_analyze = record.content if record else session.history
        result_json = analyzer.analyze(history_to_analyze, resume, company)

    elif req.stage == "whiteboard":
        analyzer = analyze_whiteboard.WhiteboardAnalyzer()
        record = db.query(InterviewStageRecord).filter_by(session_id=req.session_id, stage="whiteboard").first()
        history_to_analyze = record.content if record else session.history
        result_json = analyzer.analyze(history_to_analyze, resume, company)

    elif req.stage == "manager":
        analyzer = analyze_manager.ManagerAnalyzer()
        record = db.query(InterviewStageRecord).filter_by(session_id=req.session_id, stage="manager").first()
        history_to_analyze = record.content if record else session.history
        result_json = analyzer.analyze(history_to_analyze, resume, company)

    elif req.stage == "hr": # 👈 新增 HR 分析
        analyzer = analyze_hr.HRAnalyzer()
        record = db.query(InterviewStageRecord).filter_by(session_id=req.session_id, stage="hr").first()
        history_to_analyze = record.content if record else session.history
        result_json = analyzer.analyze(history_to_analyze, resume, company)

    elif req.stage == "overall":
        # 大回饋：撈出所有階段的紀錄
        records = db.query(InterviewStageRecord).filter_by(session_id=req.session_id).all()
        # 將所有 history 合併成一個 dict: {"phone": [...], "whiteboard": [...]}
        all_histories = {rec.stage: rec.content for rec in records}
        
        analyzer = analyze_overall.OverallAnalyzer()
        result_json = analyzer.analyze(all_histories, resume, company)
        score = result_json.get("total_score", 0)

    else:
        raise HTTPException(400, "Unknown stage")

    # 2. 存入 FeedbackReport 表
    new_report = FeedbackReport(
        session_id=req.session_id,
        stage=req.stage,
        report_type="overall" if req.stage == "overall" else "single",
        content=result_json,
        score=score
    )
    db.add(new_report)
    db.commit()

    return {"report_id": new_report.id, "content": result_json, "score": score}

@app.get("/interview/reports")
def get_reports(user_id: str, session_id: Optional[str] = None, db: Session = Depends(get_db)):
    """取得回饋報告列表"""
    query = db.query(FeedbackReport).join(InterviewSession).filter(InterviewSession.user_id == user_id)
    if session_id:
        query = query.filter(FeedbackReport.session_id == session_id)
    return query.all()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=8000, reload=True)