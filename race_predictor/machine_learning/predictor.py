import pickle
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import pickle
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from utils.logger import logger
import numpy as np # Import numpy

def predict_winner(race: pd.DataFrame, model) -> pd.DataFrame:
    """预测比赛结果，返回包含预测概率的DataFrame"""
    features = [
        "實際負磅", "排位體重", "檔位", "平均走位", "獨贏賠率",
        "马匹胜率", "平均完成时间", "平均赔率", "骑师胜率", "练马师胜率",
        "马匹近期表现", "骑师距离胜率", "练马师距离胜率"
    ]
    logger.debug(f"模型預期特徵: {features}")
    logger.debug(f"輸入 DataFrame 欄位: {race.columns.tolist()}")
    
    missing_features = [f for f in features if f not in race.columns]
    
    # Check for missing features before proceeding
    if missing_features:
        # Attempt to fill missing historical features if they were added in feature engineering
        # This handles cases where a horse/jockey/trainer might be new in the prediction set
        # but had stats calculated during training. We assume 0 for win rates, mean for others.
        fill_values = {}
        if "马匹胜率" in missing_features: fill_values["马匹胜率"] = 0
        if "平均完成时间" in missing_features: fill_values["平均完成时间"] = model.feature_importances_[features.index("平均完成时间")] # Placeholder, ideally use training mean
        if "平均赔率" in missing_features: fill_values["平均赔率"] = model.feature_importances_[features.index("平均赔率")] # Placeholder, ideally use training mean
        if "骑师胜率" in missing_features: fill_values["骑师胜率"] = 0
        if "练马师胜率" in missing_features: fill_values["练马师胜率"] = 0
        
        logger.warning(f"預測數據缺少特徵: {missing_features}. 嘗試填充: {fill_values}")
        for feature, value in fill_values.items():
             if feature in missing_features:
                 race[feature] = value # Add the column with default value
                 missing_features.remove(feature) # Remove from list if handled

        # If features are still missing after attempting to fill, raise error
        if missing_features:
             raise ValueError(f"無法處理的缺失特徵: {missing_features}")

    X_new = race[features].copy() # Use .copy()
    
    # Handle potential infinite values and NaNs in prediction data as well
    X_new.replace([np.inf, -np.inf], np.nan, inplace=True)
    X_new.fillna(0, inplace=True) # Fill NaNs with 0, consistent with training

    # Ensure column order matches the order during training (important for some models)
    # Although RandomForest is generally robust to order, it's good practice.
    # We assume the 'model' object implicitly knows the feature order it was trained on,
    # but explicitly reordering based on the 'features' list ensures consistency.
    X_new = X_new[features] 
    
    probs = model.predict_proba(X_new)[:, 1]
    # Use .loc to avoid SettingWithCopyWarning
    race.loc[:, "预测概率"] = probs 
    logger.info(f"預測概率已計算。")
    # 返回包含預測概率的 DataFrame
    race_with_probs = race.sort_values("预测概率", ascending=False).reset_index(drop=True)
    logger.debug(f"概率詳情:\n{race_with_probs[['馬名', '预测概率']]}")
    # winner = race.loc[race["预测概率"].idxmax(), "馬名"] # 原來的返回方式
    return race_with_probs # 返回帶概率的 DataFrame
