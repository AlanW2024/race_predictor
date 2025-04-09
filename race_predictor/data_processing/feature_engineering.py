import pandas as pd
# 使用絕對導入
from utils.logger import logger

def calculate_recent_performance(df: pd.DataFrame, group_col: str, target_col: str, window: int = 5) -> pd.Series:
    """计算近期表现特征"""
    return df.groupby(group_col)[target_col].transform(
        lambda x: x.shift(1).rolling(window, min_periods=1).mean()
    )

def calculate_distance_stats(df: pd.DataFrame, group_col: str, distance_col: str) -> pd.Series:
    """计算特定距离赛事表现"""
    return df.groupby([group_col, distance_col])['是否第一'].transform(
        lambda x: x.shift(1).expanding().mean()
    )

def add_historical_features(df: pd.DataFrame) -> pd.DataFrame:
    """添加历史数据特征"""
    if df.empty:
        logger.warning("输入数据为空，返回空 DataFrame。")
        return df

    # 确保数据已按日期和场次排序 
    df = df.sort_values(by=['日期', '場次']).reset_index(drop=True)

    # 基础历史特征
    df['马匹参赛次数'] = df.groupby('馬匹編號').cumcount()
    df['马匹胜率'] = df.groupby('馬匹編號')['是否第一'].transform(lambda x: x.shift(1).expanding().mean())
    df['平均完成时间'] = df.groupby('馬匹編號')['完成時間'].transform(lambda x: x.shift(1).expanding().mean())
    df['平均赔率'] = df.groupby('馬匹編號')['獨贏賠率'].transform(lambda x: x.shift(1).expanding().mean())
    
    # 新增特征
    df['马匹近期表现'] = calculate_recent_performance(df, '馬匹編號', '名次')
    df['骑师距离胜率'] = calculate_distance_stats(df, '騎師', '距離')
    df['练马师距离胜率'] = calculate_distance_stats(df, '練馬師', '距離')

    # 骑师历史表现
    df['骑师参赛次数'] = df.groupby('騎師').cumcount()
    df['骑师胜率'] = df.groupby('騎師')['是否第一'].transform(lambda x: x.shift(1).expanding().mean())

    # 练马师历史表现
    df['练马师参赛次数'] = df.groupby('練馬師').cumcount()
    df['练马师胜率'] = df.groupby('練馬師')['是否第一'].transform(lambda x: x.shift(1).expanding().mean())

    # 填充首次出现（shift(1) 导致第一行为 NaN）以及没有历史记录的情况
    # 对于胜率，首次参赛填充 0
    df["马匹胜率"] = df["马匹胜率"].fillna(0)
    df["骑师胜率"] = df["骑师胜率"].fillna(0)
    df["练马师胜率"] = df["练马师胜率"].fillna(0)
    
    # 对于平均完成时间和赔率，可以用全局平均值或中位数填充，或者保持 NaN 让模型处理（取决于模型）
    # 这里我们先用 0 填充，表示无历史记录，后续模型训练时可能需要进一步处理或选择不同填充策略
    df["平均完成时间"] = df["平均完成时间"].fillna(df["平均完成时间"].median()) # 使用中位数填充 NaN
    df["平均赔率"] = df["平均赔率"].fillna(df["平均赔率"].median()) # 使用中位数填充 NaN
    
    # 删除辅助列（如果不需要）
    # df = df.drop(columns=['马匹参赛次数', '骑师参赛次数', '练马师参赛次数'])

    logger.info("马匹、骑师、练马师历史特征添加完成 (使用 expanding window)。")
    return df
