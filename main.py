from broker import BROKER
from cerbo import Cerbo
from martin_long import MyStrategy
import sys
import pandas as pd
import time
import datetime
import sys
from pprint import pprint
symbol = 'BTCUSDT'

broker = BROKER(symbol)
long = MyStrategy(symbol)
# short = MyStrategy_short(symbol)
# 创建一个Cerbo对象并传入strategy对象
cerbo_long = Cerbo(long)
# cerbo_short = Cerbo(short)
# trend = None #多头趋势
trend = 1 #多头趋势
while True:
    try:
        # now = datetime.datetime.now()
        # if  7 > now.second > 3 and now.minute % 5 == 0 :
        #     # 获取持仓信息
        #     positon = broker.ta_trade.get_u_position(symbol, '5m',limit=2)
        #     if float(positon.iloc[-1]['sumOpenInterest']) > float(positon.iloc[-2]['sumOpenInterest']):
        #         trend = 1
        #     else:
        #         trend = 0
        #     print(f'当前交易对{symbol},当前趋势{trend}')
        if trend is not None:
            cerbo_long.update(trend)
            # cerbo_short.update(trend)
        time.sleep(3)   
    except Exception as e:
        print(e)
        time.sleep(3)
            
        
        
