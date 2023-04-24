class Cerbo:
    def __init__(self, strategy):
        self.strategy = strategy

    def update(self):
        # 这里是update方法的实现逻辑
        # 当有新的kline到达时，调用strategy的next方法
        self.strategy.next()