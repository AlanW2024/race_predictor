import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from scraper.fetcher import scrape_race_day_parallel, fetch_race_schedule
from data_processing.preprocessing import preprocess_data
from data_processing.feature_engineering import add_historical_features
from machine_learning.model import train_model
from machine_learning.predictor import predict_winner
from utils.session import create_session
from utils.logger import logger

if __name__ == "__main__":
    session = create_session()

    # 指定你想查的日期與場地 (使用dd/mm/yyyy格式)
    racing_days = [
        ("23/03/2025", "ST"),
        ("26/03/2025", "ST"), 
        ("30/03/2025", "ST")
    ]
    
    combined_results = []
    for date_str, venue in racing_days:
        logger.info(f"===== 开始抓取 {date_str} {venue} =====")
        day_races = scrape_race_day_parallel(session, date_str, venue)
        if not day_races:
            logger.info(f"{date_str} {venue} 无数据，跳过。")
            continue

        for race_info in day_races:
            base_info = race_info.get("基本資訊", {})
            results = race_info.get("賽果", [])
            for row in results:
                combined_results.append({**base_info, **row})
    
    # 進行後續資料處理 & 建模
    df = pd.DataFrame(combined_results)
    
    # --- 添加排序邏輯 ---
    # 轉換日期為可排序格式，並確保場次是數值類型
    df['日期'] = pd.to_datetime(df['日期'], format='%d/%m/%Y')
    df['場次'] = pd.to_numeric(df['場次'])
    # 按日期和場次排序
    df = df.sort_values(by=['日期', '場次']).reset_index(drop=True)
    # 將日期轉回原始字符串格式（如果後續需要）
    df['日期'] = df['日期'].dt.strftime('%d/%m/%Y')
    # --- 排序結束 ---
    
    df = preprocess_data(df)
    df = add_historical_features(df) # 現在傳遞的是排序後的數據
    
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/processed_data.csv", index=False, encoding="utf-8-sig")
    logger.info("数据处理完成，已保存到 data/processed_data.csv")
    
    # 训练模型并获取比较结果
    model_result = train_model(df)
    best_model = model_result["best_model"]
    best_acc = model_result["best_accuracy"]
    model_results = model_result["model_results"]
    
    logger.info("\n===== 模型比较结果 =====")
    for name, acc in model_results.items():
        logger.info(f"{name}: {acc:.4f}")
    logger.info(f"最佳模型准确率: {best_acc:.4f}")
    
    # 調試日期與數據過濾
    logger.info("開始檢查可用日期與數據：")
    print("可用日期：", df["日期"].unique())  # 打印所有日期以供檢查
    
    
# --- 預測指定日期的所有場次 ---
# 選取最新的日期進行預測
prediction_date = df['日期'].unique()[-1] if not df.empty else None 

if prediction_date:
    logger.info(f"===== 開始預測 {prediction_date} 的所有場次 =====")
    prediction_df = df[df["日期"] == prediction_date].copy()
    
    if not prediction_df.empty:
        # 獲取該日期的所有場次編號
        race_numbers = sorted(prediction_df['場次'].unique())
        logger.info(f"找到 {prediction_date} 的場次: {race_numbers}")

        for race_no in race_numbers:
            logger.info(f"--- 預測第 {race_no} 場 ---")
            try:
                # 獲取該場次的數據
                sample_race = prediction_df.groupby("場次").get_group(race_no).copy()
                
                # 進行預測，獲取帶概率的 DataFrame
                race_predictions = predict_winner(sample_race, best_model) 
                
                # 打印預測結果
                if not race_predictions.empty:
                    winner = race_predictions.loc[0, "馬名"] # DataFrame 已按概率降序排列
                    logger.info(f"預測第 {race_no} 場第一名: {winner}")
                    
                    # 打印所有馬匹的預測概率
                    logger.info(f"第 {race_no} 場預測概率詳情:")
                    # 使用 to_string() 避免截斷
                    print(race_predictions[['馬名', '预测概率']].to_string(index=False)) 
                else:
                     logger.warning(f"第 {race_no} 場預測結果為空。")

            except Exception as e: # 捕捉可能的錯誤，例如分組錯誤
                logger.error(f"預測第 {race_no} 場時出錯: {e}")
    else:
        logger.warning(f"日期 {prediction_date} 沒有數據可供預測。")
else:
    logger.error("數據集中沒有可用的日期進行預測。")
# --- 預測結束 ---
