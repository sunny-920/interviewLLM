# interview_llm/core.py
import sys
import os
from typing import Dict, Any, Optional

# 設定路徑以確保能找到根目錄的模組
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    # ==========================================
    # 🔧 修改 Import：指向新的 interview 資料夾
    # ==========================================
    # 這裡假設你的資料夾結構是 interview_llm/interview/interview_telephone.py
    # 使用相對匯入 (from .interview.xxx)
    from .interview.interview_telephone import TelephoneInterviewer
    from .interview.interview_whiteboard import WhiteboardInterviewer
    from .interview.interview_manager import ManagerInterviewer
    from .interview.interview_hr import HRInterviewer
except ImportError:
    # 若相對匯入失敗 (例如直接執行 core.py)，嘗試絕對路徑
    try:
        from interview_llm.interview.interview_telephone import TelephoneInterviewer
        from interview_llm.interview.interview_whiteboard import WhiteboardInterviewer
        from interview_llm.interview.interview_manager import ManagerInterviewer
        from interview_llm.interview.interview_hr import HRInterviewer
    except ImportError:
        print("⚠️ Warning: 無法匯入面試官模組，請檢查資料夾結構。")
        pass

class InterviewLLM:
    def __init__(self):
        pass

    def _get_interviewer_agent(self, stage: str):
        stage = str(stage).lower()
        if "phone" in stage or "telephone" in stage:
            return TelephoneInterviewer()
        elif "whiteboard" in stage:
            return WhiteboardInterviewer()
        elif "manager" in stage:
            return ManagerInterviewer()
        elif "hr" in stage:
            return HRInterviewer()
        else:
            return TelephoneInterviewer()

    def next_question(self, session_context: Dict[str, Any], user_answer: Optional[str] = None) -> str:
        current_stage = session_context.get("current_stage", "phone")
        history = session_context.get("history", [])
        resume = session_context.get("resume", {})
        company_info = session_context.get("company_info", {})
        
        # 🆕 取得交接筆記 (Handoff Summaries)
        previous_summaries = session_context.get("previous_summaries", {})

        # 1. 取得全新 Agent
        try:
            agent = self._get_interviewer_agent(current_stage)
        except NameError:
            return "系統錯誤：找不到對應的面試官模組。"

        # 2. 注入資料 (Context)
        if hasattr(agent, "set_context"):
            agent.set_context(resume, company_info)
            
        # 🆕 注入交接筆記 (直接設定屬性)
        # 你的 agent 程式碼中 (如 interview_telephone.py) 
        # 可以用 self.previous_summaries 來讀取這個變數
        agent.previous_summaries = previous_summaries

        # 3. 重建 Agent 的大腦 (System Prompt + Resume + Summaries)
        if hasattr(agent, "build_system_messages"):
            agent.messages = agent.build_system_messages()

        # 4. 判斷是否為剛開始 (AI 先攻)
        is_first_turn = (user_answer is None and not self._has_ai_spoke(history))

        if is_first_turn:
            # AI 開場
            return agent._get_response()

        # 5. 恢復對話歷史 (Restore Memory)
        chat_history = [m for m in history if m.get("role") != "system"]
        agent.messages.extend(chat_history)

        # 6. 進行對話
        response = agent.chat(user_answer if user_answer else "")
        return response

    def _has_ai_spoke(self, history: list) -> bool:
        for msg in history:
            if msg.get("role") == "assistant":
                return True
        return False

llm_engine = InterviewLLM()# interview_llm/core.py
import sys
import os
from typing import Dict, Any, Optional

# 設定路徑以確保能找到根目錄的模組
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    # ==========================================
    # 🔧 修改 Import：指向新的 interview 資料夾
    # ==========================================
    # 這裡假設你的資料夾結構是 interview_llm/interview/interview_telephone.py
    # 使用相對匯入 (from .interview.xxx)
    from .interview.interview_telephone import TelephoneInterviewer
    from .interview.interview_whiteboard import WhiteboardInterviewer
    from .interview.interview_manager import ManagerInterviewer
    from .interview.interview_hr import HRInterviewer
except ImportError:
    # 若相對匯入失敗 (例如直接執行 core.py)，嘗試絕對路徑
    try:
        from interview_llm.interview.interview_telephone import TelephoneInterviewer
        from interview_llm.interview.interview_whiteboard import WhiteboardInterviewer
        from interview_llm.interview.interview_manager import ManagerInterviewer
        from interview_llm.interview.interview_hr import HRInterviewer
    except ImportError:
        print("⚠️ Warning: 無法匯入面試官模組，請檢查資料夾結構。")
        pass

class InterviewLLM:
    def __init__(self):
        pass

    def _get_interviewer_agent(self, stage: str):
        stage = str(stage).lower()
        if "phone" in stage or "telephone" in stage:
            return TelephoneInterviewer()
        elif "whiteboard" in stage:
            return WhiteboardInterviewer()
        elif "manager" in stage:
            return ManagerInterviewer()
        elif "hr" in stage:
            return HRInterviewer()
        else:
            return TelephoneInterviewer()

    def next_question(self, session_context: Dict[str, Any], user_answer: Optional[str] = None) -> str:
        current_stage = session_context.get("current_stage", "phone")
        history = session_context.get("history", [])
        resume = session_context.get("resume", {})
        company_info = session_context.get("company_info", {})
        
        # 🆕 取得交接筆記 (Handoff Summaries)
        previous_summaries = session_context.get("previous_summaries", {})

        # 1. 取得全新 Agent
        try:
            agent = self._get_interviewer_agent(current_stage)
        except NameError:
            return "系統錯誤：找不到對應的面試官模組。"

        # 2. 注入資料 (Context)
        if hasattr(agent, "set_context"):
            agent.set_context(resume, company_info)
            
        # 🆕 注入交接筆記 (直接設定屬性)
        # 你的 agent 程式碼中 (如 interview_telephone.py) 
        # 可以用 self.previous_summaries 來讀取這個變數
        agent.previous_summaries = previous_summaries

        # 3. 重建 Agent 的大腦 (System Prompt + Resume + Summaries)
        if hasattr(agent, "build_system_messages"):
            agent.messages = agent.build_system_messages()

        # 4. 判斷是否為剛開始 (AI 先攻)
        is_first_turn = (user_answer is None and not self._has_ai_spoke(history))

        if is_first_turn:
            # AI 開場
            return agent._get_response()

        # 5. 恢復對話歷史 (Restore Memory)
        chat_history = [m for m in history if m.get("role") != "system"]
        agent.messages.extend(chat_history)

        # 6. 進行對話
        response = agent.chat(user_answer if user_answer else "")
        return response

    def _has_ai_spoke(self, history: list) -> bool:
        for msg in history:
            if msg.get("role") == "assistant":
                return True
        return False

llm_engine = InterviewLLM()