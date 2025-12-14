# interview_whiteboard.py
import sys
from openai import OpenAI
from api_config import API_KEY 
from common_utils import read_file_content, save_transcript

class WhiteboardInterviewer:
    def __init__(self, model_name="gpt-4o"):
        self.model_name = model_name
        self.client = OpenAI(api_key=API_KEY)
        self.messages = []
        self.SYSTEM_PROMPT = """
[角色設定]
你是 Alex，一位資深軟體工程師。你的任務是進行「白板題 (Whiteboard Coding)」面試。
你專注於演算法、資料結構 (C/C++, Python) 與解題邏輯。

[流程]
1. 出題：根據履歷中的技能 (如 C++ 或 Python)，出一道中等難度的演算法題目 (類似 LeetCode Medium)。
2. 互動：請面試者先說明解題思路，再寫出程式碼。
3. 檢核：檢查程式碼的正確性、邊界條件與時間複雜度。
4. 討論：若有錯誤，引導面試者修正；若正確，詢問如何優化。
"""

    def start(self, resume_path="resume.txt"):
        resume = read_file_content(resume_path)
        self.messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"應徵者履歷：\n{resume}\n請出一道適合的題目開始面試。"}
        ]
        return self._get_response()

    def chat(self, user_input):
        self.messages.append({"role": "user", "content": user_input})
        return self._get_response()

    def _get_response(self):
        try:
            res = self.client.chat.completions.create(
                model=self.model_name, messages=self.messages, temperature=0.5 # 技術題溫度低一點較精確
            )
            reply = res.choices[0].message.content.strip()
            self.messages.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            return f"API Error: {e}"

    def end_session(self):
        save_transcript(self.messages, "whiteboard_log", "whiteboard_latest_log", "Alex")