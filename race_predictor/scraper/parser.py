import re
from typing import Dict, List
from bs4 import BeautifulSoup
# 使用絕對導入
from utils.logger import logger

def parse_basic_info(soup: BeautifulSoup) -> Dict[str, str]:
    """解析賽事基本資訊：日期、馬場、場次、班次、距離、賽道、場地狀況、獎金、完成時間"""
    basic_info = {
        "日期": "", "馬場": "", "場次": "", "班次": "",
        "距離": "", "賽道": "", "場地狀況": "",
        "獎金": "", "全場時間": "",
        "累積時間": "", "分段時間": "", "200米時間": ""
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

        class_match_zh = re.search(r'第?\s*([一二三四五六七八九十\d]+)\s*班', info_text)
        if class_match_zh:
            group_val = class_match_zh.group(1)
            basic_info["班次"] = f"第{group_val}班"
        else:
            class_match_en = re.search(r'Class\s*(\d+)', info_text, re.IGNORECASE)
            if class_match_en:
                basic_info["班次"] = f"Class {class_match_en.group(1)}"
            else:
                special_class_match = re.search(r'(四歲|三級賽|二級賽|一級賽|讓賽|錦標)', info_text)
                if special_class_match:
                    basic_info["班次"] = special_class_match.group(1)

        distance_match = re.search(r'(\d+)\s*米', info_text)
        if distance_match:
            basic_info["距離"] = distance_match.group(1) + "米"

        track_match = re.search(r'賽道\s*[:：]\s*([^\s]+\s*-\s*\"[^\"]+\"\s*賽道)', info_text)
        if track_match:
            basic_info["賽道"] = track_match.group(1).replace("HK$", "").strip()

        condition_match = re.search(r'場地狀況\s*[:：]\s*([^\s]+)', info_text)
        if condition_match:
            basic_info["場地狀況"] = condition_match.group(1).strip()

        prize_match = re.search(r'HK\$\s*([\d,]+)', info_text)
        if prize_match:
            basic_info["獎金"] = "HK$ " + prize_match.group(1)
            
                    # ⏱ 分段時間
        segment_times = re.findall(r'分段時間\s*[:：]?\s*((?:\d{1,3}\.\d{2}\s*){4})', info_text)
        if segment_times:
            segments = segment_times[0].strip().split()
            for i, seg in enumerate(segments, 1):
                basic_info[f"分段時間{i}"] = seg

        # ⏱ 累積時間（括號內）
        accum_times = re.findall(r'\((\d{1,2}:\d{2}\.\d{2}|\d{1,3}\.\d{2})\)', info_text)
        for i, acc in enumerate(accum_times[:4], 1):
            basic_info[f"累積時間{i}"] = acc


    # 額外抓取分段時間相關
    data = {
        "累積時間": [],
        "分段時間": [],
        "200米時間": []
    }

    all_times = soup.find_all("td", {"class": "f_tac"})
    for td in all_times:
        text = td.get_text(strip=True)
        if re.match(r"^\(?\d{1,2}:\d{2}\.\d{2}\)?$", text):
            data["累積時間"].append(text.replace("(", "").replace(")", ""))
        elif re.match(r"^\d{2}\.\d{2}$", text):
            num = float(text)
            if num > 20:
                data["分段時間"].append(text)
            else:
                data["200米時間"].append(text)

    basic_info["累積時間"] = "|".join(data["累積時間"])
    basic_info["分段時間"] = "|".join(data["分段時間"])
    basic_info["200米時間"] = "|".join(data["200米時間"])

    return basic_info

def parse_results(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """解析賽果表格，確保每匹馬的完成時間正確抓取。"""
    results = []
    results_table = soup.find("table", {"class": "table_bd"})
    if not results_table:
        logger.warning("未找到賽果數據表格。")
        return results

    headers = [
        "名次", "馬號", "馬名", "騎師", "練馬師",
        "實際負磅", "排位體重", "檔位", "頭馬距離",
        "沿途走位", "完成時間", "獨贏賠率"
    ]

    rows = results_table.find_all("tr")
    if len(rows) <= 1:
        return results

    data_rows = rows[1:]
    for row_idx, row in enumerate(data_rows):
        cols = row.find_all("td")
        if len(cols) < len(headers):
            logger.debug(f"第 {row_idx} 行欄位不足，跳過。")
            continue

        row_data = {}
        for i, col in enumerate(cols[:len(headers)]):
            if headers[i] == "沿途走位":
                position_texts = [t.strip() for t in col.find_all(string=True, recursive=True) if t.strip().isdigit()]
                text = " ".join(position_texts)
            else:
                text = col.get_text(strip=True)

            if headers[i] == "馬名":
                code = ""
                m = re.search(r'\(([A-Z]\d+)\)', text)
                if m:
                    code = m.group(1)
                    text = re.sub(r'\s*\([A-Z]\d+\)', '', text).strip()
                row_data["馬名"] = text
                row_data["馬匹編號"] = code
            else:
                row_data[headers[i]] = text

        if row_data.get("名次") and row_data.get("馬名"):
            results.append(row_data)
        else:
            logger.debug(f"跳過不完整資料: {row_data}")

    return results
