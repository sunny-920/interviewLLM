# interview_llm/handoff_generator.py
import json
from openai import OpenAI
try:
    from api_config import API_KEY
except ImportError:
    import sys
    sys.path.append("..")
    from api_config import API_KEY

class HandoffGenerator:
    def __init__(self, model_name="gpt-4o"):
        self.client = OpenAI(api_key=API_KEY)
        self.model_name = model_name

    def generate_summary(self, stage: str, history: list) -> dict:
        """
        輸入：該階段對話紀錄
        輸出：交接筆記 JSON
        """
        # 1. 將對話轉為純文字
        transcript = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

        # 2. 設計 Prompt (重點：只看表現，不看履歷)
        system_prompt = f"""
        你是一位資深的人資招募經理。你剛剛結束了一場「{stage}」階段的面試。
        你的任務是根據「對話紀錄」，撰寫一份交接筆記給下一位面試官。

        [分析重點]
        1. 確認候選人表現出的技術能力是否符合職位。
        2. 觀察候選人的溝通邏輯、性格特質。
        3. 找出面試中候選人回答得不清楚、或令人存疑的地方。

        [輸出格式]
        請直接回傳 JSON 格式，不要有 markdown 標記，包含以下欄位：
        - "strengths": [列出 2-3 個明顯優點]
        - "weaknesses": [列出 2-3 個明顯缺點或風險]
        - "suggested_questions": [建議下一位面試官追問的 2 個問題]
        - "overall_score": (1-10分)
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"面試對話紀錄如下：\n{transcript}"}
                ],
                temperature=0.7,
                response_format={"type": "json_object"} # 強制 JSON 輸出
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Handoff generation failed: {e}")
            return {} # 失敗回傳空字典，避免卡死流程