import asyncio
import json
import os
import sys
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.async_configs import LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# 1. 讀取設定
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

if not os.getenv("OPENAI_API_KEY"):
    print("❌ [致命錯誤]：找不到 OPENAI_API_KEY")
    print("   請確認目錄下是否有 .env 檔案，且內容包含 OPENAI_API_KEY=sk-...")
    sys.exit(1)

# 資料結構定義
class JobAnalysisResult(BaseModel):
    company_name: str = Field(..., description="公司名稱")
    job_title: str = Field(..., description="職位名稱")
    markdown_report: str = Field(..., description="完整的職缺分析報告，包含技術規格、面試題庫等 Markdown 內容")

async def search_duckduckgo_and_get_url(crawler, company, position, platform):
    """
    第一階段：使用 DuckDuckGo 搜尋
    """
    if platform == "104":
        query = f"{company} {position} site:104.com.tw/job/"
        target_domain = "104.com.tw/job/"
    else:
        query = f"{company} {position} site:1111.com.tw/job/"
        target_domain = "1111.com.tw/job/"

    encoded_query = urllib.parse.quote(query)
    ddg_url = f"https://duckduckgo.com/?q={encoded_query}&t=h_&ia=web"
    
    print(f"   └── 🔎 正在 DuckDuckGo 搜尋: {query}")

    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_for="body", 
        delay_before_return_html=2.0,
        magic=True
    )
    
    result = await crawler.arun(url=ddg_url, config=config)
    
    if not result.success:
        print(f"   ❌ 搜尋請求失敗: {result.error_message}")
        return None

    soup = BeautifulSoup(result.html, 'html.parser')
    links = soup.select("a")
    
    for link in links:
        href = link.get('href')
        if href and target_domain in href:
            if "duckduckgo" not in href:
                clean_url = href.split('?')[0]
                print(f"   🎯 鎖定目標網址: {clean_url}")
                return clean_url

    print("   ⚠️ 警告：搜尋結果中找不到符合的職缺連結 (可能關鍵字太模糊或職缺已下架)")
    return None

async def analyze_job_detail(crawler, job_url):
    """
    第二階段：進入詳情頁進行 LLM 分析
    """
    print(f"   └── 🚀 正在載入職缺詳情頁，準備進行 AI 分析 (這可能需要 10-20 秒)...")

    llm_config = LLMConfig(
        provider="openai/gpt-4o-mini",
        api_token=os.getenv('OPENAI_API_KEY')
    )

    # === 你的 PROMPT 保持原樣 ===
    extraction_strategy = LLMExtractionStrategy(
        llm_config=llm_config,
        schema=JobAnalysisResult.model_json_schema(),
        instruction="""
    你是一位資深的「技術招募顧問」。
    請根據提供的職缺資料，整理出結構化的面試準備檔案。
    
    **重要指令**：
    請將所有分析結果整理成一篇完整的 Markdown 文章，並填入回傳 JSON 的 `markdown_report` 欄位中。
    
    Markdown 內容格式要求如下：

    # 1. 公司基本識別資料
    * **公司全名**：
    * **應徵職位**：
    * **產業類別**：
    * **公司地點**：
    * **管理責任**：
    * **出差外派**：
    * **上班時段**：
    * **休假制度**：
    * **薪水**：

    # 2. 技術規格分析 (⚠️ 重點)
    * **學歷要求**：
    * **語言條件**：
    * **核心程式語言**：[例如 Python, Java, C#, JavaScript 等]
    * **前端技術**：[例如 React, Vue, HTML/CSS]
    * **後端與資料庫**：[例如 Node.js, Spring Boot, MySQL, MongoDB]
    * **開發工具與環境**：[例如 Git, Linux, Docker, AWS]

    # 3. 職位職責
    * **主要工作內容**：
    * **專案類型推測**：

    # 4. 軟實力與文化
    * **人格特質**：
    * **福利亮點**：

    # 6. 其他重要資料
    * **上面結構化內容未提及但重要的資料**：

    # 5. 面試官教戰題庫
    * **建議白板題方向**：
    * **建議主管技術題**：
    * **建議HR訪問問題**：
        """
    )

    config = CrawlerRunConfig(
        extraction_strategy=extraction_strategy,
        cache_mode=CacheMode.BYPASS,
        wait_for="body", 
        delay_before_return_html=3.0,
        magic=True
    )

    result = await crawler.arun(url=job_url, config=config)

    if result.success:
        try:
            return json.loads(result.extracted_content)
        except:
            print("   ❌ AI 回傳資料解析錯誤 (JSON Format Error)")
            return None
    else:
        print(f"   ❌ 詳情頁爬取失敗: {result.error_message}")
        return None

async def main():
    print("\n" + "="*50)
    print("🤖 AI 求職面試準備助手 - 啟動中")
    print("⚠️  注意：程式執行期間會開啟 Chrome 視窗")
    print("⚠️  請勿手動關閉視窗，以免程式中斷！")
    print("="*50 + "\n")

    # 檢查輸入檔案
    input_file = 'company_input.json'
    if not os.path.exists(input_file):
        print(f"❌ 錯誤：找不到 {input_file}")
        print("   請先執行 create_data.py 建立資料檔。")
        return

    # 檢查 JSON 內容是否為空
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                raise ValueError("檔案內容為空")
            companies = json.loads(content)
    except Exception as e:
        print(f"❌ 錯誤：{input_file} 格式不正確或為空。詳細錯誤: {e}")
        return

    # 設定瀏覽器
    browser_cfg = BrowserConfig(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
        headless=False, 
        verbose=True
    )

    results_text = ""

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        for index, item in enumerate(companies, 1):
            print(f"\n🔄 [{index}/{len(companies)}] 正在處理：{item['company']} - {item['position']}")
            
            try:
                job_url = await search_duckduckgo_and_get_url(
                    crawler, 
                    item['company'], 
                    item['position'], 
                    item['platform']
                )

                if job_url:
                    extracted_data = await analyze_job_detail(crawler, job_url)
                    
                    if extracted_data:
                        info = extracted_data[0] if isinstance(extracted_data, list) else extracted_data
                        
                        report_content = info.get('markdown_report', '⚠️ 分析失敗：AI 未回傳有效報告')
                        
                        output_str = f"========================================\n"
                        output_str += f"分析對象：{item['company']} - {item['position']}\n"
                        output_str += f"來源網址：{job_url}\n"
                        output_str += f"========================================\n\n"
                        output_str += report_content
                        output_str += "\n\n" + ("-" * 50) + "\n\n"
                        
                        print(f"   ✅ 分析完成！已暫存結果。")
                        results_text += output_str
                    else:
                        print(f"   ⚠️ AI 分析失敗 (可能因網頁內容過少或被阻擋)")
                        results_text += f"=== {item['company']} ===\n(詳情頁分析失敗)\n\n"
                else:
                    results_text += f"=== {item['company']} ===\n(DuckDuckGo 搜尋無結果)\n\n"

            except Exception as e:
                print(f"   ❌ 系統發生未預期錯誤: {e}")

    # 寫入檔案
    output_file = 'company_profile.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(results_text)
    
    abs_path = os.path.abspath(output_file)
    print("\n" + "="*50)
    print("🎉 全部任務完成！")
    print(f"📂 結果已儲存至：{abs_path}")
    print("="*50 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ 使用者手動停止程式 (Ctrl+C)")