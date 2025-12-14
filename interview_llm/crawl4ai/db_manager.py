import sqlite3
import os
from pathlib import Path

# 設定資料庫路徑 (存放在上一層資料夾，避免汙染程式碼資料夾)
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "jobs_database.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化資料庫"""
    print(f"   ⚙️  檢查資料庫路徑: {DB_PATH}")
    conn = get_db_connection()
    # 建立資料表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS job_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            input_company TEXT,
            input_position TEXT,
            real_company TEXT,
            real_position TEXT,
            file_path TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def sync_database_with_files():
    """
    同步功能：檢查資料庫中的檔案是否存在。
    如果使用者手動刪除了 txt 檔案，這裡會把資料庫對應的紀錄也刪掉。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, file_path, real_company, real_position FROM job_records")
    rows = cursor.fetchall()
    
    deleted_count = 0
    for row in rows:
        file_path = row["file_path"]
        # 檢查檔案是否存在
        if not os.path.exists(file_path):
            print(f"⚠️ 發現檔案遺失，移除資料庫紀錄：{row['real_company']} - {row['real_position']}")
            conn.execute("DELETE FROM job_records WHERE id = ?", (row["id"],))
            deleted_count += 1
    
    conn.commit()
    conn.close()
    if deleted_count > 0:
        print(f"🧹 資料庫同步完成，共清除了 {deleted_count} 筆無效資料。")

def check_job_exists(input_company, input_position):
    """
    檢查是否已經爬過 (根據使用者的搜尋關鍵字)
    回傳: (True/False, 檔案路徑, 真實公司名)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    # 這裡我們用使用者輸入的關鍵字來判斷是否重複執行
    cursor.execute("""
        SELECT file_path, real_company, real_position 
        FROM job_records 
        WHERE input_company = ? AND input_position = ?
    """, (input_company, input_position))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return True, row["file_path"], row["real_company"]
    return False, None, None

def add_job_record(input_company, input_position, real_company, real_position, file_path):
    """新增一筆紀錄"""
    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO job_records (input_company, input_position, real_company, real_position, file_path)
            VALUES (?, ?, ?, ?, ?)
        """, (input_company, input_position, real_company, real_position, str(file_path)))
        conn.commit()
        print(f"✅ 資料庫已更新：{real_company} - {real_position}")
    except sqlite3.IntegrityError:
        print("⚠️ 資料庫寫入失敗（可能重複）")
    finally:
        conn.close()