# interview_llm/analyzers/analyze_overall.py
from .base_analyzer import BaseAnalyzer

class OverallAnalyzer(BaseAnalyzer):
    def analyze(self, all_histories, resume, company_info):
        """
        all_histories: 包含所有階段對話的 Dict 或 List
        """
        system_prompt = """
        你是一位高階招聘經理。使用者完成了所有階段的面試。
        請根據所有對話紀錄，進行「最終量化評估」。

        [評分標準 (0-100分)]
        請針對以下維度打分：
        1. 技術能力 (Hard Skills)
        2. 溝通協作 (Soft Skills)
        3. 文化契合度 (Culture Fit)
        4. 邏輯思維 (Logic)

        [輸出格式]
        請回傳 JSON，供前端繪製圖表：
        {
            "total_score": 85,
            "dimensions": {
                "technical": 80,
                "communication": 90,
                "culture": 85,
                "logic": 75
            },
            "overall_comment": "總體來說...",
            "hire_recommendation": "Strong Hire / Hire / No Hire"
        }
        """
        return self._call_llm(system_prompt, all_histories, resume, company_info)