import asyncio
import json
import urllib.parse
import re
import os
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.async_configs import LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from pydantic import BaseModel, Field
import importlib.util

# ================= 1. 設定與 API KEY =================
# 假設此檔案位於 project/interview_llm/crawler.py
# 我們要往上兩層找到根目錄的 api_config.py
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
API_CONFIG_PATH = ROOT_DIR / "api_config.py"

API_KEY = None
if API_CONFIG_PATH.exists():
    spec = importlib.util.spec_from_file_location("api_config", API_CONFIG_PATH)
    api_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api_config)
    API_KEY = getattr(api_config, "API_KEY", None)

if not API_KEY:
    print("⚠️ Warning: API_KEY not found in api_config.py")

# ================= 2. Schema 定義 =================
class JobAnalysisResult(BaseModel):
    company_name: str = Field(..., description="從網頁中提取的真實招聘公司名稱")
    job_title: str = Field(..., description="從網頁中提取的真實職位名稱")
    markdown_report: str = Field(..., description="分析後的 markdown 報告")

# ================= 3. 輔助函式 =================
def sanitize_filename(name):
    """移除檔案名稱中的非法字元"""
    if not name: return "unknown"
    return re.sub(r'[\\/*?:"<>|]', "", name).replace(" ", "_")

async def search_duckduckgo(crawler, company, position):
    """搜尋 DuckDuckGo 找 104/1111 連結"""
    print(f"   └── 🔎 Search: {company} {position}")
    # 優先找 104，也可以加入 1111
    query = f"{company} {position} (site:104.com.tw/job/ OR site:1111.com.tw/job/)"
    encoded = urllib.parse.quote(query)
    url = f"https://duckduckgo.com/?q={encoded}&t=h_&ia=web"
    
    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS, 
        wait_for="body", 
        delay_before_return_html=2.0
    )
    result = await crawler.arun(url=url, config=config)
    
    if not result.success: return None
    soup = BeautifulSoup(result.html, "html.parser")
    
    # 找尋最像職缺的連結
    for link in soup.select("a"):
        href = link.get("href")
        if href and ("104.com.tw/job/" in href or "1111.com.tw/job/" in href) and "duckduckgo" not in href:
            clean_url = href.split("?")[0]
            print(f"   🎯 Found URL: {clean_url}")
            return clean_url
    return None

async def analyze_page(crawler, url, hint_company, hint_position):
    """進入職缺頁面進行 AI 分析"""
    print(f"   └── 🚀 Analyzing: {url}")
    llm_config = LLMConfig(provider="openai/gpt-4o-mini", api_token=API_KEY)
    
    strategy = LLMExtractionStrategy(
        llm_config=llm_config,
        schema=JobAnalysisResult.model_json_schema(),
        instruction=f"""
    你現在要從求職網站的HTML中提取資訊。
    
    【重要目標】：
    使用者正在搜尋的公司是：「{hint_company}」
    使用者正在搜尋的職位是：「{hint_position}」
    
    請在網頁內容中尋找符合上述目標的「真實公司全名」與「真實職缺名稱」。
    
    【禁止事項】：
    1. company_name 絕對不能是 "104人力銀行"、"1111人力銀行" 或 "DuckDuckGo"。
    2. job_title 絕對不能是 "技術招募顧問" (那是你的角色，不是職缺)。
    
    【任務】：
    請根據網頁內容，將分析結果整理成 Markdown 報告放入 `markdown_report` 欄位。
    Markdown 內容需包含：
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
        cache_mode=CacheMode.BYPASS, 
        extraction_strategy=strategy, 
        wait_for="h1",
        delay_before_return_html=3.0
    )
    
    result = await crawler.arun(url=url, config=config)
    
    if result.success:
        try:
            data = json.loads(result.extracted_content)
            item = data[0] if isinstance(data, list) else data
            
            # 防呆：若 AI 抓錯，用 user 輸入的覆蓋
            bad_keywords = ["104", "1111", "人力銀行"]
            if any(k in item.get("company_name", "") for k in bad_keywords):
                item["company_name"] = hint_company
            
            return item
        except Exception as e:
            print(f"   ❌ JSON Parse Error: {e}")
            return None
    return None

# ================= 4. 核心對外函式 (給 API 用) =================
async def run_crawler(company_name: str, position: str = "軟體工程師"):
    """
    這是主要的 Entry Point。
    回傳 dict: { "summary": ..., "values": ..., "raw_data": ... }
    """
    print(f"🔄 Crawler started for {company_name}")
    
    browser_cfg = BrowserConfig(headless=True, verbose=False) # Server 上通常用 headless=True
    
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        # 1. 搜尋
        job_url = await search_duckduckgo(crawler, company_name, position)
        if not job_url:
            return {
                "error": "Job URL not found", 
                "company": company_name,
                "summary": "無法找到該公司的公開職缺資訊，將使用通用面試模式。"
            }

        # 2. 分析
        info = await analyze_page(crawler, job_url, company_name, position)
        if not info:
            return {
                "error": "Analysis failed",
                "company": company_name,
                "summary": "無法分析職缺頁面內容。"
            }

        # 3. 整理回傳資料 (配合 SessionContext 格式)
        # 我們把 markdown report 當作 context 的主要來源
        report = info.get("markdown_report", "")
        
        # (選用) 同時保留原本的存檔邏輯，作為備份
        save_backup_file(info, company_name, position, job_url)

        return {
            "source_url": job_url,
            "company": info.get("company_name", company_name),
            "position": info.get("job_title", position),
            "summary": report,  # 這裡的 summary 會被餵給 LLM
            "crawled_at": datetime.now().isoformat()
        }

def save_backup_file(info, company, position, url):
    """保留原本的存檔功能作為 Log"""
    try:
        output_dir = ROOT_DIR / "data" / "crawled_companies"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        safe_name = sanitize_filename(company)
        filename = f"{safe_name}_{timestamp}.txt"
        
        content = (
            f"URL: {url}\n"
            f"Company: {company}\n"
            f"Position: {position}\n"
            f"{'='*30}\n"
            f"{info.get('markdown_report', '')}"
        )
        
        with open(output_dir / filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"   📂 Backup saved: {filename}")
    except Exception as e:
        print(f"   ⚠️ Backup save failed: {e}")