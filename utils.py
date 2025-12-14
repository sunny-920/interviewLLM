# utils.py
import os
import json
import re
from datetime import datetime
from glob import glob

DATA_DIR = "data"
RESUME_DIR = os.path.join(DATA_DIR, "resumes")
COMPANY_DIR = os.path.join(DATA_DIR, "companies")

STAGE_ORDER = {
    "phone": 1,
    "whiteboard": 2,
    "manager": 3,
    "hr": 4
}

def sort_stages(stages: list) -> list:
    valid_stages = [s for s in stages if s in STAGE_ORDER]
    return sorted(valid_stages, key=lambda x: STAGE_ORDER[x])

def ensure_directories():
    os.makedirs(RESUME_DIR, exist_ok=True)
    os.makedirs(COMPANY_DIR, exist_ok=True)

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).replace(" ", "_")

# --- 讀取履歷 ---
def load_resume_data(user_id: str, filename: str):
    path = os.path.join(RESUME_DIR, user_id, filename)
    if not os.path.exists(path):
        # 容錯：如果不在 user 資料夾，試試看直接在 resumes 下找
        path_fallback = os.path.join(RESUME_DIR, filename)
        if os.path.exists(path_fallback):
            path = path_fallback
        else:
            raise FileNotFoundError(f"Resume file not found: {filename}")
    
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# --- 讀取公司資料 (Init 用) ---
def load_company_data(filename: str) -> str:
    """直接讀取指定的 txt 檔案"""
    path = os.path.join(COMPANY_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Company file not found: {filename}")
    
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# --- 儲存公司資料 (Crawler 用) ---
def save_crawled_company(company: str, position: str, content: str) -> str:
    ensure_directories()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    safe_comp = sanitize_filename(company)
    safe_pos = sanitize_filename(position)
    
    # 檔名範例: 覺揚_SRE_20251214.txt
    filename = f"{safe_comp}_{safe_pos}_{timestamp}.txt"
    path = os.path.join(COMPANY_DIR, filename)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
        
    return filename, path

# --- Session 存檔 ---
def save_session_record(user_id: str, session_id: str, stage: str, data: list):
    base_dir = f"data/users/{user_id}/sessions/{session_id}/{stage}"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    
    filename = datetime.now().strftime("%Y-%m-%dT%H-%M-%S") + ".json"
    file_path = os.path.join(base_dir, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    return file_path