import pandas as pd
from utils.logger import logger

def add_historical_features(df: pd.DataFrame) -> pd.DataFrame:
    """添加历史数据特征"""
    if df.empty:
        logger.warning("输入数据为空，返回空 DataFrame。")
        return df
    
    # 计算马匹历史表现
    horse_stats = df.groupby("馬匹編號").agg({
        "是否第一": "mean",
        "完成時間": "mean",
        "獨贏賠率": "mean"
    }).rename(columns={"是否第一": "马匹胜率", "完成時間": "平均完成时间", "獨贏賠率": "平均赔率"})
    
    df = df.merge(horse_stats, on="馬匹編號", how="left")
    logger.info("历史特征添加完成。")
    return df