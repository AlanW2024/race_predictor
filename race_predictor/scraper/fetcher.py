import re
from typing import List, Optional, Union, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup
# 使用簡單相對導入
from utils.session import create_session
from utils.logger import logger
from scraper.parser import parse_basic_info, parse_results

def fetch_page(session: requests.Session, url: str, timeout: int = 15) -> Optional[str]:
    logger.info(f"请求 URL: {url}")
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"请求错误：{e}")
    return None

def fetch_race_schedule(session: requests.Session, num_days: int = 3) -> List[Tuple[str, str]]:
    """
    從 HKJC 的賽馬排期頁面，抓取最近賽馬日期與場地 (簡化示例).
    若失敗就回傳預設的三天賽期。
    """
    url = "https://racing.hkjc.com/racing/information/Chinese/Racing/Racecard.aspx"
    html = fetch_page(session, url)
    if not html:
        return [("2025/03/23", "ST"), ("2025/03/26", "ST"), ("2025/03/30", "ST")]

    soup = BeautifulSoup(html, "html.parser")
    divs = soup.select("div.racecard_date")
    date_venue_list = []
    for div in divs:
        text = div.get_text(strip=True)
        m = re.search(r'(\d{4}/\d{2}/\d{2})', text)
        if m:
            date_str = m.group(1)
            # 判斷場地
            if "沙田" in text:
                date_venue_list.append((date_str, "ST"))
            elif "跑馬地" in text:
                date_venue_list.append((date_str, "HV"))

    if not date_venue_list:
        return [("2025/02/26", "HV"), ("2025/03/02", "ST"), ("2025/03/05", "HV")]

    return date_venue_list[:num_days]

def scrape_single_race(session: requests.Session, date_str: str, venue: str, race_no: int) -> Dict[str, Union[Dict[str, str], List[Dict[str, str]]]]:
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
    def scrape_race(race_no):
        return scrape_single_race(session, date_str, venue, race_no)
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(scrape_race, range(1, max_races + 1)))
    return [r for r in results if r]
