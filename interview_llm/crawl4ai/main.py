import asyncio
import json
import sys
from pathlib import Path

# 匯入我們剛寫好的模組
import db_manager
import interview_llm.crawler as crawler

# 設定路徑
PARENT_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = PARENT_DIR / "company_input.json"

async def main():
    print("="*60)
    print("🤖 智慧面試準備系統 (資料庫版) - 啟動")
    print("="*60)

    # 1. 初始化資料庫
    db_manager.init_db()

    # 2. 同步檢查：如果 txt 檔案被刪了，資料庫也要刪掉紀錄
    print("\n🔄 正在檢查資料庫與檔案同步狀態...")
    db_manager.sync_database_with_files()

    # 3. 讀取輸入清單
    if not INPUT_FILE.exists():
        print(f"❌ 找不到輸入檔：{INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        targets = json.load(f)

    print(f"\n📋 讀取到 {len(targets)} 個待處理項目\n")

    # 4. 逐一處理
    for idx, item in enumerate(targets, 1):
        input_company = item["company"]
        input_position = item["position"]
        platform = item.get("platform", "104")

        print(f"[{idx}/{len(targets)}] 檢查：{input_company} - {input_position}")

        # --- 步驟 A: 檢查資料庫 ---
        exists, file_path, real_name = db_manager.check_job_exists(input_company, input_position)
        
        if exists:
            print(f"   ✨ 資料庫已有紀錄 (公司: {real_name})")
            print(f"   📂 檔案位置：{file_path}")
            print("   ⏩ 跳過爬蟲\n")
            continue
        
        # --- 步驟 B: 資料庫沒有 -> 呼叫爬蟲 ---
        print("   ⚠️ 資料庫無紀錄，啟動爬蟲...")
        
        success, real_company, real_position, new_file_path = await crawler.run_single_crawl(
            input_company, 
            input_position, 
            platform
        )

        # --- 步驟 C: 爬蟲成功 -> 更新資料庫 ---
        if success:
            db_manager.add_job_record(
                input_company, 
                input_position, 
                real_company,  # 這是網站上真實的公司名
                real_position, # 這是網站上真實的職稱
                new_file_path
            )
        else:
            print("   ❌ 爬蟲任務失敗，跳過資料庫寫入")
        
        print("-" * 40 + "\n")

    print("🎉 所有作業完成！")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 使用者中斷作業")