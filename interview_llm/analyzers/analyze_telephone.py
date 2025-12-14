# interview_llm/analyzers/analyze_telephone.py
from .base_analyzer import BaseAnalyzer

class TelephoneAnalyzer(BaseAnalyzer):
    def analyze(self, history, resume, company_info):
        system_prompt = """
        你是一位專業的面試教練。請分析這場「電話面試」的紀錄。
        
        [輸入資料權重]
        1. 對話紀錄 (History)：權重 80% (分析重點)
        2. 履歷 (Resume)：權重 20% (僅用於比對一致性)
        
        [分析任務]
        1. 溝通清晰度：回答是否切題、邏輯是否通順。
        2. 真實性檢查：使用者的回答是否與履歷內容有矛盾？(若有，請指出)
        3. 亮點與改進：列出 1 個亮點與 1 個改進點。

        [輸出格式]
        請回傳 JSON：
        {
            "clarity_feedback": "...",
            "consistency_check": "一致/不一致，說明...",
            "highlight": "...",
            "suggestion": "..."
        }
        """
        return self._call_llm(system_prompt, history, resume, company_info)