import requests
import pandas as pd
from datetime import datetime

# 币安合约API的基本地址
base_url = "https://fapi.binance.com"

# 合约符号和K线间隔
symbol = "BTCUSDT"
interval = "1h"

# 获取当前时间戳
end_time = int(datetime.timestamp(datetime.now())) * 1000

# 计算7天前的时间戳
start_time = end_time - 7 * 24 * 60 * 60 * 1000

# API端点
endpoint = f"/fapi/v1/klines"
params = {
    "symbol": symbol,
    "interval": interval,
    "startTime": start_time,
    "endTime": end_time,
    "limit": 1000  # 最大限制，可以根据需要适当调整
}

# 发送API请求并获取数据
response = requests.get(base_url + endpoint, params=params)
data = response.json()

# 将数据转换为DataFrame
df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume", "close_time", "quote_asset_volume", "number_of_trades", "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"])

# 重命名列名和转换时间戳
df.rename(columns={"timestamp": "timestamp", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"}, inplace=True)
df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')

# 计算最高价和最低价的差值除以开盘价的比例
df["high_low_ratio"] = (df["high"].astype(float) - df["low"].astype(float)) / df["open"].astype(float)

# 保存数据为CSV文件
# df.to_csv("BTCUSDT_1hKline_7days_with_ratio.csv", index=False)
# print("数据已保存为BTCUSDT_1hKline_7days_with_ratio.csv")


# 计算高低比例的平均值
average_ratio = df["high_low_ratio"].mean()

# 打印最大值和最小值
max_ratio = df["high_low_ratio"].max()
min_ratio = df["high_low_ratio"].min()

print(f"最大高低比例: {max_ratio:.4f}")
print(f"最小高低比例: {min_ratio:.4f}")
print(f"平均高低比例: {average_ratio:.4f}")

