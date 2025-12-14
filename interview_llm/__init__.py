# interview_llm/interview/__init__.py

# 這裡的目的是方便外部 (core.py) 直接匯入
# 這樣 core.py 其實也可以寫成： from .interview import TelephoneInterviewer

from .interview_telephone import TelephoneInterviewer
from .interview_whiteboard import WhiteboardInterviewer
from .interview_manager import ManagerInterviewer
from .interview_hr import HRInterviewer