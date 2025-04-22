import re
from typing import Dict, List, Optional, Union # 导入 Optional 和 Union
from bs4 import BeautifulSoup
# 使用絕對導入
from utils.logger import logger
import pandas as pd # 需要 pandas 来处理 NA 值

def time_string_to_seconds(time_str: str) -> Optional[float]:
    """将 m:ss.ff 或 ss.ff 格式的时间字符串转换为总秒数"""
    if pd.isna(time_str) or not isinstance(time_str, str):
        return None
    try:
        if ':' in time_str:
            parts = time_str.split(':')
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        else:
            # 假设是 ss.ff 格式
            return float(time_str)
    except ValueError:
        logger.warning(f"无法解析时间字符串: '{time_str}'")
        return None

def parse_basic_info(soup: BeautifulSoup) -> Dict[str, Union[str, float, None]]:
    """解析賽事基本資訊：日期、馬場、場次、班次、距離、賽道、場地狀況、獎金、完成時間、累積時間（秒數）"""
    basic_info: Dict[str, Union[str, float, None]] = { # 明确类型
        "日期": "", "馬場": "", "場次": "", "班次": "",
        "距離": "", "賽道": "", "場地狀況": "",
        "獎金": "", "全場時間_秒": None, # 存储秒数
        "累積時間1_秒": None, "累積時間2_秒": None, "累積時間3_秒": None, "累積時間4_秒": None, # 存储秒数
        "分段時間1_秒": None, "分段時間2_秒": None, "分段時間3_秒": None, "分段時間4_秒": None, # 存储秒数
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
            
                    # ⏱ 分段時間 - 提取并转换为秒数
        segment_times_match = re.search(r'分段時間\s*[:：]?\s*((?:\d{1,3}\.\d{2}\s*){3})', info_text)
        if segment_times_match:
            segments_str = segment_times_match.group(1).strip().split()
            for i, seg_str in enumerate(segments_str, 1): # 只循环三次
                seg_seconds = time_string_to_seconds(seg_str) # 转换为秒数
                basic_info[f"分段時間{i}_秒"] = seg_seconds # 存储秒数

        # ⏱ 累積時間（括號內），转换为秒数存储
        accum_times_str = re.findall(r'\((\d{1,2}:\d{2}\.\d{2}|\d{1,3}\.\d{2})\)', info_text)
        for i, acc_str in enumerate(accum_times_str[:4], 1): # 最多取4个
            seconds = time_string_to_seconds(acc_str)
            basic_info[f"累積時間{i}_秒"] = seconds # 存储秒数

        # 提取全场完成时间并转换为秒数 (需要找到正确的元素)
        # 假设全场时间在赛果表格的第一行最后一列
        results_table = soup.find("table", {"class": "table_bd"})
        finish_time_seconds = None
        if results_table:
            first_row_cols = results_table.select("tbody tr:first-child td")
            if len(first_row_cols) > 10: # 确保有足够列
                 finish_time_str = first_row_cols[10].get_text(strip=True) # 第11列是完成时间
                 finish_time_seconds = time_string_to_seconds(finish_time_str)
                 basic_info["全場時間_秒"] = finish_time_seconds

        # 计算分段时间4（秒数）
        if finish_time_seconds is not None and basic_info["累積時間3_秒"] is not None:
             # 确保两者都是有效的浮点数
             if isinstance(finish_time_seconds, float) and isinstance(basic_info["累積時間3_秒"], float):
                 segment4_seconds = round(finish_time_seconds - basic_info["累積時間3_秒"], 2)
                 basic_info["分段時間4_秒"] = segment4_seconds
             else:
                 logger.warning("无法计算分段时间4，因为全场时间或累积时间3无效。")
        elif finish_time_seconds is None: # 修正缩进
             logger.warning("未找到全场时间，无法计算分段时间4。")
        elif basic_info["累積時間3_秒"] is None: # 修正缩进
             logger.warning("未找到累积时间3，无法计算分段时间4。")

    # 注意：下面这段提取 "累積時間", "分段時間", "200米時間" 的逻辑与上面提取括号内时间的方式可能冲突或重复
    # 并且它们被合并成单一字符串，不利于后续处理。
    # 建议审视是否还需要这部分，或者修改其逻辑以适应新的秒数存储方式。
    # 暂时注释掉这部分，以避免覆盖上面计算好的秒数。
    # data = {
    #     "累積時間": [],
    #     "分段時間": [],
    #     "200米時間": []
    # }
    # all_times = soup.find_all("td", {"class": "f_tac"})
    # for td in all_times:
    #     text = td.get_text(strip=True)
    #     # ... (原有的提取逻辑) ...
    # basic_info["累積時間"] = "|".join(data["累積時間"]) # 这会覆盖上面计算的秒数
    # basic_info["分段時間"] = "|".join(data["分段時間"])
    # basic_info["200米時間"] = "|".join(data["200米時間"])

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
