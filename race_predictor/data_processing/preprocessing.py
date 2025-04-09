import pandas as pd
import re
# 使用絕對導入
from utils.logger import logger

def fix_time_format(t):
    if pd.isna(t):
        return None
    # 如果是 mm:ss.ff 格式，加前綴變成 0:mm:ss.ff
    if re.match(r"^\d+:\d{2}\.\d{2}$", t):
        return "0:" + t
    return t if re.match(r"^\d+:\d{2}:\d{2}\.\d{2}$", t) else None

def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("数据预处理开始。")
    
    # 首先按日期和场次排序，确保历史数据顺序正确
    if '日期' in df.columns and '場次' in df.columns:
        df = df.sort_values(by=['日期', '場次']).reset_index(drop=True)

    # 去除空值或缺失列（保留必要的历史数据列）
    required_cols = ["馬名", "場次", "排位體重", "檔位", "獨贏賠率", "名次", "完成時間"]
    df = df.dropna(subset=required_cols)

    # 清洗數值類欄位
    numeric_columns = ["實際負磅", "排位體重", "檔位", "獨贏賠率"]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 是否第一名
    df["是否第一"] = (df["名次"].astype(str).str.strip() == "1").astype(int)

    # 定義更健壯的平均走位計算函數
    def calculate_average_position(pos_str):
        try:
            positions = re.findall(r"\d+", str(pos_str))
            if not positions:
                return None # 返回 None 如果沒有找到數字
            # 將找到的數字轉換為整數，求和後除以數量
            return sum(map(int, positions)) / len(positions)
        except Exception as e:
            logger.warning(f"處理沿途走位時出錯: '{pos_str}', 錯誤: {e}. 返回 None.")
            return None # 出錯時返回 None

    # 應用新的計算函數
    df["平均走位"] = df["沿途走位"].apply(calculate_average_position)
    
    # 在處理完成時間之前，先處理平均走位的缺失值 (例如，用中位數填充)
    # 注意：這裡填充的是新計算出的可能為 None 的值，而不是原始的異常大值
    avg_pos_median = df["平均走位"].median()
    # 使用 df.loc 來避免 SettingWithCopyWarning
    df.loc[df["平均走位"].isna(), "平均走位"] = avg_pos_median
    # df["平均走位"].fillna(avg_pos_median, inplace=True) # 原寫法，可能觸發警告
    if pd.notna(avg_pos_median):
        logger.info(f"使用中位數 {avg_pos_median:.2f} 填充了 '平均走位' 的缺失值。")
    else:
        logger.warning("'平均走位' 的中位數無法計算 (可能所有值都無效)，未進行填充。")


    # 處理完成時間欄位：補 0: 前綴 → timedelta → 秒數
    df["完成時間"] = df["完成時間"].apply(fix_time_format)
    df["完成時間"] = pd.to_timedelta(df["完成時間"], errors="coerce").dt.total_seconds()

    # 排除沒有完成時間或平均走位的數據
    df = df.dropna(subset=["完成時間", "平均走位"])

    # 計算全場時間（第一名馬匹的完成時間）
    df["全場時間"] = df.groupby("場次")["完成時間"].transform(
        lambda x: x[x.index.isin(df[df["是否第一"] == 1].index)].iloc[0] if any(df["是否第一"] == 1) else None
    )

    # 排除沒有全場時間的場次
    df = df.dropna(subset=["全場時間"])

    logger.info("数据预处理完成。")
    return df
