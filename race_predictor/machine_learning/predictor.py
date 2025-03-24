import pickle
import pandas as pd
from utils.logger import logger

def predict_winner(race_data: pd.DataFrame, model=None) -> str:
    """预测单场比赛的第一名"""
    if model is None:
        try:
            with open("models/rf_model.pkl", "rb") as f:
                model = pickle.load(f)
        except FileNotFoundError:
            logger.error("未找到模型文件，请先训练模型。")
            return ""
    
    features = ["實際負磅", "排位體重", "檔位", "平均走位", "獨贏賠率"]
    X_new = race_data[features].fillna(0)
    probs = model.predict_proba(X_new)[:, 1]
    race_data["第一名概率"] = probs
    winner = race_data.loc[probs.argmax(), "馬名"]
    logger.info(f"预测结果 - 第一名: {winner} (概率: {max(probs):.4f})")
    return winner