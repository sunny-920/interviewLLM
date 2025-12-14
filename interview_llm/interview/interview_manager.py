# interview_manager.py
from openai import OpenAI
from api_config import API_KEY 
from common_utils import read_file_content, save_transcript

class ManagerInterviewer:
    def __init__(self, model_name="gpt-4o"):
        self.client = OpenAI(api_key=API_KEY)
        self.messages = []
        self.SYSTEM_PROMPT = """
[角色設定]
你是 Sarah，研發部門經理。
你的目標是評估應徵者的「專案經驗深度」、「解決問題能力」與「團隊適配度」。

[重點]
1. 請針對履歷中的具體專案（如：智慧路徑搜尋機器人）進行深挖。
2. 使用 STAR 原則（情境、任務、行動、結果）追問。
3. 詢問在壓力下如何做決策，或如何處理技術分歧。
"""

    def start(self, resume_path="resume.txt"):
        resume = read_file_content(resume_path)
        self.messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"履歷：\n{resume}\n請以部門主管 Sarah 身份開始面試，針對專案經驗提問。"}
        ]
        return self._get_response()

    def chat(self, user_input):
        self.messages.append({"role": "user", "content": user_input})
        return self._get_response()

    def _get_response(self):
        res = self.client.chat.completions.create(
            model="gpt-4o", messages=self.messages, temperature=0.7
        )
        reply = res.choices[0].message.content.strip()
        self.messages.append({"role": "assistant", "content": reply})
        return reply

    def end_session(self):
        save_transcript(self.messages, "manager_log", "manager_latest_log", "Sarah")