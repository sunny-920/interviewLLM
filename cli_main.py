# cli_main.py
import sys
import asyncio
import os

# 1. 修正匯入路徑：分析模組現在位於 interview_llm 資料夾內
try:
    from interview_llm import analyze_telephone
    from interview_llm import analyze_whiteboard
    from interview_llm import analyze_manager
    from interview_llm import analyze_hr
    from interview_llm import analyze_overall
    # 引入新的爬蟲
    from interview_llm.crawler import run_crawler
except ImportError as e:
    # 如果你在根目錄執行，應該不會報錯；若報錯請檢查資料夾結構
    print(f"⚠️ 匯入模組失敗 (若不影響面試可忽略): {e}")

# 匯入面試官模組 (位於根目錄)
from interview_telephone import TelephoneInterviewer
from interview_whiteboard import WhiteboardInterviewer
from interview_manager import ManagerInterviewer
from interview_hr import HRInterviewer

# --- 輔助函式：讀取本地檔案 ---
def read_local_file(filename):
    """讀取根目錄下的 txt 檔案"""
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return None
                return content
        except Exception as e:
            print(f"❌ 讀取 {filename} 失敗: {e}")
            return None
    else:
        print(f"⚠️ 找不到檔案: {filename} (將使用預設空值)")
        return None

def run_interview_session(interviewer_class, name):
    agent = interviewer_class()
    print(f"\n" + "="*40)
    print(f"🚀 啟動 {name} 模擬系統")
    print(f"="*40)
    print("輸入 'exit' 或 '結束' 可隨時離開。\n")

    # ==========================================
    # 👇 修改重點：讀取本地檔案並注入 Agent
    # ==========================================
    print("📂 正在讀取本地資料...")
    
    local_resume = read_local_file("resume.txt")
    local_company = read_local_file("company.txt")
    
    # 如果找不到 company.txt，嘗試找 company_profile.json (舊版相容)
    if not local_company:
        local_company = read_local_file("company_profile.json")

    # 將讀到的資料「灌」進去 Agent
    if hasattr(agent, "set_context"):
        # 如果檔案不存在，傳入預設提示文字
        r_data = local_resume if local_resume else "（測試模式：未提供履歷）"
        c_data = local_company if local_company else "（測試模式：未提供公司資料）"
        
        agent.set_context(r_data, c_data)
        print(f"✅ 已載入 Context: 履歷({len(r_data)}字), 公司({len(c_data)}字)")
    
    # ⚠️ 重要：資料注入後，必須重建 System Prompt
    if hasattr(agent, "build_system_messages"):
        agent.messages = agent.build_system_messages()
        # print("🔧 System Prompt 已更新")

    # ==========================================

    # 開場
    print("\n⏳ AI 正在思考開場白...")
    reply = agent.start()
    
    if not reply:
        print("❌ 無法啟動面試 (請檢查 API Key 或網路)")
        return

    print(f"🤖 {name}: {reply}")

    while True:
        try:
            user_in = input("\n👤 你: ").strip()
            
            # 1. 使用者手動結束
            if user_in.lower() in ['exit', '結束', '停止', 'bye']:
                print("--- 結束面試 ---")
                break
            
            if not user_in:
                continue

            ai_reply = agent.chat(user_in)
            print(f"🤖 {name}: {ai_reply}")

            # 2. AI 自動結束判斷
            end_keywords = [
                "感謝您今天的時間", "感謝您的撥空", "祝您一切順利", 
                "今天的面談就到這邊", "期待後續", "再見"
            ]
            
            if any(keyword in ai_reply for keyword in end_keywords):
                print("\n(AI 示意面試結束)")
                break

        except KeyboardInterrupt:
            print("\n強制中斷")
            break

# 封裝爬蟲執行
def run_cli_crawler():
    company = input("請輸入公司名稱: ").strip()
    position = input("請輸入職位名稱 (預設: 軟體工程師): ").strip()
    if not position:
        position = "軟體工程師"
    
    print(f"\n🚀 正在啟動爬蟲搜尋: {company} / {position}...")
    try:
        result = asyncio.run(run_crawler(company, position))
        
        if "error" in result:
            print(f"❌ 爬蟲失敗: {result['error']}")
        else:
            print("\n✅ 爬蟲完成！")
            summary = result.get("summary", "無摘要")
            print("-" * 30)
            print(summary[:500] + "..." if len(summary) > 500 else summary)
            print("-" * 30)
            
            # 順便存成 company.txt 方便等等測試用
            save = input("是否將此結果存為 company.txt 以供測試？(y/n): ").lower()
            if save == 'y':
                with open("company.txt", "w", encoding="utf-8") as f:
                    f.write(summary)
                print("💾 已儲存至 company.txt")
            
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

def main():
    while True:
        print("\n" + "="*30)
        print("   AI 面試模擬系統 - CLI 本地測試版")
        print("="*30)
        print("0. 🔍 [準備] 爬蟲並建立 company.txt")
        print("-" * 20)
        print("1. [面試] 電訪 (JAYDEN)")
        print("2. [分析] 電訪回饋報告")
        print("-" * 20)
        print("3. [面試] 白板題 (Alex)")
        print("4. [分析] 白板回饋報告")
        print("-" * 20)
        print("5. [面試] 主管 (Sarah)")
        print("6. [分析] 主管回饋報告")
        print("-" * 20)
        print("7. [面試] HR (Emily)")
        print("8. [分析] HR 回饋報告")
        print("-" * 20)
        print("9. 👑 [整體] 綜合評估報告")
        print("-" * 20)
        print("00. 離開")
        
        choice = input("\n請選擇功能: ").strip()

        if choice == '0':
            run_cli_crawler()
        elif choice == '1':
            run_interview_session(TelephoneInterviewer, "電訪")
        elif choice == '2':
            if hasattr(analyze_telephone, 'run'): analyze_telephone.run()
            else: print("此模組無 run() 方法")
        elif choice == '3':
            run_interview_session(WhiteboardInterviewer, "白板題")
        elif choice == '4':
            if hasattr(analyze_whiteboard, 'run'): analyze_whiteboard.run()
        elif choice == '5':
            run_interview_session(ManagerInterviewer, "主管面試")
        elif choice == '6':
            if hasattr(analyze_manager, 'run'): analyze_manager.run()
        elif choice == '7':
            run_interview_session(HRInterviewer, "HR 面試")
        elif choice == '8':
            if hasattr(analyze_hr, 'run'): analyze_hr.run()
        elif choice == '9':
            if hasattr(analyze_overall, 'run'): analyze_overall.run()
        elif choice == '00':
            sys.exit()
        else:
            print("無效選項")

if __name__ == "__main__":
    main()