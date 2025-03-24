import os
import pickle
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from utils.logger import logger

def train_model(df: pd.DataFrame) -> RandomForestClassifier:
    """训练随机森林模型并保存"""
    features = ["實際負磅", "排位體重", "檔位", "平均走位", "獨贏賠率"]
    X = df[features].fillna(0)
    y = df["是否第一"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    logger.info(f"模型训练完成，测试集准确率: {accuracy:.4f}")
    
    os.makedirs("models", exist_ok=True)
    with open("models/rf_model.pkl", "wb") as f:
        pickle.dump(model, f)
    logger.info("模型已保存到 models/rf_model.pkl")
    return model