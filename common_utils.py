# common_utils.py
import json
import os
import datetime
from openai import OpenAI
from api_config import API_KEY

PARAMS_FILE = "params.json"

def read_file_content(filepath):
    """讀取文字檔案內容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"[Error] 找不到檔案: {filepath}")
        return None
    except Exception as e:
        print(f"[Error] 讀取 {filepath} 失敗: {e}")
        return None

def update_latest_log(key, filename):
    """更新 params.json 中的最新 log 檔名"""
    params = {}
    # 預設結構
    default_params = {
        "telephone_latest_log": None,
        "whiteboard_latest_log": None,
        "manager_latest_log": None,
        "hr_latest_log": None
    }

    try:
        if os.path.exists(PARAMS_FILE):
            with open(PARAMS_FILE, 'r', encoding='utf-8') as f:
                params = json.load(f)
    except Exception:
        params = default_params

    # 確保所有 key 都存在
    for k in default_params.keys():
        if k not in params:
            params[k] = None

    params[key] = filename
    
    try:
        with open(PARAMS_FILE, 'w', encoding='utf-8') as f:
            json.dump(params, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[System] 無法更新參數檔: {e}")

def get_latest_log_filename(key):
    """從 params.json 取得指定的 log 檔名"""
    try:
        if os.path.exists(PARAMS_FILE):
            with open(PARAMS_FILE, 'r', encoding='utf-8') as f:
                params = json.load(f)
                return params.get(key)
    except Exception:
        pass
    return None

def save_transcript(messages, prefix, log_key, ai_name):
    """通用存檔函式"""
    if len(messages) <= 2: return None

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"--- {prefix.upper()} 面試紀錄 ---\n\n")
            for msg in messages[2:]:
                role = ai_name if msg["role"] == "assistant" else "應徵者"
                f.write(f"{role}:\n{msg['content']}\n\n")
        
        print(f"\n[System] 對話紀錄已儲存至: {filename}")
        update_latest_log(log_key, filename)
        return filename
    except Exception as e:
        print(f"[Error] 存檔失敗: {e}")
        return None

def run_gpt_analysis(system_prompt, user_content, model="gpt-4o"):
    """通用的 GPT 分析請求函式"""
    client = OpenAI(api_key=API_KEY)
    try:
        print("正在進行 AI 分析，請稍候...")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"分析失敗: {e}"