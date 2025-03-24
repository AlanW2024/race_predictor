import os
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
    racing_days = fetch_race_schedule(session, num_days=3)
    if not racing_days:
        logger.error("无法获取赛程，程序退出。")
        exit(1)
    
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
    
    df = pd.DataFrame(combined_results)
    df = preprocess_data(df)
    df = add_historical_features(df)
    
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/processed_data.csv", index=False, encoding="utf-8-sig")
    logger.info("数据处理完成，已保存到 data/processed_data.csv")
    
    model = train_model(df)
    
    # 选择一个有数据的日期进行预测
    for date_str, venue in reversed(racing_days):  # 从后向前检查
        sample_df = df[df["日期"] == date_str]
        if not sample_df.empty:
            try:
                sample_race = sample_df.groupby("場次").get_group("1")
                winner = predict_winner(sample_race, model)
                logger.info(f"预测 {date_str} 第 1 场第一名: {winner}")
                break
            except KeyError:
                logger.warning(f"{date_str} 无第 1 场数据，尝试其他日期")
    else:
        logger.error("所有日期均无数据可用于预测")