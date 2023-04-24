import datetime
import re
import time
import ccxt
from decimal import Decimal
import pandas as pd
import talib
from pprint import pprint
# from utils.positions import Positions
# 交易所初始化

binance = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
    })



class FutureTrader():
    def __init__(self,apikey='',secert=''):
        self.log = None
        self.symbols_dict = {}
        self.buy_orders_dict = {}
        self.sell_orders_dict = {}
        binance.apiKey = apikey
        binance.secret = secert
        binance.timeout = 20000
        # self.positions = Positions('future_positions.json')

    def creat_order(self,symbol,type,qty,price,side,pos_side,stop_order=False,busd=True):
        '''
        symbol : 交易对 BTCUSDT
        type : 订单类型 limit market
        qty : 数量 
        price : 价格
        side : 买卖方向 buy sell
        pos_side : 持仓方向 LONG SHORT
        stop_order : 是否是止损订单
        
        example:
        创建多头
        creat_order('MASKUSDT','limit',1,6.3,'buy','LONG')
        创建空头
        creat_order('MASKUSDT','limit',1,6.2,'sell','SHORT')
        多单止损
        creat_order('MASKUSDT','limit',1,5.7,'sell','LONG',stop_order=True) 
        空单止损
        creat_order('MASKUSDT','limit',1,6.7,'buy','SHORT',stop_order=True) 
        '''
        # 设置交易对和订单类型
        if busd == False:
            symbol_list = symbol.split('USDT')
            symbol = symbol_list[0] + '/USDT' 
        else:
            symbol_list = symbol.split('BUSD')
            symbol = symbol_list[0] + '/BUSD' 
        # 设置订单参数
        params = {
        'positionSide': pos_side,  # 建立多头头寸
        }

        if stop_order == True:
            params['closePosition'] = 'true'
            params['stopPrice'] = price
            qty = 1
            type = 'market'

        # 下单建立多头头寸，购买0.001个BTC，价格为27000
        order = binance.create_order(
        symbol=symbol,
        type=type,
        side=side,
        amount=qty,
        price=price,
        params=params,
        )

        return order['info']

    def round_to(self, value: float, target: float) -> float:
        """
        Round price to price tick value.
        """
        value = Decimal(str(value))
        target = Decimal(str(target))
        # rounded = float(int(round(value / target)) * target)
        # 删除了rounded，为了让目标向下取整。3.9这种好取到3.
        rounded = float(int((value / target)) * target)
        return rounded

    '''
    传入datafram 最大交易金额 返回atr 最小开仓手数 当前收盘价
    '''

    def turtle_calculate_unit(self, data, money):
        atr = data.iloc[-1]['ATR_21']
        close = data.iloc[-1]['close']
        unit = 0.01 * money / (atr / close)
        return(atr, unit, close)

    def get_account_info(self):
        r = binance.fapiPrivateV2_get_account({})
        return r

    def get_wallet_balance(self):
        r = binance.fapiPrivateV2_get_account({})
        return r
    
    def get_time(self):
        r = binance.fapiPublicGetTime({})
        return int(r['serverTime'])

    def get_aggtrade(self,symbol):
        # 最近成交归集
        '''
        {
            "a": 26129,         // 归集成交ID
            "p": "0.01633102",  // 成交价
            "q": "4.70443515",  // 成交量
            "f": 27781,         // 被归集的首个成交ID
            "l": 27781,         // 被归集的末个成交ID
            "T": 1498793709153, // 成交时间
            "m": true,          // 是否为主动卖出单
        }
        '''
        r = binance.fapiPublicGetAggTrades({'symbol':symbol})
        return pd.DataFrame(r)
    
    def future_transfer(self, symbol, amount, side):
        '''
        执行资产划转
        symbol : USDT
        amount : 数量
        side   :
        1: 现货账户向USDT合约账户划转

        2: USDT合约账户向现货账户划转

        3: 现货账户向币本位合约账户划转

        4: 币本位合约账户向现货账户划转
        '''
        params = {
            "asset": symbol,
            "amount": amount,
            "type" : side,
        }
        print(params)
        r = binance.sapiPostFuturesTransfer(params)
        return r

    # def 

    def get_exchange_info(self, symbol_query='USDT'):
        data = binance.fapiPublicGetExchangeInfo({})
        if isinstance(data, dict):
            items = data.get('symbols', [])
            if symbol_query == 'USDT':
                for item in items:
                    if (item.get('quoteAsset') == 'USDT' or item.get('quoteAsset') == 'BUSD') and item.get('status') == "TRADING":

                        symbol = item['symbol']
                        symbol_data = {"symbol": symbol}

                        for filters in item['filters']:
                            if filters['filterType'] == 'PRICE_FILTER':
                                symbol_data['min_price'] = float(
                                    filters['tickSize'])
                            elif filters['filterType'] == 'LOT_SIZE':
                                symbol_data['min_qty'] = float(
                                    filters['stepSize'])
                            elif filters['filterType'] == 'MIN_NOTIONAL':
                                symbol_data['min_notional'] = float(
                                    filters['notional'])
                        if bool(re.search(r'_', symbol)) == False:
                            # 防止出现交割合约BTC_2209这种
                            self.symbols_dict[symbol] = symbol_data
            if symbol_query == 'BUSD':
                for item in items:
                    if item.get('quoteAsset') == 'BUSD' and item.get('status') == "TRADING":

                        symbol = item['symbol']
                        symbol_data = {"symbol": symbol}

                        for filters in item['filters']:
                            if filters['filterType'] == 'PRICE_FILTER':
                                symbol_data['min_price'] = float(
                                    filters['tickSize'])
                            elif filters['filterType'] == 'LOT_SIZE':
                                symbol_data['min_qty'] = float(
                                    filters['stepSize'])
                            elif filters['filterType'] == 'MIN_NOTIONAL':
                                symbol_data['min_notional'] = float(
                                    filters['notional'])
                        if bool(re.search(r'\d', symbol)) == False:
                            # 防止出现交割合约BTC_2209这种
                            self.symbols_dict[symbol] = symbol_data

    def init_trading_symbol(self, symbol, margin_leverage, marginType='ISOLATED'):
        '''
        marginType : ISOLATED 逐仓 CROSSED 全仓
        '''
        try:
            r = binance.fapiPrivatePostMarginType(
                {'symbol': symbol, 'marginType': marginType})
            if r['msg'] != 'sucess':
                return False
            # print('OK')
        except:
            # print('Already ISOLATED')
            pass

        r = binance.fapiPrivatePostLeverage(
            {'symbol': symbol, 'leverage': margin_leverage})
        if r['leverage'] != str(margin_leverage):
            return False

        return float(r['leverage'])

    def changeleverage(self, symbol, leverage: int):
        '''
        调整全仓杠杆 symbol leverage:倍率
        '''
        try:
            r = binance.fapiPrivatePostLeverage(
                {'symbol': symbol, 'leverage': leverage})
            if r['leverage'] != str(leverage):
                return float(r['leverage'])
            return float(r['leverage'])
        except Exception as e:
            print('Chang margin level get an error！')
            return float(r['leverage'])

    def post_order(self, symbol, side, type, qty, price):
        '''
        symbol :交易对
        side : SELL BUY
        type : LIMIT MARKET TAKE_PROFIT_MARKET(市价止盈，不用传pos) STOP_MARKET(市价止盈，不用传pos)
        quantity : 数量
        price : 价格
        return :{'orderId': '58262779104', 'symbol': 'BTCUSDT', 'status': 'NEW', 'clientOrderId': 'fjaPeB9vmwLejWgNCwAiFd', 'price': '22344.90', 'avgPrice': '0.00000', 'origQty': '0.001', 'executedQty': '0', 'cumQty': '0', 'cumQuote': '0', 'timeInForce': 'GTC', 'type': 'LIMIT', 'reduceOnly': False, 'closePosition': False, 'side': 'BUY', 'positionSide': 'BOTH', 'stopPrice': '0', 'workingType': 'CONTRACT_PRICE', 'priceProtect': False, 'origType': 'LIMIT', 'updateTime': '1655349467248'}
        '''
        min_qty = self.symbols_dict.get(symbol).get('min_qty', 0)
        qty = self.round_to(qty, min_qty)
        min_price = self.symbols_dict.get(symbol).get('min_price', 0)
        price = self.round_to(price, min_price)
        value = abs(price * qty)
        min_value = self.symbols_dict.get(symbol, {}).get('min_notional', 0)
        if value < min_value and type != 'STOP_MARKET' and type != 'TAKE_PROFIT_MARKET' and type != 'LIMIT_r':
            print(
                f"{symbol} ,min_notional{min_value} value is small, delete the position data.")
            return 0
        params = {
            "symbol": symbol,
            "side": side,
            "type": type,
            "quantity": qty,
            "price": price,
            "timeInForce": "GTC",
        }
        if type == 'LIMIT_r':
            params['timeInForce'] = 'GTC'
            params['reduceOnly'] = 'true'
            params['type'] = 'LIMIT'
        if type == 'LIMIT':
            params['timeInForce'] = 'GTC'
        if type == 'MARKET':
            if params.get('price'):
                del params['price']
                del params['timeInForce']
        if type == 'STOP_MARKET':
            params['stopPrice'] = price
            params['closePosition'] = 'true'
            # del params['side']
            del params['price']
            del params['quantity']
            del params['timeInForce']
        if type == 'TAKE_PROFIT_MARKET':
            params['stopPrice'] = price
            params['closePosition'] = 'true'
            # del params['side']
            del params['price']
            del params['quantity']
            del params['timeInForce']

        print(f'++++symbol:{symbol},price:{price},qty:{qty}++++')
        r = binance.fapiPrivate_post_order(params)
        return r

    def get_book_ticker(self, symbol):
        '''
        return : {'symbol': 'BTCUSDT', 'bidPrice': '22374.90', 'bidQty': '0.733', 'askPrice': '22375.00', 'askQty': '1.276', 'time': '1655347582956'}
        bidPrice : 最优买单价格
        askPrice : 最优卖单价格
        '''
        r = binance.fapiPublicGetTickerBookticker({'symbol': symbol})
        return r

    def get_depth(self, symbol, limit=5):
        r = binance.fapiPublicGetDepth({'symbol': symbol, 'limit': limit})
        return r

    def get_dead_price(self, symbol,pos_side = 'BOTH'):
        '''
        获取当前持仓的爆仓价格
        限制：只允许单币种，只能全仓
        symbol : 'BTCUSDT',side 'LONG SHORT'
        双向持仓下，请注明side'LONG SHORT'
        '''
        r = binance.fapiPrivateGetPositionRisk()
        for item in r:
            if item['symbol'] == symbol and item['positionSide'] == pos_side:
                return (float(item['liquidationPrice']))

    def getPremiumindex(self):
        '''
        返回资金费率的字典{symbol:费率}
        '''
        r = binance.fapiPublicGetPremiumindex({})
        dict = {}
        for item in r:
            symbol = item['symbol']
            if bool(re.search(r'\d', symbol)) == False:
                lastFundingRate = float(item['lastFundingRate'])
                dict[symbol] = lastFundingRate
        return dict

    def get_order(self, symbol, order_id):
        '''
        return :{'orderId': '58262779104', 'symbol': 'BTCUSDT', 'status': 'FILLED', 'clientOrderId': 'fjaPeB9vmwLejWgNCwAiFd', 'price': '22344.90', 'avgPrice': '22343.80000', 'origQty': '0.001', 'executedQty': '0.001', 'cumQuote': '22.34380', 'timeInForce': 'GTC', 'type': 'LIMIT', 'reduceOnly': False, 'closePosition': False, 'side': 'BUY', 'positionSide': 'BOTH', 'stopPrice': '0', 'workingType': 'CONTRACT_PRICE', 'priceProtect': False, 'origType': 'LIMIT', 'time': '1655349467248', 'updateTime': '1655349467248'}
        '''
        r = binance.fapiPrivate_get_order(
            {'symbol': symbol, 'orderId': order_id})
        return r

    def get_history_order(self, symbol):
        '''
        return :{'orderId': '58262779104', 'symbol': 'BTCUSDT', 'status': 'FILLED', 'clientOrderId': 'fjaPeB9vmwLejWgNCwAiFd', 'price': '22344.90', 'avgPrice': '22343.80000', 'origQty': '0.001', 'executedQty': '0.001', 'cumQuote': '22.34380', 'timeInForce': 'GTC', 'type': 'LIMIT', 'reduceOnly': False, 'closePosition': False, 'side': 'BUY', 'positionSide': 'BOTH', 'stopPrice': '0', 'workingType': 'CONTRACT_PRICE', 'priceProtect': False, 'origType': 'LIMIT', 'time': '1655349467248', 'updateTime': '1655349467248'}
        '''
        r = binance.fapiPrivateGetAllOrders({'symbol': symbol})
        return r

    def countdowncancelall(self, symbol, time: int):
        '''
        倒计时取消挂单
        参数 ： symbol BTCUSDT
        时间 ： 60  即为60s
        '''
        r = binance.fapiPrivatePostCountdowncancelall(
            {'symbol': symbol, 'countdownTime': time*1000})
        return r

    def check_order(self, symbol, order_id):
        '''
        传入symbol ,订单ID
        CANCELED : 订单被手动取消
        FILLED : 订单完全成交
        NEW : 订单等待成交
        '''
        r = self.get_order(symbol, order_id)
        if r['status'] == 'CANCELED':
            qty = float(r['executedQty'])
            return ('CANCELED', qty)
        if r['status'] == 'FILLED':
            return ('FILLED', r['executedQty'])
        if r['status'] == 'NEW':
            return ('NEW', 0)
        else:
            return('XD',0)
    def cancel_order(self, symbol, order_id):
        r = binance.fapiPrivateDeleteOrder(
            {'symbol': symbol, 'orderId': order_id})
        return r

    def cancel_all_open_order(self, symbol):
        r = binance.fapiPrivateDeleteAllOpenOrders({'symbol': symbol})
        if r['code'] == '200':
            return True
        return False

    def return_symbol_pos(self, symbol,positionSide='BOTH'):
        '''
        返回当前币种持仓，带正负号
        '''
        r = binance.fapiPrivate_get_account({})['positions']
        for item in r:
            if item['symbol'] == symbol and item['positionSide'] == positionSide :
                return float(item['positionAmt'])
            
    def return_symbol_avg_price(self, symbol,positionSide='BOTH'):
        '''
        返回当前币种平均持仓成本
        '''
        r = binance.fapiPrivate_get_account({})['positions']
        for item in r:
            if item['symbol'] == symbol and item['positionSide'] == positionSide:
                return float(item['entryPrice'])
            
    def return_symbol_pnl(self, symbol):
        '''
        返回当前币种利润，带正负号
        '''
        r = binance.fapiPrivate_get_account({})['positions']
        for item in r:
            if item['symbol'] == symbol:
                return float(item['unrealizedProfit'])
            
    def return_initialMargin(self, symbol):
        '''
        返回当前币种持仓起始保证金
        '''
        r = binance.fapiPrivate_get_account({})['positions']
        for item in r:
            if item['symbol'] == symbol:
                return float(item['positionInitialMargin'])

    def return_all_symbol_pos(self):
        '''
        返回所有仓位不为0的币种格式(symbol,pos)
        '''
        pos_list = []
        r = binance.fapiPrivate_get_account({})['positions']
        for item in r:
            if float(item['positionAmt']) !=0:
                pos_list.append((item['symbol'],float(item['positionAmt'])))
        return pos_list

    def return_open_order(self,symbol):
        '''
        返回当前挂单，如果挂单已经成交或者取消，返回Order does not exist
        '''
        r = binance.fapiPrivateGetOpenOrders({'symbol':symbol})
        return r
    
    def return_xianhuo_usdt(self):
        '''
        返回现货中有多少USDT
        '''
        return binance.fetch_balance()['USDT']['free']
    
    def kelly_transfer(self,kelly):
        '''
        依据凯利系数自动划转对应的金额，返回划转的数量
        '''
        # 先把合约所有的都划转到现货
        money = float(self.get_wallet_balance()['availableBalance'])
        if money != 0:
            self.future_transfer('USDT',money, 2)
        total =  self.return_xianhuo_usdt()
        need = kelly * total + 2
        need = kelly
        self.future_transfer('USDT',need,1)
        print(f'凯利划转执行，划转金额{need}，当前凯利系数{kelly}')
        return need
    
    def normal_transfer(self,money_1):
        '''
        普通划转，返回划转的数量
        '''
        # 先把合约所有的都划转到现货
        money = float(self.get_wallet_balance()['availableBalance'])
        if money != 0:
            self.future_transfer('USDT',money, 2)
        self.future_transfer('USDT',money_1,1)
        print(f'普通划转执行，划转金额{money_1}')
        return money_1
    