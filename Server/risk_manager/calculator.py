# -*- coding: utf-8 -*-

from collections import deque, defaultdict


class Dealer:
    def __init__(self, dcode, dname, dloss):
        self.dcode = dcode
        self.dname = dname
        self.dloss = dloss

    def __str__(self):
        return "[{}|{}|{}]".format(self.dcode, self.dname, self.dloss)


class Security:
    def __init__(self, scode, sname, recent_price):
        self.scode = scode
        self.sname = sname
        self.recent_price = recent_price

    def __str__(self):
        return "[{}|{}|{}]".format(self.scode, self.sname, self.recent_price)


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

    def __str__(self):
        return "t=%s,s=%s,v=%s,p=%s,d=%s" % (self.tcode, self.scode, self.vol, self.price, self.direct)

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
        self.deque_b = deque()
        self.deque_s = deque()
        self.paired_vol = 0
        self.profit_land = 0.0
        self.trader_cost = 0.0
        self.system_cost = 0.0
        self.remain_amt = 0.0
        self.remain_vol = 0.0
        self.profit_float = 0.0
        self.price_current = 0
        self.total_b = 0
        self.total_s = 0

    def update_profit_float(self):
        """
        p = 0.0
        for trade in self.deque_b:
            p += (self.price_current - trade.price) * trade.vol
        for trade in self.deque_s:
            p += (trade.price - self.price_current) * trade.vol
        self.profit_float = p
        """
        pass

    def set_price_current(self, price_current):
        """ Update RemainAmt and RemainVol """
        """ Update FloatProfit """
        """ Update CurrentPrice """
        #self.update_profit_float()
        p = 0.0
        remain_amt = 0.0
        remain_vol = 0
        for trade in self.deque_b:
            p += (price_current - trade.price) * trade.vol
            remain_amt += trade.price * trade.vol
            remain_vol += trade.vol
        for trade in self.deque_s:
            p += (trade.price - price_current) * trade.vol
            remain_amt += trade.price * trade.vol
            remain_vol -= trade.vol
        self.profit_float = p
        self.remain_amt = remain_amt
        self.remain_vol = remain_vol
        self.price_current = price_current

    def add(self, trade):
        """ Update TradeCostAmt """
        trader_cost = trade.trader_tax + trade.stamp_tax + trade.sh_tax
        system_cost = trade.system_tax + trade.stamp_tax + trade.sh_tax
        self.trader_cost += trader_cost
        self.system_cost += system_cost
        """ Update RemainTradeRecordList """
        if trade.direct == -1:
            self.deque_s.append(trade)
            self.total_s += trade.vol
        elif trade.direct == 1:
            self.deque_b.append(trade)
            self.total_b += trade.vol
        else:
            raise Exception("Not Expect Branch")
        while len(self.deque_b) > 0 and len(self.deque_s) > 0:
            b_trade = self.deque_b.popleft()
            s_trade = self.deque_s.popleft()
            delta_price = s_trade.price - b_trade.price
            volumn = min(b_trade.vol, s_trade.vol)
            """ Update PairedVol """
            self.paired_vol += volumn
            """ Update LandProfit """
            self.profit_land += delta_price * volumn
            if b_trade.vol > s_trade.vol:
                r_trade = Trade(b_trade.vol-s_trade.vol, b_trade.price, 1)
                self.deque_b.appendleft(r_trade)
            elif b_trade.vol < s_trade.vol:
                r_trade = Trade(s_trade.vol-b_trade.vol, s_trade.price, -1)
                self.deque_s.appendleft(r_trade)
        """ Update RemainAmt and RemainVol """
        """ Update FloatProfit """
        """ Update CurrentPrice """
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

    def clean_trade(self):
        self.calculators = defaultdict(Calculator)
        self.trades_df = defaultdict(list)
        self.trades_df_dirty = True

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
            self.result_df_dirty = False
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


class RiskControlUtil:

    @staticmethod
    def make_big_matrix(ta, hq_dt):
        big_dt = []
        for key in ta.calculators.keys():
            tcode, scode = key
            ele = dict()
            ele["tcode"] = tcode
            ele["scode"] = scode
            ele["tname"] = ta.traders_name[tcode]
            ele["tloss"] = ta.traders_loss[tcode]
            ele["sname"] = hq_dt[scode]["sname"]
            ele["sprice"] = hq_dt[scode]["recent_price"]
            ele["total_b"] = ta.calculators[key].total_b
            ele["total_s"] = ta.calculators[key].total_s
            ele["unbalanced"] = abs(ele["total_b"] - ele["total_s"])
            if ele["total_b"] == ele["total_s"]:
                ele["direct"] = "close"
            else:
                ele["direct"] = "long" if ele["total_b"] > ele["total_s"] else "short"
            ele["profit_float"] = ta.calculators[key].profit_float
            ele["profit_land"] = ta.calculators[key].profit_land
            big_dt.append(ele)
        return big_dt

    @staticmethod
    def make_system_matrix(system_dt):
        return system_dt

    @staticmethod
    def make_trader_matrix(trader_dt, trader_info):
        result = list()
        for t in trader_info.keys():
            dt = dict()
            dt["tname"] = trader_info[t][0]
            dt["loss"] = trader_info[t][1]
            try:
                dt["np"] = trader_dt[t]["tnp"]
            except:
                dt["np"] = 0.0
            result.append(dt)
        return result

    @staticmethod
    def make_unbalanced_matrix(unbalanced_dt, trader_info, scode_info):
        pass

    @staticmethod
    def make_detail_matrix(detail_dt, trader_info, scode_info):
        pass

    @staticmethod
    def make_analyz_matrix(detail_dt, hold_dt, hq_dt):
        raise Exception("Not Emplymented.")


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


