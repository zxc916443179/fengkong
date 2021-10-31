# -*- coding: utf-8 -*-

from collections import deque, defaultdict


class Trade:
    def __init__(self, vol, price, direct=1, tcode=None, scode=None,
            taxs=None, date=None, time=None):
        self.vol = abs(vol)
        self.price = price
        if vol < 0:
            self.direct = -1
        else:
            self.direct = direct
        self.tcode = tcode
        self.scode = scode
        self.date = date
        self.time = time
        self.update_taxs(taxs)

    def update_taxs(self, taxs):
        if taxs is None:
            self.system_tax = 0.0
            self.trader_tax = 0.0
            self.stamp_tax = 0.0
            self.sh_tax = 0.0
        else:
            self.system_tax = self.vol * self.price * taxs["system"]
            self.trader_tax = self.vol * self.price * taxs["trader"]
            if self.direct == -1:
                self.stamp_tax = self.vol * self.price * taxs["stamp"]
            else:
                self.stamp_tax = 0
            if self.scode >= "600000":
                self.sh_tax = self.vol * self.price * taxs["shanghai"]
            else:
                self.sh_tax = 0


class Calculator:

    def __init__(self, scode=None, tcode=None):
        self.scode = scode
        self.tcode = tcode
        self.profit_land = 0.0
        self.profit_float = 0.0
        self.deque_b = deque()
        self.deque_s = deque()
        self.price_current = 0

    def update_profit_float(self):
        p = 0.0
        for trade in self.deque_b:
            p += (self.price_current - trade.price) * trade.vol
        for trade in self.deque_s:
            p += (trade.price - self.price_current) * trade.vol
        self.profit_float = p

    def set_price_current(self, price_current):
        self.price_current = price_current
        self.update_profit_float()

    def add(self, trade):
        if trade.direct == -1:
            self.deque_s.append(trade)
        elif trade.direct == 1:
            self.deque_b.append(trade)
        else:
            raise Exception("Not Expect Branch")
        while len(self.deque_b) > 0 and len(self.deque_s) > 0:
            b_trade = self.deque_b.popleft()
            s_trade = self.deque_s.popleft()
            delta_price = s_trade.price - b_trade.price
            volumn = min(b_trade.vol, s_trade.vol)
            self.profit_land += delta_price * volumn
            if b_trade.vol > s_trade.vol:
                r_trade = Trade(b_trade.vol-s_trade.vol, b_trade.price, 1)
                self.deque_b.appendleft(r_trade)
            elif b_trade.vol < s_trade.vol:
                r_trade = Trade(s_trade.vol-b_trade.vol, s_trade.price, -1)
                self.deque_s.appendleft(r_trade)
        self.set_price_current(trade.price)

    def compute(self, trade_list, price_current):
        for (vol, price) in trade_list:
            self.add(Trade(vol, price))
        self.set_price_current(price_current)


class TradeAnalyzer:

    def __init__(self):
        self.trade_date = ""

        self.traders_code = []
        self.traders_name = {}
        self.traders_loss = {}

        self.secs_code = []
        self.secs_name = {}
        self.secs_price = {}

        self.trades_df = defaultdict(list)
        self.calculators = defaultdict(Calculator)
        self.trades_df_dirty = False

        self.detail_df = None
        self.trader_df = None
        self.system_df = None
        self.unbalanced_df = None
        self.result_df_dirty = True

        self.taxs = {
                "system": 0.00011,
                "trader": 0.0003,
                "stamp": 0.001,
                "shanghai": 0.00002
                }

    def set_taxs(self, taxs):
        self.taxs = taxs
        self.trades_df_dirty = True

    def set_current_price(self, prices_dict):
        for scode in self.secs_code:
            if scode in prices_dict.keys():
                self.secs_price[scode] = prices_dict[scode]
        for (tcode, scode) in self.calculators.keys():
            if scode in self.secs_price.keys():
                self.calculators[(tcode, scode)].set_price_current(prices_dict[scode])

    def add_trade(self, trade):
        if trade.tcode not in self.traders_name.keys():
            # Add a non expect trade
            return
        self.trades_df[(trade.tcode, trade.scode)].append(trade)
        self.calculators[(trade.tcode, trade.scode)].add(trade)
        self.result_df_dirty = True
        if trade.tcode not in self.traders_code:
            self.traders_code.append(trade.tcode)
        if trade.scode not in self.secs_code:
            self.secs_code.append(trade.scode)

    def add_trades(self, trades):
        for trade in trades:
            self.add_trade(trade)

    def update_trades_df(self):
        if self.trades_df_dirty:
            raise Exception("No Implement")
        else:
            return

    def update_result_df(self):
        if self.result_df_dirty:
            self.detail_df = list()
            self.unbalanced_df = list()
            for (tcode, scode) in self.calculators.keys():
                # update detail_df
                result = {"tcode": tcode, "scode": scode}
                result["profit_land"] = self.calculators[(tcode,scode)].profit_land
                result["profit_float"] = self.calculators[(tcode,scode)].profit_float
                result["trader_tax"] = 0.0
                result["system_tax"] = 0.0
                result["stamp_tax"] = 0.0
                result["sh_tax"] = 0.0
                for t in self.trades_df[(tcode, scode)]:
                    result["system_tax"] += t.system_tax
                    result["trader_tax"] += t.trader_tax
                    result["stamp_tax"] += t.stamp_tax
                    result["sh_tax"] += t.sh_tax
                self.detail_df.append(result)
                # update unbalanaced_df
                result = {"tcode": tcode, "scode": scode}
                if len(self.calculators[(tcode, scode)].deque_s) != 0:
                    for t in self.calculators[(tcode, scode)].deque_s:
                        result["vol"] = t.vol
                        result["price"] = t.price
                        result["direct"] = t.direct
                        self.unbalanced_df.append(result)
                elif len(self.calculators[(tcode, scode)].deque_b) != 0:
                    for t in self.calculators[(tcode, scode)].deque_b:
                        result["vol"] = t.vol
                        result["price"] = t.price
                        result["direct"] = t.direct
                        self.unbalanced_df.append(result)
                else:
                    # balanced!
                    pass
            #print(self.detail_df)
            #print(self.unbalanced_df)

            self.trader_df = dict()
            self.system_df = defaultdict(float)
            for i in self.detail_df:
                # update trader_df
                if i["tcode"] not in self.trader_df.keys():
                    self.trader_df[i["tcode"]] = {
                            "trader_tax":   i["trader_tax"],
                            "system_tax":   i["system_tax"],
                            "stamp_tax":    i["stamp_tax"],
                            "sh_tax":       i["sh_tax"],
                            "profit_land":  i["profit_land"],
                            "profit_float": i["profit_float"],
                            }
                else:
                    self.trader_df[i["tcode"]]["trader_tax"]    += i["trader_tax"]
                    self.trader_df[i["tcode"]]["system_tax"]    += i["system_tax"]
                    self.trader_df[i["tcode"]]["stamp_tax"]     += i["stamp_tax"]
                    self.trader_df[i["tcode"]]["sh_tax"]        += i["sh_tax"]
                    self.trader_df[i["tcode"]]["profit_land"]   += i["profit_land"]
                    self.trader_df[i["tcode"]]["profit_float"]  += i["profit_float"]
                # update system_df
                self.system_df["trader_tax"]    += i["trader_tax"]
                self.system_df["system_tax"]    += i["system_tax"]
                self.system_df["stamp_tax"]     += i["stamp_tax"]
                self.system_df["sh_tax"]        += i["sh_tax"]
                self.system_df["profit_land"]   += i["profit_land"]
                self.system_df["profit_float"]  += i["profit_float"]
            for key in self.trader_df:
                self.trader_df[key]["tnp"] = self.trader_df[key]["profit_land"]\
                        - self.trader_df[key]["trader_tax"]\
                        - self.trader_df[key]["stamp_tax"]\
                        - self.trader_df[key]["sh_tax"]
            self.system_df["snp"] = self.system_df["profit_land"]\
                    - self.system_df["system_tax"]\
                    - self.system_df["stamp_tax"]\
                    - self.system_df["sh_tax"]
            #print(self.trader_df)
            #print(self.system_df)
            self.detail_df_dirty = False
        else:
            return

    def get_detail_df(self):
        if self.result_df_dirty:
            self.update_result_df()
        return self.detail_df

    def get_unbalanced_df(self):
        if self.result_df_dirty:
            self.update_result_df()
        return self.unbalanced_df

    def get_trader_df(self):
        if self.result_df_dirty:
            self.update_result_df()
        return self.trader_df

    def get_system_df(self):
        if self.result_df_dirty:
            self.update_result_df()
        return self.system_df


if __name__ == "__main__":
    trades = [
            (1000, 10.2),
            (-1000, 10.4),
            (100, 10),
            (-120, 10),
            ]
    price = 12
    calc = Calculator()
    calc.compute(trades, price)
    print(calc.profit_land)
    print(calc.profit_float)
    assert(abs(calc.profit_land - 200.0) < 0.01)
    assert(abs(calc.profit_float - -40.0) < 0.01)


