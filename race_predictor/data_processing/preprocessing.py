import pandas as pd
from utils.logger import logger

def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """清洗和格式化数据"""
    if df.empty:
        logger.warning("输入数据为空，返回空 DataFrame。")
        return df
    
    # 转换完成时间为秒数
    df["完成時間"] = pd.to_timedelta(df["完成時間"], errors="coerce").dt.total_seconds()
    
    # 处理数值字段
    df["獨贏賠率"] = pd.to_numeric(df["獨贏賠率"], errors="coerce")
    df["實際負磅"] = pd.to_numeric(df["實際負磅"], errors="coerce")
    df["排位體重"] = pd.to_numeric(df["排位體重"], errors="coerce")
    df["檔位"] = pd.to_numeric(df["檔位"], errors="coerce")
    
    # 将“名次”转为是否第一的标签
    df["是否第一"] = (df["名次"] == "1").astype(int)
    
    # 处理“沿途走位”，预期格式为 "1-2-3"
    def parse_positions(x):
        if pd.notna(x):
            try:
                # 处理连字符分隔的位置序列
                return [int(i) for i in x.split('-')]
            except (ValueError, AttributeError) as e:
                logger.debug(f"沿途走位数据异常：{x}，错误：{e}，返回空列表")
                return []
        return []
    
    df["沿途走位"] = df["沿途走位"].apply(parse_positions)
    df["平均走位"] = df["沿途走位"].apply(lambda x: sum(x) / len(x) if x else 0)
    
    logger.info("数据预处理完成。")
    return df