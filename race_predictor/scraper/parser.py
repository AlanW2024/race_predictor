import re
from typing import Dict, List
from bs4 import BeautifulSoup
from utils.logger import logger

def parse_basic_info(soup: BeautifulSoup) -> Dict[str, str]:
    """解析赛事实体基本信息"""
    basic_info = {
        "日期": "", "馬場": "", "場次": "", "班次": "", "距離": "",
        "賽道": "", "場地狀況": "", "獎金": "", "完成時間": ""
    }
    
    date_venue_span = soup.select_one("span.f_fl.f_fs13")
    if date_venue_span:
        text = date_venue_span.get_text(strip=True)
        match = re.search(r'賽事日期[:：]\s*([\d/]+)\s*(\S+)', text)
        if match:
            basic_info["日期"] = match.group(1)
            basic_info["馬場"] = match.group(2)
    
    race_tab = soup.find("div", {"class": "race_tab"})
    if race_tab:
        info_text = race_tab.get_text(" ", strip=True)
        race_no_match = re.search(r'第\s*(\d+)\s*場', info_text)
        if race_no_match:
            basic_info["場次"] = race_no_match.group(1)
        
        class_match_zh = re.search(r'第\s*([一二三四五六七八九十]+)\s*班', info_text)
        if class_match_zh:
            basic_info["班次"] = f"第{class_match_zh.group(1)}班"
        else:
            class_match_en = re.search(r'Class\s*(\d+)', info_text, re.IGNORECASE)
            if class_match_en:
                basic_info["班次"] = f"Class {class_match_en.group(1)}"
        
        distance_match = re.search(r'(\d+)\s*米', info_text)
        if distance_match:
            basic_info["距離"] = distance_match.group(1) + "米"
        
        track_match = re.search(r'賽道\s*:\s*([^0-9]+)', info_text)
        if track_match:
            basic_info["賽道"] = track_match.group(1).strip()
        
        condition_match = re.search(r'場地狀況\s*[:：]\s*([^賽]+)', info_text)
        if condition_match:
            basic_info["場地狀況"] = condition_match.group(1).strip()
        
        prize_match = re.search(r'HK\$\s*([\d,]+)', info_text)
        if prize_match:
            basic_info["獎金"] = "HK$ " + prize_match.group(1)
        
        time_match = re.search(r'時間\s*[:：]\s*\(([\d:.]+)\)', info_text)
        if time_match:
            basic_info["完成時間"] = time_match.group(1)
    
    return basic_info

def parse_results(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """解析赛果表格数据"""
    results = []
    results_table = soup.find("table", {"class": "table_bd"})
    if not results_table:
        logger.warning("未找到赛果数据表格。")
        return results
    
    headers = ["名次", "馬號", "馬名", "騎師", "練馬師", "獨贏賠率", "實際負磅", "排位體重", "檔位", "頭馬距離", "沿途走位", "完成時間"]
    rows = results_table.find_all("tr")[1:]
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 6:
            continue
        row_data = {}
        for i, col in enumerate(cols):
            if i >= len(headers):
                break
            if headers[i] == "馬名":
                text = col.get_text(strip=True)
                code = ""
                m = re.search(r'\(([A-Z]\d+)\)', text)
                if m:
                    code = m.group(1)
                    text = re.sub(r'\s*\([A-Z]\d+\)', '', text).strip()
                row_data["馬名"] = text
                row_data["馬匹編號"] = code
            else:
                row_data[headers[i]] = col.get_text(strip=True)
        if row_data.get("名次") and row_data.get("馬名"):
            logger.debug(f"解析行数据：{row_data}")
            results.append(row_data)
        else:
            logger.warning(f"跳过数据不完整的记录：{row_data}")
    return results