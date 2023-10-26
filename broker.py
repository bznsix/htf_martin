from gateway.binance_gateway import FutureTrader
# from wickky_logic.wickky import WICKKY
import pandas as pd

class BROKER():
    
    def __init__(self,symbol):
        self.symbol = symbol
        self.future = FutureTrader('','')
        self.future.get_exchange_info()
        # self.ta_trade = WICKKY()
        
    def get_cash(self,busd=False):
        if busd == True:
            assets = self.future.get_wallet_balance()['assets']
            for item in assets:
                if item['asset'] == 'BUSD':
                    return float(item['availableBalance']) - 1
        else:
            return float(self.future.get_wallet_balance()['availableBalance']) - 1
    
    def get_position(self,side):
        
        return self.future.return_symbol_pos(self.symbol,positionSide=side.upper())
    
    def get_avg_price(self,side):
        return self.future.return_symbol_avg_price(self.symbol,positionSide=side.upper())
    
    def buy(self,size,side,stop_order=False,price=None):
        prices = self.future.get_book_ticker(self.symbol)
        bid_price = float(prices['askPrice'])
        if price is not None:
            bid_price = price
        print(f'{self.symbol}购买，价格{bid_price},数量{size},方向{side}')
        order = self.future.creat_order(self.symbol, 'limit', size, bid_price, 'buy',side,stop_order=stop_order)
        return order
    
    def sell(self,size,side,stop_order=False,price=None):
        prices = self.future.get_book_ticker(self.symbol)
        bid_price = float(prices['bidPrice'])
        if price is not None:
            bid_price = price
        print(f'{self.symbol}出售，价格{bid_price},数量{size},方向{side}')
        order =  self.future.creat_order(self.symbol, 'limit', size, bid_price, 'sell', side,stop_order=stop_order)
        return order
    
    def cancel(self):
        self.future.cancel_all_open_order(self.symbol)
    
    def check_order(self, order):
        return self.future.check_order(symbol=self.symbol,order_id=order)

    # def get_data(self,timeframe='3m'):
    #     # 获取K线数据
    #     data = self.ta_trade.getKlines(self.symbol,timeframe=timeframe,isPerp=True,limit=100)
    #     df = self.ta_trade.getEMA(data)[:-1] #舍弃最新的K线
    #     rev_df = pd.DataFrame(df.values[::-1], columns=df.columns)
    #     return rev_df
    
    def get_ticker(self):
        # 获取最新价格
        prices = self.future.get_book_ticker(self.symbol)
        bid_price = float(prices['bidPrice'])
        return bid_price
        

'''
测试 
开多单
开空单
多单止损
空单止损
平多单
平空单
获取多头仓位
获取空头仓位
获取多头平均成本
获取空头平均成本
'''

