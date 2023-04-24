from broker import BROKER
from cerbo import Cerbo
from btc_60_martin import MyStrategy
import sys
import pandas as pd
import time

symbol = 'ETHBUSD'

strategy = MyStrategy(symbol)
# 创建一个Cerbo对象并传入strategy对象
cerbo = Cerbo(strategy)
while True:
    try:
        cerbo.update()
        time.sleep(20)
    except Exception as e:
        print(e)
        time.sleep(20)
