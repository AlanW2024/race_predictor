import os
import re
from typing import List, Optional, Union, Dict
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup
from utils.session import create_session
from utils.logger import logger
from scraper.parser import parse_basic_info, parse_results

def fetch_page(session: requests.Session, url: str, timeout: int = 15) -> Optional[str]:
    """根据指定 URL 获取网页 HTML 内容，并保存到本地"""
    try:
        logger.info(f"请求 URL: {url}")
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        html = response.text
        os.makedirs("raw_html", exist_ok=True)
        # 清洗 URL，生成合法文件名
        safe_filename = re.sub(r'[/:?&=]+', '_', url.split('/')[-1])  # 提取最后一段并替换非法字符
        file_path = f"raw_html/{safe_filename}.html"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html)
        return html
    except requests.RequestException as e:
        logger.error(f"请求错误：{e}")
    return None

# 以下函数保持不变
def scrape_single_race(session: requests.Session, date_str: str, venue: str, race_no: int) -> Dict[str, Union[Dict[str, str], List[Dict[str, str]]]]:
    """爬取单一场次的数据"""
    base_url = "https://racing.hkjc.com/racing/information/Chinese/Racing/LocalResults.aspx"
    target_url = f"{base_url}?RaceDate={date_str}&Racecourse={venue}&RaceNo={race_no}"
    
    html = fetch_page(session, target_url)
    if not html:
        return {}
    
    soup = BeautifulSoup(html, "html.parser")
    basic_info = parse_basic_info(soup)
    results_data = parse_results(soup)
    
    if not results_data:
        logger.info(f"{date_str} {venue} 第 {race_no} 场无赛果数据，跳过。")
        return {}
    
    logger.info(f"{date_str} {venue} 第 {race_no} 场 解析到 {len(results_data)} 条赛果数据。")
    return {"基本資訊": basic_info, "賽果": results_data}

def scrape_race_day_parallel(session: requests.Session, date_str: str, venue: str, max_races: int = 11) -> List[Dict]:
    """并行爬取一天的所有场次"""
    def scrape_race(race_no):
        return scrape_single_race(session, date_str, venue, race_no)
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(scrape_race, range(1, max_races + 1)))
    return [r for r in results if r]

def fetch_race_schedule(session: requests.Session, num_days: int = 3) -> List[tuple]:
    """动态获取最近的赛马日程（简化版，需根据实际页面调整）"""
    url = "https://racing.hkjc.com/racing/information/Chinese/Racing/Racecard.aspx"
    html = fetch_page(session, url)
    if not html:
        return [("2025/02/26", "HV"), ("2025/03/02", "ST"), ("2025/03/05", "ST")]  # 默认值
    
    soup = BeautifulSoup(html, "html.parser")
    race_dates = []
    for item in soup.select("div.racecard_date"):  # 示例选择器
        text = item.get_text(strip=True)
        date_match = re.search(r"(\d{4}/\d{2}/\d{2})", text)
        if date_match:
            date = date_match.group(1)
            venue = "ST" if "沙田" in text else "HV"
            race_dates.append((date, venue))
    return race_dates[:num_days] if race_dates else [("2025/02/26", "HV"), ("2025/03/02", "ST"), ("2025/03/05", "ST")]