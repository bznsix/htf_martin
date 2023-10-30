import pandas as pd
from datetime import timedelta, datetime
import random,sys,json
from broker import BROKER
import os
import time
from pprint import pprint
params = (
    ('margin', 10), #杠杆倍数
    ('gap_time', 5), #分成多少份
    ('kline_interval',60*60*1000), #ms级别K线时间戳
    ('long_win_ratio',0.01) #止盈比例
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
        self.start_cash = 0 #起始总资金
        self.now_gap = 0 #现在已经用了多少份
        self.long_order = {} #所有的多单{'gap_time':order}
        self.long_stop_order = {} #最新的止盈单
        self.dead_order = 0 #最新的止损订单
        self.last_can_buy = 0 #最新一次可以购买的时间
        self.last_buy_price = 0 #最后一次购买的价格
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
                    
    def clear_order(self):
        # 清除变量，更新资金
        self.broker.cancel()
        # 清除所有订单
        self.long_order = {}
        self.long_stop_order = {}
        self.dead_order = 0
        self.now_gap = 0
        self.last_buy_price = 0
        self.start_cash = self.broker.get_cash() * self.params.margin #更新总资金
    
    def after_create_order(self,price):
        self.now_gap += 1
        self.last_buy_price = price
        self.last_can_buy = time.time() * 1000 + self.params.kline_interval
        print(f'更新下次可以购买时间，当前时间{time.time()},下次可以购买{self.last_can_buy}')
        
    def next(self,trend):

        close = self.broker.get_ticker()
        long_pos = self.broker.get_position(side='long')
        timestamp_ms = int(time.time() * 1000)
        
        if long_pos == 0 :
            self.clear_order()
            # 限价开一份多单,千分之一滑点
            size = self.start_cash / self.params.gap_time / close
            print(f'起始创建订单，size:{size},star_cash:{self.start_cash}')
            order = self.broker.buy(size,'long',close*1.001)
            self.long_order[order['orderId']] = order
            self.after_create_order(close*1.001)
        
        if long_pos > 0:
            for key in self.long_order.keys():
                if self.long_stop_order.get(key) is None:
                    # 当前level没有止盈单
                    # 检测买单是否成交
                    r = self.broker.check_order(self.long_order[key]['orderId'])[0]
                    if r  == 'FILLED':
                        # 成交了就更新买单信息
                        self.long_order[key] = self.broker.future.get_order(symbol=self.symbol,order_id=key)
                        price = float(self.long_order[key]['avgPrice']) * (1+self.params.long_win_ratio)
                        amount = float(self.long_order[key]['executedQty'])
                        print(f'创建止盈单,单号:{key},价格{price:.4f},数量{amount:.4f}')
                        self.long_stop_order[key] = self.broker.sell(amount, 'long',price = price)
                    # else:
                    #     pprint(f'当前订单还没有成交,{self.long_order[key]}')

            # 加仓逻辑
            # print(self.now_gap,close < self.last_buy_price * (1-self.params.long_win_ratio),timestamp_ms > self.last_can_buy)
            if self.now_gap < self.params.gap_time and close < self.last_buy_price * (1-self.params.long_win_ratio) and timestamp_ms > self.last_can_buy:
                size = self.start_cash / self.params.gap_time / close
                print(f'触发加仓，size:{size},当前时间:{timestamp_ms},上次购买{self.last_buy_price},当前是{self.now_gap}次')
                order = self.broker.buy(size,'long',close*1.001)
                self.long_order[order['orderId']] = order
                self.after_create_order(close*1.001)
        
        keys_to_remove = []
        # 检测止盈单逻辑
        for key,order in self.long_stop_order.items():
            try:
                r = self.broker.check_order(order['orderId'])[0]
                if r  == 'FILLED':
                    print(f'第{key}次加仓成功止盈')
                    keys_to_remove.append(key)
                    self.now_gap -= 1
                    # 为了庆祝，我们将时间回退，方便我们继续加仓
                    self.last_can_buy = time.time() * 1000 - self.params.kline_interval
                    #为了更快的复利，我们在这里更新下起始总资金
                    self.start_cash = self.broker.get_cash() / (self.params.gap_time - self.now_gap) * self.params.gap_time * self.params.margin
                    print(f'触发更新起始总资金，起始总资金为->{self.start_cash}')
            except:
                # 加仓可能会清除止盈订单
                del self.long_stop_order[key]
        
        for key in keys_to_remove:
            print(f'这一次删除的订单{key}')
            del self.long_stop_order[key]
            del self.long_order[key]
            
        
        buy_price = []
        for key,order in self.long_order.items():
            buy_price.append(float(order['price']))
        
        if len(buy_price) != 0:
            self.last_buy_price = min(buy_price)
            # print(f'当前还有的订单列表：{buy_price},更新最后一次购买：{self.last_buy_price}')
                
        # pprint(f'当前时间{timestamp_ms},当前仓位{long_pos}')   
        # pprint(self.long_order)
        # pprint(self.long_stop_order)
        self.save_to_json()
