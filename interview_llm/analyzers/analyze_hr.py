# interview_llm/analyzers/analyze_hr.py
from .base_analyzer import BaseAnalyzer

class HRAnalyzer(BaseAnalyzer):
    def analyze(self, history, resume, company_info):
        system_prompt = """
        你是一位資深的人力資源總監。使用者剛完成了「HR 文化契合度面試」。
        請根據對話紀錄與履歷進行分析。

        [分析重點]
        1. 動機與穩定性：應徵者對公司的熱誠是否足夠？離職原因是否合理？
        2. 文化契合度：應徵者的價值觀是否符合公司文化 (參考公司資料)。
        3. 薪資與期望：應徵者的期望是否合理 (若對話中有提到)。

        [輸出格式 (JSON)]
        {
            "culture_fit_score": 1-10,
            "motivation_analysis": "...",
            "red_flags": ["如果有明顯風險請列出", "無則留空"],
            "suggestion": "針對 HR 面試的改進建議"
        }
        """
        return self._call_llm(system_prompt, history, resume, company_info)