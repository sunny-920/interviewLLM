# interview_llm/analyzers/base_analyzer.py
import json
from openai import OpenAI
try:
    from api_config import API_KEY
except ImportError:
    import sys
    sys.path.append("..")
    from api_config import API_KEY

class BaseAnalyzer:
    def __init__(self, model_name="gpt-4o"):
        self.client = OpenAI(api_key=API_KEY)
        self.model_name = model_name

    def _call_llm(self, system_prompt, history, resume, company_info):
        # 將歷史紀錄轉為字串
        history_str = json.dumps(history, ensure_ascii=False) if isinstance(history, list) else str(history)
        
        user_msg = f"""
        【應徵者履歷】
        {str(resume)}
        
        【公司資料】
        {str(company_info)}
        
        【對話紀錄】
        {history_str}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Analysis failed: {e}")
            return {"error": str(e)}

    def analyze(self, history, resume, company_info):
        raise NotImplementedError("Subclasses must implement analyze method")