# interview_hr.py
from openai import OpenAI
from api_config import API_KEY 
from common_utils import read_file_content, save_transcript

class HRInterviewer:
    def __init__(self, model_name="gpt-4o"):
        self.client = OpenAI(api_key=API_KEY)
        self.messages = []
        # 您的 HR Prompt
        self.SYSTEM_PROMPT = """
[角色設定]
你現在是一位名叫 Emily 的專業 HR (人資) 面試官。
(此處請貼上您原本的 HR Prompt)
"""

    def start(self, resume_path="resume.txt"):
        resume = read_file_content(resume_path)
        self.messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"履歷：\n{resume}\n請以 HR Emily 身份開始面試。"}
        ]
        return self._get_response()

    def chat(self, user_input):
        self.messages.append({"role": "user", "content": user_input})
        return self._get_response()

    def _get_response(self):
        res = self.client.chat.completions.create(
            model="gpt-4o", messages=self.messages, temperature=0.8
        )
        reply = res.choices[0].message.content.strip()
        self.messages.append({"role": "assistant", "content": reply})
        return reply

    def end_session(self):
        save_transcript(self.messages, "hr_log", "hr_latest_log", "Emily")