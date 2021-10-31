# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
#import tushare as ts
from collections import deque


def algorithm_1(df):
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
        res = [df['Code'].values[0],'0','balanced','0']
    elif cum_flag == 1:
        assert cum_price_buy > 0
        assert cum_vol_buy > cum_vol_sell
        #标准算法成本价
        #price_buy = (cum_price_buy*cum_vol_buy - cum_price_sell*cum_vol_sell)/(cum_vol_buy - cum_vol_sell)
        #金牛日内算法成本价
        price_buy = cum_price_buy
        res = [df['Code'].values[0],price_buy,'buy',cum_vol_buy - cum_vol_sell]
    elif cum_flag == -1:
        assert cum_price_sell > 0
        assert cum_vol_sell > cum_vol_buy
        #标准算法成本价
        #price_sell = (cum_price_buy*cum_vol_buy - cum_price_sell*cum_vol_sell)/(cum_vol_buy - cum_vol_sell)
        #金牛日内算法成本价
        price_sell = cum_price_sell
        res = [df['Code'].values[0],price_sell,'sell',cum_vol_sell - cum_vol_buy]

    return res


def algorithm_2(df, current_price=0.0):
    buy_pair_list = deque()
    sell_pair_list = deque()
    profit = 0.0
    float_profit = 0.0

    for idx, row in df.iterrows():
        vol = row['Volumn']
        flag = row['Flag']
        price = row['Price']
        if flag == '买入':
            buy_pair_list.append((price, vol))
        else:
            sell_pair_list.append((price, vol))

    while (len(buy_pair_list)!=0) and (len(sell_pair_list)!=0):
        buy_price, buy_vol = buy_pair_list.popleft()
        sell_price, sell_vol = sell_pair_list.popleft()
        if buy_vol < sell_vol:
            profit = buy_vol * (sell_price - buy_price)
            sell_pair_list.appendleft( (sell_price, sell_vol - buy_vol) )
        elif buy_vol > sell_vol:
            profit = sell_vol * (sell_price - buy_price)
            buy_pair_list.appendleft( (buy_price, buy_vol - sell_vol) )
        else:
            profit = buy_vol * (sell_price - buy_price)

    if len(buy_pair_list) != 0:
        for price, vol in buy_pair_list:
            float_profit += vol * (current_price - price)
        res = ('buy', list(buy_pair_list), profit, float_profit)
    elif len(sell_pair_list) != 0:
        for price, vol in sell_pair_list:
            float_profit += vol * (price - current_price)
        res = ('sell', list(sell_pair_list), profit, float_profit)
    else:
        res = ('balanced', [], profit, float_profit)
    return res


def main():
    df = pd.read_csv('algorithm.csv', encoding='gb2312')
    for code, subDf in df.groupby('Code'):
        #result1 = algorithm_1(subDf)
        #print(result1)
        result2 = algorithm_2(subDf)
        if result2[0] != 'balanced':
            print(result2)
        #break


if __name__ == '__main__':
    main()


