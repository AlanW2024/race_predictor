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
import math

def seconds_to_mmssff(seconds):
    """将秒数转换为 m:ss.ff 格式的字符串"""
    if pd.isna(seconds) or not isinstance(seconds, (int, float)) or seconds < 0:
        return None
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    # 使用 round 进行四舍五入到两位小数，然后格式化
    # 增加一个极小值避免浮点数精度问题导致如 .999 变成 .99 而不是 1.00
    formatted_seconds_val = round(remaining_seconds + 1e-9, 2) 
    # 检查是否因四舍五入进位到 60
    if formatted_seconds_val >= 60.0:
        minutes += 1
        formatted_seconds_val -= 60.0
        
    # 格式化为 xx.xx，并确保秒数部分总是两位数（如 05.27 或 05.00）
    # 使用 format 方法可以更明确地控制格式
    formatted_seconds_str = "{:05.2f}".format(formatted_seconds_val)
    
    return f"{minutes}:{formatted_seconds_str}"

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

    # 创建一个副本用于模型训练和预测（保留秒数格式）
    df_for_model = df.copy()
    logger.info("创建用于模型训练/预测的数据副本（保留秒数格式）。")

    # --- 格式化用于保存的 DataFrame ---
    df_to_save = df.copy() # 创建另一个副本用于保存
    logger.info("开始将时间格式转换为 m:ss.ff 用于保存...")
    # 需要格式化的列现在是带有 '_秒' 后缀的原始秒数列
    # 注意：Excel截图显示分段时间是纯数字秒数，所以不格式化分段时间列
    time_cols_to_format_seconds = ['完成時間', '平均完成时间'] + [f"累積時間{i}_秒" for i in range(1, 5)] 
    
    for col_seconds in time_cols_to_format_seconds:
        # 目标列名去掉 '_秒' 后缀
        col_target = col_seconds.replace('_秒', '') 
        if col_seconds in df_to_save.columns:
            logger.info(f"转换 {col_seconds} 为 {col_target} (m:ss.ff 格式)...")
            # 应用格式化函数，并将结果存到新的或覆盖旧的列名
            df_to_save[col_target] = df_to_save[col_seconds].apply(seconds_to_mmssff)
            # 可以选择删除原始秒数列，如果不需要的话
            # del df_to_save[col_seconds] 
        elif col_target in df_to_save.columns and col_target != col_seconds: # 处理 '完成時間', '平均完成时间'
             logger.info(f"转换 {col_target} (m:ss.ff 格式)...")
             df_to_save[col_target] = df_to_save[col_target].apply(seconds_to_mmssff)


    # 确保存储的分段时间列是原始秒数（根据Excel截图）
    # 如果 parser.py 中计算了分段时间秒数，确保它们被包含在 df_to_save 中
    # 如果需要，可以重命名列以匹配 Excel 截图（例如 '分段時間1' 而不是 '分段時間1_秒'）
    for i in range(1, 5):
        col_seconds = f"分段時間{i}_秒"
        col_target = f"分段時間{i}"
        if col_seconds in df_to_save.columns:
             # 如果目标列不存在或需要覆盖，则重命名/赋值
             if col_target not in df_to_save.columns or col_target == col_seconds:
                 df_to_save[col_target] = df_to_save[col_seconds]
                 if col_target != col_seconds:
                     del df_to_save[col_seconds] # 删除带 _秒 的列
             # 如果目标列已存在且不同，则可能需要检查逻辑，这里假设直接使用秒数
             elif col_target in df_to_save.columns and col_target != col_seconds:
                 df_to_save[col_target] = df_to_save[col_seconds] # 确保是秒数
                 del df_to_save[col_seconds]


    # 删除不再需要的原始秒数列（可选，如果上面没有删除的话）
    cols_to_drop = [f"累積時間{i}_秒" for i in range(1, 5) if f"累積時間{i}_秒" in df_to_save.columns and f"累積時間{i}" in df_to_save.columns]
    if '全場時間_秒' in df_to_save.columns: # 全场时间似乎也不需要保存
        cols_to_drop.append('全場時間_秒')
    df_to_save.drop(columns=cols_to_drop, inplace=True, errors='ignore')


    os.makedirs("data", exist_ok=True)
    # 修改输出文件名，尝试写入新文件以绕过锁定
    output_csv_path = "data/processed_data_v2.csv" 
    try:
        df_to_save.to_csv(output_csv_path, index=False, encoding="utf-8-sig")
        logger.info(f"数据处理完成，相关时间格式已转换，已保存到 {output_csv_path}")
    except PermissionError as e:
        logger.error(f"写入文件 {output_csv_path} 时仍然发生权限错误: {e}")
        logger.error("请确保没有程序锁定该文件或 data 文件夹，并检查文件/文件夹权限。")
        # 如果写入新文件也失败，则问题可能更复杂
        raise e # 重新抛出异常，让脚本停止

    # --- 保存结束 ---

    # --- 模型训练和预测（使用 df_for_model，包含秒数）---
    logger.info("开始模型训练（使用秒数格式的时间数据）...")
    # 训练模型并获取比较结果 - 传入包含秒数的 df_for_model
    model_result = train_model(df_for_model) 
    best_model = model_result["best_model"]
    best_acc = model_result["best_accuracy"]
    model_results = model_result["model_results"]
    
    logger.info("\n===== 模型比较结果 =====")
    for name, acc in model_results.items():
        logger.info(f"{name}: {acc:.4f}")
    logger.info(f"最佳模型准确率: {best_acc:.4f}")
    
    # 調試日期與數據過濾
    logger.info("開始檢查可用日期與數據：")
    # 使用 df_for_model 或 df_to_save 都可以，因为日期列没变
    print("可用日期：", df_for_model["日期"].unique())  
    
    
# --- 預測指定日期的所有場次 ---
# 選取最新的日期進行預測
# 使用 df_for_model 或 df_to_save 都可以
prediction_date = df_for_model['日期'].unique()[-1] if not df_for_model.empty else None 

if prediction_date:
    logger.info(f"===== 開始預測 {prediction_date} 的所有場次 =====")
    # 使用包含秒数的 df_for_model 进行预测数据的筛选
    prediction_df = df_for_model[df_for_model["日期"] == prediction_date].copy() 
    
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
