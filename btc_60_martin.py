import pandas as pd
from datetime import timedelta, datetime
import random,sys,json
from broker import BROKER
import os

params = (
    ('margin', 20),
    ('win', 0.001), #止盈比例 0.1%
    ('loss', 0.002),# 止损比例 0.2%
)

class PARAMS():
    def __init__(self,params):
        for item in params:
            key = 'self.' + item[0] 
            value = item[1]
            exec("%s = %f" % (key,value))
            
class MyStrategy():

    def __init__(self,symbol):
        self.params = PARAMS(params)
        self.broker = BROKER(symbol)
        self.symbol = symbol
        # print('现金',self.broker.get_cash())
        self.load_config()
        
    def load_config(self):
        #在这里创建变量,会自动保存到文件
        self.price_gap = 0 #确定加仓的间隔，取10分钟内的平均涨跌幅
        self.last_win = 1 #上一次盈利的是空仓还是多仓 0 空 1 多
        self.inital_money = 0 #初始购买份数 = 总金额 / 3 / （1+2+4）
        self.long_last_buy = 0 
        self.long_increase_time = 0
        self.short_last_buy = 0
        self.short_increase_time = 0
        self.long_order = None
        self.short_order = None
        self.long_win_order = None
        self.short_win_order = None
        self.long_stop_order = None
        self.short_stop_order = None
        self.full_buy = False
        self.dead_order = None
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                data = json.load(f)
                for key, value in data.items():
                    setattr(self, key, value)
    
    def save_to_json(self):
        data = {}
        #你不想保存到json的变量
        ban_list = ['params','broker','cover']
        for key, value in self.__dict__.items():
            if not key.startswith("__"):
                if key not in ban_list:
                    data[key] = value
        with open("config.json", "w") as f:
            json.dump(data, f)
                    
    
    def next(self):
        # 止盈单不应该带上stop_order,止损单要带上stop_order
        long_position = self.broker.get_position(side='long')
        short_position = self.broker.get_position(side='short')
        long_avg_price = self.broker.get_avg_price(side='long')
        short_avg_price = self.broker.get_avg_price(side='short')
        # long_stop_activate = short_stop_activate = 0
        
        if self.long_win_order is not None:
            r = self.broker.check_order(self.long_win_order[0])
            if r[0] == 'FILLED':
                self.last_win = 1
                self.long_win_order = None
                self.long_last_buy = 0
                self.long_increase_time = 0
                long_position = 0
                self.broker.cancel()
                print('止盈单成交')
                print('------------')
            if r[0] == 'CANCELED' or r[0] == 'EXPIRED':
                self.long_win_order = None
            # print(f'多单止盈检查结果{r}')
        
        if self.long_stop_order is not None:
            r = self.broker.check_order(self.long_stop_order[0])
            if r[0] == 'FILLED':
                self.last_win = 1
                self.long_win_order = None
                self.long_last_buy = 0
                self.long_increase_time = 0
                self.long_stop_order = None
                long_stop_activate = 0
                self.broker.cancel()
                print(f'加仓单成交')
                print('------------')
            if r[0] == 'CANCELED' or r[0] == 'EXPIRED':
                self.long_stop_order = None
            # print(f'多单止损检查结果{r}')
        
        if self.dead_order is None and long_position != 0 and self.full_buy == True:
            print(f'检测到最后加仓，设置止损订单')
            # 挂爆仓止损
            dead_price = self.broker.future.get_dead_price(self.symbol,'LONG')
            self.dead_order = self.broker.future.creat_order(self.symbol,'limit',1,dead_price+5,'sell','LONG',stop_order=True) 
            print(f'获取的爆仓价格为{dead_price},设置爆仓单{self.dead_order}')
        
        if long_position == 0:
            # 开多单
            # 没仓位了就把止损单关了
            self.full_buy = False
            self.dead_order = None
            close = self.broker.get_ticker()
            self.inital_money = self.broker.get_cash() / 5
            size = self.inital_money / close
            self.broker.cancel()
            orders = self.broker.buy(size, side='long')
            self.long_order = orders[0]
            print(f'开多单,价格{close:.4f},数量{size:.4f},初始资金:{self.inital_money:.4f}')
        
        if long_position != 0:
            if self.long_stop_order is None and self.full_buy == False:
                # 挂加仓单
                try:
                    self.long_stop_order = self.broker.buy(long_position*2,'long',price=long_avg_price*(1-self.params.loss))
                except:
                    # 判断是不是钱不够了
                    cash = self.broker.get_cash()
                    if cash < 0:
                        print(f'已经没有钱再加仓了,cash{cash}')
                        self.full_buy = True
                    elif cash * 50 < long_position * 2 * long_avg_price*(1-self.params.loss):
                        print(f'最后一次加仓,资金{cash}')
                        size = cash * 50 / (long_avg_price*(1-self.params.loss))
                        self.long_stop_order = self.broker.buy(size,'long',price=long_avg_price*(1-self.params.loss))
                        self.full_buy = True
                        
            
            if self.long_win_order is None:
                # 挂止盈单
                self.long_win_order = self.broker.sell(long_position, 'long',price = long_avg_price * (1 + self.params.win))
                    
        self.save_to_json()