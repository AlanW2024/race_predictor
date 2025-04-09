import os
import pickle
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score
from utils.logger import logger
import numpy as np

def train_xgboost(X_train, y_train):
    """训练XGBoost模型"""
    params = {
        'n_estimators': [100, 200],
        'max_depth': [3, 6, 9],
        'learning_rate': [0.01, 0.1]
    }
    xgb = XGBClassifier(random_state=42)
    grid = GridSearchCV(xgb, params, cv=5, n_jobs=-1, verbose=1)
    grid.fit(X_train, y_train)
    return grid.best_estimator_

def train_lightgbm(X_train, y_train):
    """训练LightGBM模型"""
    params = {
        'n_estimators': [100, 200],
        'max_depth': [3, 6, 9],
        'learning_rate': [0.01, 0.1]
    }
    lgbm = LGBMClassifier(random_state=42)
    grid = GridSearchCV(lgbm, params, cv=5, n_jobs=-1, verbose=1)
    grid.fit(X_train, y_train)
    return grid.best_estimator_

def train_logistic(X_train, y_train):
    """训练逻辑回归模型"""
    params = {
        'C': [0.1, 1, 10],
        'penalty': ['l1', 'l2']
    }
    lr = LogisticRegression(random_state=42, solver='liblinear')
    grid = GridSearchCV(lr, params, cv=5, n_jobs=-1, verbose=1)
    grid.fit(X_train, y_train)
    return grid.best_estimator_

def model_comparison(X_train, y_train, X_test, y_test):
    """比较不同模型性能"""
    models = {
        'RandomForest': RandomForestClassifier(random_state=42),
        'XGBoost': XGBClassifier(random_state=42),
        'LightGBM': LGBMClassifier(random_state=42),
        'LogisticRegression': LogisticRegression(random_state=42)
    }
    
    results = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        results[name] = acc
        logger.info(f"{name} 准确率: {acc:.4f}")
    
    return results

def train_model(df: pd.DataFrame) -> dict:
    """训练并比较多个模型，返回最佳模型和比较结果"""
    features = [
        "實際負磅", "排位體重", "檔位", "平均走位", "獨贏賠率",
        "马匹胜率", "平均完成时间", "平均赔率", "骑师胜率", "练马师胜率",
        "马匹近期表现", "骑师距离胜率", "练马师距离胜率"
    ]
    
    # 检查特征是否存在
    missing_features = [f for f in features if f not in df.columns]
    if missing_features:
        raise ValueError(f"缺少必要特征: {missing_features}")
        
    X = df[features].copy()
    y = df["是否第一"]

    # 数据清洗
    X.replace([np.inf, -np.inf], np.nan, inplace=True)
    X.fillna(0, inplace=True)
    
    # 划分训练测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
    
    # 训练各模型
    models = {
        "RandomForest": RandomForestClassifier(random_state=42),
        "XGBoost": XGBClassifier(random_state=42),
        "LightGBM": LGBMClassifier(random_state=42),
        "LogisticRegression": LogisticRegression(random_state=42)
    }
    
    results = {}
    best_acc = 0
    best_model = None
    
    for name, model in models.items():
        logger.info(f"开始训练 {name} 模型...")
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        results[name] = acc
        
        if acc > best_acc:
            best_acc = acc
            best_model = model
        
        logger.info(f"{name} 模型测试准确率: {acc:.4f}")
    
    # 保存最佳模型
    os.makedirs("models", exist_ok=True)
    with open("models/best_model.pkl", "wb") as f:
        pickle.dump(best_model, f)
    logger.info(f"最佳模型已保存 (准确率: {best_acc:.4f})")
    
    return {
        "best_model": best_model,
        "best_accuracy": best_acc,
        "model_results": results
    }
