import logging
from common_server.share_module import TuShare
from common_server.timer import timeit
from risk_manager.reader import Reader
import pandas as pd
import numpy as np
import traceback as tb
from risk_manager.calculator import Calculator
from copy import deepcopy

ts = None

class RiskManager(object):
    def __init__(self, mid_dir, log_dir, final_csv_file, mid_csv_file, names_to_account, name, trader_tax_rate=0.0003, stamp_tax_rate=0.001) -> None:
        self.tushare = TuShare()
        self.import_package()
        self.logger = logging.getLogger()
        self.names_to_account = names_to_account
        self.name = name
        self.reader = Reader(mid_dir, log_dir, mid_csv_file, final_csv_file, names_to_account)
        self.has_data = self.reader.has_data
        self.mid_csv_file = self.reader.final_csv_file

        self.trade_cost = trader_tax_rate
        self.yhs_cost = stamp_tax_rate

        # renew by renew_humans
        self.humans = []            #账户列表
        self.names_dic = {}         #账户与人名的对应关系
        self.loss = {}              #账户与警戒位的对应关系
        # renew by provide_data
        self.data = None            #当日股票成交记录
        self.dic = {}               #人与管理股票列表
        self.stack_stock = None     #股票当日库存状态列表
        self.lingtougu_flag = True  #是否显示零头股
        self.temp_data = None
        self.status = None

        self.renew_humans()
        self.renew_status()

    def import_package(self):
        global ts
        import tushare as ts

    def renew_humans(self):
        '''
        --------
            更新名单
        --------
        '''
        if not self.has_data:
            return
        names_df = pd.read_excel(self.names_to_account)
        self.humans = []
        self.names_dic = {}
        self.loss = {}
        for idx, row in names_df.iterrows():
            account = row['Account']
            stop = row['Stop']
            try:
                account = int(account)
            except:
                self.logger.warning("[%s]Account[%s] cast to int failed!" % (idx, account))
                continue
            try:
                stop = int(stop)
            except:
                self.logger.warning("[%s]Stop[%s] cast to int failed!" % (idx, stop))
                stop = 5000
            name = str(row['Names']).strip()
            if name=='None' or name=='':
                self.logger.warning("Name at idx[%s] is empty" % idx)
                continue
            # self.logger.debug("(Account, Name, Stop): (%d, %s, %d) at %s" % (account, name, stop, idx))
            self.humans.append(account)
            self.names_dic[account] = name
            self.loss[account] = stop

    def __is_float(self, _s):
        '''
        --------
        首先把 _s 转换为 str ，然后尝试转换为 float ，如果成功返回 True ，
        否则返回 False 。
        主要用在 list comprehension 中
        --------
        '''
        try:
            float(str(_s))
            return True
        except:
            return False

    def provide_data(self):
        '''
        --------
            获取当日的委托明细
            委托可以由多个文件组成
        --------
        '''
        # TODO: 这里cols有问题
        cols = ['投顾编号', '证券代码', '证券名称', '委托时间', '操作', '成交均价', '成交数量', '状态']
        #获取文件内容
        data = pd.read_csv(self.mid_csv_file, encoding="gb2312")
        data = data[cols]
        # 删除投顾编号不为 float 类型的委托
        loc = [self.__is_float(str(i)) for i in data['投顾编号'].values]
        data = data.loc[loc, :]
        #删除投顾编号不在 humans 列表中的委托
        loc = [int(float(i)) in self.humans for i in data['投顾编号'].values]
        data = data.loc[loc, :]
        #删除成交数量为0的委托
        #del_row = np.isnan(data.loc[:, '成交数量'])
        #data = data.loc[-del_row, :]
        loc = [str(int(i)).isdigit() and int(i) != 0 for i in data['成交数量'].values]
        data = data.loc[loc, :]
        #del_row = np.array([i==0 for i in data['成交数量'].values])
        #data = data.loc[-del_row, :]
        save_row = data.loc[:, '成交数量'].values != 0
        data = data.loc[save_row, :]
        #过滤除买入卖出以外的操作
        loc = np.logical_or(data['操作'].values=='买入', data['操作'].values=='卖出')
        data = data.loc[loc, :]
        #data['证券代码'] = [str(int(i)).zfill(6) for i in data['证券代码'].values]
        data.columns = ['Human', 'Code', 'Name', 'Time', 'Flag', 'Price', 'Volumn', 'Status']
        return data

    def renew_stock_status(self):
        '''
        --------
            获取当前股票仓位情况
        --------
        '''
        data = self.data
        self.stack_stock = {}
        self.dic = {}
        for human, subDf in self.data.groupby('Human'):
            self.stack_stock[human] = []
            self.dic[human] = []
            for scode, subSubDf in subDf.groupby('Code'):
                #self.stock.append(scode)
                res = self.recognition(subSubDf)
                self.dic[human].append(scode)
                self.stack_stock[human].append(res)
            self.stack_stock[human] = np.array(self.stack_stock[human])
        #for Human in self.humans:
        #    stack_stock[Human] = []
        #    for code in self.dic[Human]:
        #        #选出该交易员交易该股票的委托, 若为空则跳过
        #        loc1 = data['Code']==code
        #        loc2 = data['Human']==Human
        #        temp = data[loc1&loc2]
        #        if len(temp) == 0:
        #            continue
        #        #计算仓位是否已平，若未平则返回值内包含未平部分平均成本价
        #        res = self.recognition(temp)
        #        stack_stock[Human].append(res)
        #    stack_stock[Human] = np.array(stack_stock[Human])

    def get_current_status(self):
        '''
        --------
            获取当前股票未平仓位浮动盈亏
        --------
        '''
        if not self.has_data:
            return
        res = []
        #获取未平仓位部分的证券代码
        current_codes = []
        for Human in self.stack_stock.keys():
            status = self.stack_stock[Human]
            if len(status) == 0:
                continue
            loc = status[:, 2] != 'balanced'
            status = status[loc, :]
            codes = [str(int(float(i))).zfill(6) for i in status[:, 0].tolist()]
            current_codes.extend(codes)
        current_codes = np.unique(current_codes).tolist()

        #如果没有未平仓位，则返回
        if len(current_codes) == 0:
            return []

        #获取未平仓位实时行情
        # 这里能不能改成异步的
        success, data = self.tushare.getRealTimeQuotes(current_codes)
        if not success:
            self.logger.debug("cannot get real time quotes")
            if self.temp_data is not None:
                data = self.temp_data
            else:
                return []
        else:
            self.temp_data = deepcopy(data)
        # data = ts.get_realtime_quotes(current_codes)
        temp = np.array(data['price'].values, dtype = float)
        loc = temp == 0
        temp[loc] = np.array(data['pre_close'].values, dtype = float)[loc]*1
        data['price'] = temp
        data = data[['code', 'price', 'name']]
        data.index = data['code']

        #获取未平仓位部分浮动盈亏
        for Human in self.stack_stock.keys():
            status = self.stack_stock[Human]
            if len(status) == 0:
                continue
            loc = status[:, 2] != 'balanced'
            status = status[loc, :]
            codes = [str(int(float(i))).zfill(6) for i in status[:, 0].tolist()]
            loc = []
            for i in data.index:
                if i in codes:
                    loc.append(i)
            df = data.loc[loc, :].values

            #获取浮动盈亏
            #数据结构为[仓位方向，交易员，证券代码，证券名称，成本价，现价，仓位数量，当前仓位利润率]
            for i in range(len(status)):
                if status[i, 2] == 'buy':
                    res.append(['long', self.names_dic[Human], status[i, 0], df[i, 2], status[i, 1], df[i, 1], status[i, 3],\
                    (float(df[i, 1])-float(status[i, 1]))/float(status[i, 1])])
                if status[i, 2] == 'sell':
                    res.append(['short', self.names_dic[Human], status[i, 0], df[i, 2], status[i, 1], df[i, 1], status[i, 3],\
                    -(float(df[i, 1])-float(status[i, 1]))/float(status[i, 1])])
        return res

    def renew_status(self):
        '''
        --------
            更新委托文件数据
        --------
        '''
        self.reader.run()
        self.has_data = self.reader.has_data
        if not self.has_data:
            return
        self.renew_humans()

        self.data = self.provide_data()

        self.renew_stock_status()

    def get_current_status2(self):
        '''
        --------
            获取当前盈亏情况
        --------
        '''
        #printrows = ''
        if not self.has_data:
            return
        res = self.get_current_status()
        temp = np.array(res)
        res_status = []
        try:
            a, b, c, d = temp[:, 4], temp[:, 6], temp[:, 7], temp[:, 5]
            a = np.array(a, dtype=float)  # 成本价
            b = np.array(b, dtype=float)  # 仓位
            c = np.array(c, dtype=float)  # 收益率
            d = np.array(d, dtype=float)  # 现价
            kuisun = np.array(a*b*c, dtype=int)
            #status数据结构[仓位方向，交易员，证券代码，证券名称，浮动盈亏，状态，持仓市值]
            status = np.column_stack((temp[:, :4], kuisun)).tolist()

            loc = 0
            for i in status:
                loss = float(i[4]) #获取浮动盈亏

                #增加仓位以及收益率
                i.append(int(b[loc]))
                i.append(str(int(c[loc] * 10000) / 100) + '%')

                #判断是否爆仓
                i.append(' ')
                if loss<(-100):
                    i[-1] = '*'
                if loss<(-500):
                    i[-1] = '**'
                if loss<(-1000):
                    i[-1] = '***'
                i.append(int(b[loc] * d[loc]) // 10000)  # 持仓市值
                #判断是否跳过零头股显示
                # 服务端不跳过，交给客户端判断
                # if not self.lingtougu_flag and b[loc] < 100:
                #     loc += 1
                #     continue
                loc += 1
                res_status.append(i)
                #printrows += str(i) + '\n'
        except Exception as e:
            if len(temp) == 0:
                self.logger.info(f"未获取到股票交易信息，请检查[{self.name}]是否正确配置")
                self.logger.debug(f"stocks:{self.stack_stock}")
                self.logger.debug(f"data:{self.data}")
            self.logger.error(tb.format_exc())
            #printrows += 'no stock\n'
            res_status = ['no stock']
        #printrows += '-------------------------------------------------------------\n'
        #输出仓位情况
        if len(res_status) == 0:
            res_status = ['no stock']
        try:
            temp_df = pd.DataFrame(res_status)
            temp_df.to_csv('stocks.csv', index = False)
        except Exception as e:
            self.logger.warning(tb.format_exc())
            #print(e)
        #获取总统计
        res = self.total(res)
        profits = np.array(res)
        total_deal = 0
        #print(res)
        if len(res) == 0:
            total = 0
        else:
            total = np.sum(np.array(profits[:, 1], dtype=float))

        #判断是否停机
        for i in res:

            name = i[0]
            account_id = 0
            for key in self.names_dic.keys():
                if self.names_dic[key] == name:
                    account_id = int(key)
                    break
            #如果没有停机位数据，则以1000, 3000, 5000代替
            if account_id in self.loss.keys():
                tmp_loss = self.loss[account_id]
                self.loss[name] = [tmp_loss / 3, tmp_loss * 4 / 5, tmp_loss]
                #logging.info("找到了[%s,%s]的 stop 的配置！" % (account_id, name))
            else:
                #logging.warning("没有找到[%s,%s]的 stop 的配置！" % (account_id, name))
                self.loss[name] = [1000, 3000, 5000]
            i.insert(len(i) - 1, self.loss[i[0]][2])  # 市值在最后一列
            i.insert(len(i) - 1, ' ')
            if i[1]<self.loss[i[0]][0]*(-1):
                i[-2] = '*'
            if i[1]<self.loss[i[0]][1]*(-1):
                i[-2] = '**'
            if i[1]<self.loss[i[0]][2]*(-1):
                i[-2] = '***'
            i[2], i[3] = i[3], i[2]
            total_deal += i[3]
            #printrows += str(i) + '\n'
        #printrows += str(['总计', total]) + '\n'
        res.append(['总计', int(total), ' ', int(total_deal)])

        #判断是否打印
        #if printable:
        #    os.system('cls')
        #    print(printrows)
        #    return

        #返回浮动盈亏状况以及盈亏状况
        #return printrows, res, res_status
        self.status = {'main': res, 'detail': res_status}
        return {'main': res, 'detail': res_status}

    def get_current_status3(self):
        detail_list = []
        trader_list = []
        current_codes = list(self.data["Code"].unique())
        current_codes = [str(int(x)).zfill(6) for x in current_codes]

        #获取实时行情
        data = ts.get_realtime_quotes(current_codes)
        temp = np.array(data['price'].values, dtype = float)
        loc = temp == 0
        temp[loc] = np.array(data['pre_close'].values, dtype = float)[loc]*1
        data['price'] = temp
        data = data[['code', 'price', 'name']]
        data.index = data['code']

        for human, subDf in self.data.groupby('Human'):
            profit_l = 0.0
            profit_f = 0.0
            try:
                humanName = self.names_dic[human]
            except:
                humanName = human
            for scode, subSubDf in subDf.groupby('Code'):
                scode = str(int(scode)).zfill(6)

                #判断是否需要经手费
                if scode >= '600000':
                    trade_cost = self.trade_cost + 0.00002
                else:
                    trade_cost = self.trade_cost * 1

                try:
                    close_p = data[scode]["price"].values
                except:
                    close_p = 0
                calc, cost_total, cost_float = self.recognition2(subSubDf, close_p, trade_cost)
                volumn = 0
                amount = 0.0
                for trade in calc.deque_b:
                    volumn += trade.vol
                    amount += trade.vol * trade.price
                for trade in calc.deque_s:
                    volumn += trade.vol
                    amount += trade.vol * trade.price
                if volumn == 0:
                    average_price = 0
                else:
                    average_price = amount / volumn
                detail = [human, humanName, scode, volumn, amount, average_price,
                        close_p, calc.profit_land, calc.profit_float, cost_total, cost_float, calc.profit_land-cost_total]
                detail_list.append(detail)
                profit_l += calc.profit_land - cost_total
                profit_f += calc.profit_float
            trader_list.append([humanName, profit_l, profit_f])
        return trader_list, detail_list

    def recognition2(self, df, close_p, trade_cost):
        hlen = len(df)
        vol = df['Volumn'].values #成交数量
        flag = df['Flag'].values #委托方向
        price = df['Price'].values #成交价格
        trades = []
        cost_total = 0.0
        for i in range(hlen):
            v = vol[i]
            p = price[i]
            cost = p * abs(v) * trade_cost
            if cost < 5.0:
                cost = 5.0
            if flag[i] == '买入':
                trades.append((v, p))
                cost_yhs = 0
            else:
                trades.append((0-v,p))
                cost_yhs = p * abs(v) * self.yhs_cost
            cost_total += cost + cost_yhs
        cal = Calculator()
        cal.compute(trades, close_p)

        cost_float = 0.0
        for trade in cal.deque_b:
            cost_float += trade.vol * trade.price * trade_cost
        for trade in cal.deque_s:
            cost_float += (0-trade.vol) * trade.price * (trade_cost + self.yhs_cost)

        return cal, cost_total, cost_float


    def recognition(self, df):
        '''
        --------
            获取当前股票的仓位详细状况
        --------
        '''

        #初始化变量
        cum_vol_buy = 0 #累计买量
        cum_vol_sell = 0 #累计卖量
        cum_price_buy = 0 #平均买入价格
        cum_price_sell = 0 #平均卖出价格
        cum_flag = 0 #仓位方向 0表示已平，1表示多头，-1表示空头
        hlen = len(df) #委托数量
        flag = df['Flag'].values #委托方向
        vol = df['Volumn'].values #成交数量
        price = df['Price'].values #成交价格

        #遍历委托
        for i in range(hlen):
            #记录累计成交量
            if flag[i] == '买入':
                cum_vol_buy += vol[i]
            else:
                cum_vol_sell += vol[i]

            #判断当前仓位状况
            pre_cum_flag = cum_flag
            if cum_vol_buy > cum_vol_sell:
                cum_flag = 1
            elif cum_vol_buy < cum_vol_sell:
                cum_flag = -1
            else:
                cum_flag = 0

            #如果交易方向发生变化（空变多以及多变空）
            if cum_flag*pre_cum_flag == -1:
                #记录成交差额
                diff = np.abs(cum_vol_buy - cum_vol_sell)
                #更新成本价以及数量等
                if cum_flag == 1:
                    cum_price_buy = price[i]
                    cum_price_sell = 0
                    cum_vol_buy = diff
                    cum_vol_sell = 0
                else:
                    cum_price_buy = 0
                    cum_price_sell = price[i]
                    cum_vol_buy = 0
                    cum_vol_sell = diff
                #跳过判断平仓以及更新成本价步骤
                continue

            #判断是否平仓
            if cum_flag == 0:
                #更新成本价以及数量等
                cum_vol_buy = 0
                cum_vol_sell = 0
                cum_price_buy = 0
                cum_price_sell = 0
                continue

            #更新成本价
            if flag[i] == '买入':
                cum_price_buy = (cum_price_buy*(cum_vol_buy - vol[i]) + price[i]*vol[i])/cum_vol_buy
            else:
                cum_price_sell = (cum_price_sell*(cum_vol_sell - vol[i]) + price[i]*vol[i])/cum_vol_sell

        #更新最终股票敞口状况
        #cum_vol = np.abs(cum_vol_buy - cum_vol_sell)

        #更新股票持仓情况
        if cum_flag == 0:
            res = [df['Code'].values[0], '0', 'balanced', '0']
        elif cum_flag == 1:
            assert cum_price_buy > 0
            assert cum_vol_buy > cum_vol_sell
            #标准算法成本价
            #price_buy = (cum_price_buy*cum_vol_buy - cum_price_sell*cum_vol_sell)/(cum_vol_buy - cum_vol_sell)
            #金牛日内算法成本价
            price_buy = cum_price_buy
            res = [df['Code'].values[0], price_buy, 'buy', cum_vol_buy - cum_vol_sell]
        elif cum_flag == -1:
            assert cum_price_sell > 0
            assert cum_vol_sell > cum_vol_buy
            #标准算法成本价
            #price_sell = (cum_price_buy*cum_vol_buy - cum_price_sell*cum_vol_sell)/(cum_vol_buy - cum_vol_sell)
            #金牛日内算法成本价
            price_sell = cum_price_sell
            res = [df['Code'].values[0], price_sell, 'sell', cum_vol_sell - cum_vol_buy]

        return res

    def total(self, res):
        '''
        --------
            获取当前交易员累计盈亏
            为方便起见，以当前未平的仓位具体状况作为输入
        --------
        '''
        data = self.data
        profits = []
        for Human in self.stack_stock.keys():
            profit = 0 #累计盈亏
            vol = 0 #累计成交量
            money = 0 #累计成交额
            unbalanced = 0 # 未平仓位市值
            for code in self.dic[Human]:
                #统计委托
                loc1 = data['Code']==code
                loc2 = data['Human']==Human
                temp = data[loc1&loc2]
                if len(temp) == 0:
                    continue
                loc1 = temp['Flag'].values == '买入'
                loc2 = temp['Flag'].values == '卖出'

                #获取买入价格数量
                if loc1.any():
                    buy_price = temp.loc[loc1, 'Price'].values
                    buy_vol = temp.loc[loc1, 'Volumn'].values
                    buy_status = np.repeat(0, len(buy_vol))
                    bs_loc = temp.loc[loc1, 'Status'].values != '隔夜仓'
                    buy_status[bs_loc] = 1
                else:
                    buy_price = np.array([0])
                    buy_vol = np.array([0])
                    buy_status = np.array([1])

                #获取卖出价格数量
                if loc2.any():
                    sell_price = temp.loc[loc2, 'Price'].values
                    sell_vol = temp.loc[loc2, 'Volumn'].values
                    sell_status = np.repeat(0, len(sell_vol))
                    ss_loc = temp.loc[loc2, 'Status'].values != '隔夜仓'
                    sell_status[ss_loc] = 1
                else:
                    sell_price = np.array([0])
                    sell_vol = np.array([0])
                    sell_status = np.array([1])

                #判断是否需要经手费
                code = str(code).zfill(6)
                if code >= '600000':
                    trade_cost = self.trade_cost + 0.00002
                else:
                    trade_cost = self.trade_cost * 1

                #计算交易费用
                sell_cost = sell_price*sell_vol*(trade_cost + self.yhs_cost)*sell_status
                buy_cost = buy_price*buy_vol*trade_cost

                if type(sell_cost) == np.ndarray:
                    sell_cost[(sell_cost<5)&(sell_cost!=0)] = 5
                else:
                    if sell_cost < 5 and sell_cost != 0:
                        sell_cost = 5
                sell_cost = np.round(np.sum(sell_cost), 2)

                if type(buy_cost) == np.ndarray:
                    buy_cost[(buy_cost<5)&(buy_cost!=0)] = 5
                else:
                    if buy_cost < 5 and buy_cost != 0:
                        buy_cost = 5
                buy_cost = np.round(np.sum(buy_cost), 2)

                profit = profit + np.sum(sell_price*sell_vol) - np.sum(buy_price*buy_vol) -\
                        sell_cost - buy_cost

                #判断该股票是否有未平仓位
                for i in res:
                    if str(i[2]).zfill(6) == code and i[1] == self.names_dic[Human]:
                        unbalanced += float(i[5])*float(i[6])
                        if i[0] == 'long':
                            profit = profit + float(i[5])*float(i[6])
                        else:
                            profit = profit - float(i[5])*float(i[6])

                #更新成交数量以及成交额
                vol = vol + np.sum(buy_vol) + np.sum(sell_vol)
                money = money + np.sum(sell_price*sell_vol) + np.sum(buy_price*buy_vol)

            profits.append([self.names_dic[Human], int(profit), int(money // 10000), int(unbalanced // 10000)])
        return profits
