# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import codecs
import logging
import datetime
import configparser

import numpy as np
import pandas as pd
import tushare as ts

#reload(sys)
#sys.setdefaultencoding('utf8')

__VERSION__ = "1.1.0"
TRADER_TAX_RATE = 0.0003
SYSTEM_TAX_RATE = 0.00011
STAMP_TAX_RATE = 0.001
BROKER_TAX_RATE = 0.00002

TODAY = time.strftime('%Y%m%d',time.localtime(time.time()))

logging.basicConfig(level=logging.DEBUG,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                datefmt='%a, %d %b %Y %H:%M:%S',
                filename='log/calculator_%s.log'%TODAY,
                filemode='a')

console = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
console.setFormatter(formatter)
console.setLevel(logging.INFO)

logging.getLogger('').addHandler(console)

TRADER_CODE_2_NAME = {}
for idx, row in pd.read_excel(u'conf/names_to_account.xlsx', encoding="gb2312").iterrows():
    TRADER_CODE_2_NAME[str(int(row[u'Account'])).zfill(8)] = row[u'Names']


def core_compute(df, stock_exchange, suggest_price=None):
    print("In core compute, %d" % TRADER_TAX_RATE)
    vol = 0
    price = 0.0
    money = 0.0
    trader_profit = 0.0
    system_profit = 0.0
    trader_tax = 0.0
    system_tax = 0.0
    stamp_tax = 0.0
    broker_tax = 0.0
    for idx, row in df.iterrows():
        tPrice = float(row['price'])
        tVolumn = int(row['vol']) * int(row['posit'])
        vol += tVolumn
        price = tPrice
        money -= tPrice * tVolumn
        trader_tax += abs(TRADER_TAX_RATE * tPrice * tVolumn)
        system_tax += abs(SYSTEM_TAX_RATE * tPrice * tVolumn)
        if stock_exchange == 'sh':
            trader_tax += abs(BROKER_TAX_RATE * tPrice * tVolumn)
            system_tax += abs(BROKER_TAX_RATE * tPrice * tVolumn)
            broker_tax += abs(BROKER_TAX_RATE * tPrice * tVolumn)
        if tVolumn < 0:
            stamp_tax += abs(STAMP_TAX_RATE * tPrice * tVolumn)
    if type(suggest_price) == type(0.0) and suggest_price != 0.0:
        price = suggest_price
    money += vol * price
    trader_profit = money - trader_tax - stamp_tax
    system_profit = money - system_tax - stamp_tax
    return { 'vol': vol,
            'price': price,
            'trader_profit': trader_profit,
            'system_profit': system_profit,
            'trader_tax': trader_tax,
            'system_tax': system_tax,
            'stamp_tax': stamp_tax,
            'broker_tax': broker_tax
            }


def compute(df, init_legacy_df, auto_load_legacy=False):
    results = []

    dates = list(df['date'].unique())
    dates.sort()
    today_date = datetime.date.today().isoformat()
    start_date = dates[0]
    end_date = dates[-1]

    scodes = list(df['scode'].unique())

    legacy_df = pd.DataFrame({'time':[],'scode':[],'tcode':[],'price':[],'vol':[],'posit':[]}, index=[])
    if len(init_legacy_df) != 0:
        legacy_dates = list(init_legacy_df['date'].unique())
        legacy_dates.sort()
        legacy_date = legacy_dates[0]
        tmpCode = str(int(scodes[0])).zfill(6)
        hisDf = ts.get_k_data(tmpCode, start=legacy_date, end=start_date)
        trade_dates = sorted(list(hisDf['date']), reverse=True)
        last_trade_day = ''
        for t_day in trade_dates:
            if t_day != start_date:
                last_trade_day = t_day
                break
        loc = init_legacy_df.loc[:, 'date'] == last_trade_day
        legacy_df = init_legacy_df.loc[loc, ['scode', 'tcode', 'price', 'vol', 'posit']]
        if len(legacy_df) != 0:
            legacy_df.loc[:, 'time'] = '09:00:00'
    else:
        print(u'[WARN] 输入的隔夜仓没有内容')

    StockCode2Name = {}
    priceDfs = pd.DataFrame({'code': [], 'date': [], 'close': []}, index=[])
    total_codes = list(set(scodes + list(legacy_df['scode'].unique())))
    scode_len = len(total_codes)
    for idx in range(scode_len):
        scode = total_codes[idx]
        scode = str(int(scode)).zfill(6)
        print(u'[INFO] (%3d/%d) %s' % (idx, scode_len, scode))
        nowDf = ts.get_realtime_quotes(scode)
        StockCode2Name[scode] = list(nowDf['name'])[0]
        nowDf.rename(columns = {'price': 'close'}, inplace=True)
        priceDfs = priceDfs.append(nowDf.loc[:, ['code', 'date', 'close']], ignore_index=True)
        hisDf = ts.get_k_data(scode, start=start_date, end=end_date)
        priceDfs = priceDfs.append(hisDf.loc[:, ['code', 'date', 'close']], ignore_index=True)

    idx = 0
    date_len = len(dates)
    for date in dates:
        idx += 1
        date = str(date)
        if len(date) == 8:
            date = date[:4] + '-' + date[4:6] + '-' + date[6:]
        assert(len(date)==10)

        loc = df.loc[:, 'date'] == date
        subDf = df.loc[loc, ['time', 'scode', 'tcode', 'vol', 'price', 'posit']]
        if auto_load_legacy:
            subDf = subDf.append(legacy_df, ignore_index=True)
            legacy_df = pd.DataFrame({'time':[],'scode':[],'tcode':[],'price':[],'vol':[],'posit':[]}, index=[])

        scodeNumber = len(subDf['scode'].unique())
        print(u'[INFO] (%2d/%d) 计算 %s 的委托，涉及到 %d 只股票。' % (idx, date_len, date, scodeNumber))
        iidx = 0
        for scode, subSubDf in subDf.groupby('scode'):
            iidx += 1
            scode = str(int(scode)).zfill(6)
            place = ''
            if scode[:2] == '60':
                #print(u"%s in Shanghai Stock Exchange" % scode)
                place = 'sh'
            sname = StockCode2Name[scode]
            loc = (priceDfs.loc[:, 'date'] == date) & (priceDfs.loc[:, 'code'] == scode)
            price = list(priceDfs.loc[loc, :]['close'])[0]
            for tcode, subSubSubDf in subSubDf.groupby('tcode'):
                tcode = str(int(tcode)).zfill(8)
                try:
                    tname = TRADER_CODE_2_NAME[tcode]
                except:
                    print(u"[WARN] %s do not exists" % tcode)
                    tname = tcode
                subSubSubDf = subSubSubDf.sort_values('time', axis=0)
                result = core_compute(subSubSubDf, place, price)
                result['date'] = date
                result['tcode'] = tcode
                result['tname'] = tname
                result['scode'] = scode
                result['sname'] = sname
                results.append(result)
                if auto_load_legacy and (result['vol'] >= 100 or result['vol'] <= -100):
                    leg = {}
                    leg['time'] = '09:00:00'
                    leg['tcode'] = tcode
                    leg['scode'] = scode
                    leg['vol'] = abs(result['vol'])
                    leg['price'] = result['price']
                    leg['posit'] = int( result['vol'] / abs(result['vol']) )
                    legacy_df = legacy_df.append(leg, ignore_index=True)
    return pd.DataFrame(results)


def get_legacy_df(results):
    loc = results['vol'].values != 0
    res = results.loc[loc, ['date','tcode','tname','scode','sname','price','vol']]
    res['posit'] = 1
    loc = res['vol'].values < 0
    res.loc[loc, ['posit']] = -1
    res.loc[loc, ['vol']] = -res.loc[loc, ['vol']]
    loc = res['vol'].values >= 100
    legacyDf = res.loc[loc, :]
    piecesDf = res.loc[~loc, :]
    head_cols = {'date': u'日期',
            'tcode': u'交易员编号',
            'tname': u'交易员姓名',
            'scode': u'股票代码',
            'sname': u'股票名称',
            'price': u'结算价',
            'vol': u'数量',
            'posit': u'多空'}
    legacyDf.rename(columns=head_cols, inplace=True)
    piecesDf.rename(columns=head_cols, inplace=True)
    return (legacyDf, piecesDf)


def get_profit_df(results):
    trader = []
    system = []
    for date, sub in results.groupby("date"):
        system_profit = sub['system_profit'].sum()
        sp = {'date': date, 'profit': system_profit}
        system.append(sp)
        for tcode, subDf in sub.groupby("tcode"):
            trader_profit = subDf['trader_profit'].sum()
            try:
                tname = TRADER_CODE_2_NAME[tcode]
            except:
                tname = tcode
            record = {'date':date,'tcode':tcode,'tname':tname,'profit':trader_profit}
            trader.append(record)
    t = pd.DataFrame(trader, columns=['date','tcode','tname','profit'])
    t.rename(columns={'date':u'日期','tcode':u'交易员编号','tname':u'交易员姓名','profit':u'盈亏'}, inplace=True)
    s = pd.DataFrame(system, columns=['date','profit'])
    s.rename(columns={'date':u'日期','profit':u'盈亏'}, inplace=True)
    return (t, s)


def main():
    cf = configparser.SafeConfigParser()
    with codecs.open("settings.ini", 'r', encoding="gb2312") as f:
        cf.readfp(f)
    TRADER_TAX_RATE = float(cf.get("tax", "trader_tax_rate"))
    SYSTEM_TAX_RATE = float(cf.get("tax", "system_tax_rate"))
    STAMP_TAX_RATE = float(cf.get("tax", "stamp_tax_rate"))
    print(TRADER_TAX_RATE)
    #convert = 'conf/HeadConvert.csv'
    #convertDf = pd.read_csv(convert, encoding="gb2312")
    convert = 'conf/HeadConvert.xls'
    convertDf = pd.read_excel(convert, encoding="gb2312")
    cols = {}
    sellFlag = ''
    buyFlag = ''
    for idx, row in convertDf.iterrows():
        if row['target'] == 'long':
            buyFlag = str(row['origin'])
        elif row['target'] == 'short':
            sellFlag = str(row['origin'])
        else:
            cols[row['origin']] = row['target']

    ipt = cf.get("excel", "input")
    print(u"[INFO] 获取输入文件：" + ipt)
    filename = ipt[:-4]
    df = pd.read_excel(ipt, encoding="gb2312")
    df = df.dropna(subset=[u'证券代码'])
    try:
        loc = df.loc[:, u'证券代码'] != u'混合'
        df = df.loc[loc, :]
    except:
        print(u"[INFO] 输入的证券代码没有中文")
    df.rename(columns = cols, inplace=True)
    df = df.loc[:, ['date', 'time', 'scode', 'tcode', 'price', 'vol', 'posit']]
    sellLoc = df.loc[:, 'posit'].values == sellFlag
    buyLoc = df.loc[:, 'posit'].values == buyFlag
    bothLoc = sellLoc | buyLoc
    df.loc[sellLoc, 'posit'] = -1
    df.loc[buyLoc, 'posit'] = 1
    df = df.loc[bothLoc, :]
    df = df.dropna(subset=['posit'])
    nonZeroLoc = df.loc[:, 'vol'].values != 0
    df = df.loc[nonZeroLoc, :]

    enable_legacy = int(cf.get("excel", "enable_legacy"))
    init_legacy_df = pd.DataFrame({'date':[],'tcode':[],'scode':[],'price':[],'vol':[],'posit':[]}, index=[])
    if enable_legacy:
        init_legacy = cf.get("excel", "init_legacy")
        if init_legacy[-4:] != ".xls":
            print(u"[INFO] 隔夜仓文件不是 Excel 2003-2007 的格式")
            print(u"[WARN] 忽略指定的隔夜仓文件")
        elif not os.path.exists(init_legacy):
            print(u"[INFO] 没找到指定的隔夜仓文件")
            print(u"[WARN] 忽略指定的隔夜仓文件")
        else:
            print(u"[INFO] 找到指定的隔夜仓文件")
            init_legacy_df = pd.read_excel(init_legacy, encoding="gb2312")
            tmp_cols = { u'日期': 'date',
                    u'交易员编号': 'tcode',
                    u'股票代码': 'scode',
                    u'结算价': 'price',
                    u'数量': 'vol',
                    u'多空': 'posit' }
            init_legacy_df.rename(columns=tmp_cols, inplace=True)

    auto_load_legacy = cf.get("excel", "auto_load_legacy")
    results = compute(df, init_legacy_df, auto_load_legacy)
    print(u'[INFO] 输出计算的详细结果')
    results.to_excel(u'%s-%s.xls' % (filename, 'detail'), encoding="gb2312")
    print(u'[INFO] 输出隔夜仓和零头股')
    (legacyDf, piecesDf) = get_legacy_df(results)
    legacyDf.to_excel(u'%s-%s.xls' % (filename, 'legacy'), encoding="gb2312")
    piecesDf.to_excel(u'%s-%s.xls' % (filename, 'pieces'), encoding="gb2312")
    print(u'[INFO] 输出系统收益和交易员收益')
    (traderProfitDf, systemProfitDf) = get_profit_df(results)
    traderProfitDf.to_excel(u'%s-%s.xls' % (filename, 'trader'), encoding="gb2312")
    systemProfitDf.to_excel(u'%s-%s.xls' % (filename, 'system'), encoding="gb2312")

    print(u"[INFO] 结算完成")


class Calculator:

    def __init__(self, rates, entrust, legacy, lingtougu, names):
        self.rates = rates
        self.entrust = pd.read_excel(entrust, encoding='gb2312')
        self.names = names
        if os.path.exists(legacy):
            self.legacy = pd.read_excel(legacy, encoding='gb2312')
        else:
            logging.warning(u"隔夜仓文件[%s]没有找到" % legacy)
            self.legacy = None
        if os.path.exists(lingtougu):
            self.lingtougu = pd.read_excel(lingtougu, encoding="gb2312")
        else:
            logging.warning(u"零头股文件[%s]没有找到" % lingtougu)
            self.lingtougu = None

    def recompute(self):
        pass

    def get_legacy_df(self):
        pass

    def get_lingtougu_df(self):
        pass

    def get_trader_profit(self):
        pass

    def get_system_profit(self):
        pass

    def get_detail_profit(self):
        pass


if __name__ == '__main__':
    if len(sys.argv) == 1:
        main()
    elif len(sys.argv) == 2:
        logging.info(u"开始结算。")
        cfgfile = sys.argv[1]
        if os.path.exists(cfgfile):
            logging.debug("Specified setting file[%s] found!" % cfgfile)
            cf = configparser.SafeConfigParser()
            with codecs.open(cfgfile, 'r', encoding="gb2312") as f:
                cf.readfp(f)
            trader_tax_rate = float(cf.get("tax", "trader_tax_rate"))
            system_tax_rate = float(cf.get("tax", "system_tax_rate"))
            stamp_tax_rate = float(cf.get("tax", "stamp_tax_rate"))
            rates = {}
            rates['trader'] = trader_tax_rate
            rates['system'] = system_tax_rate
            rates['stamp']  = stamp_tax_rate
            logging.debug("trader_tax_rate:%f, system_tax_rate:%f, stamp_tax_rate:%f" %
                    (trader_tax_rate, system_tax_rate, stamp_tax_rate))
            entrust_file = cf.get("input", "entrust")
            legacy_file = cf.get("legacy", "init_legacy_file")
            lingtougu_file = cf.get("lingtougu", "init_lingtougu_file")
            names_file = cf.get("names", "names_to_account")
            logging.debug("entrust:%s, legacy:%s, lingtougu:%s, names:%s" %
                    (entrust_file, legacy_file, lingtougu_file, names_file))
            if not os.path.exists(entrust_file):
                logging.error("Input entrust file[%s] NOT found!" % entrust_file)
                logging.error(u"请检查委托文件[%s]是否存在！" % entrust_file)
                raise
            if not os.path.exists(names_file):
                logging.error("Names to account file[%s] NOT found!" % names_file)
                logging.error(u"请检查交易员姓名配置文件[%s]是否存在！" % names_file)
                raise
            names_df = pd.read_excel(names_file, encoding="gb2312")
            print(names_df)
            names = {}
            for idx, row in names_df.iterrows():
                account = row['Account']
                name = row['Names']
            Cal = Calculator(rates, entrust_file, legacy_file, lingtougu_file, names)
            logging.info(u"结算正常结束。")
        else:
            logging.error("Specified setting file[%s] NOT found!" % cfgfile)
            logging.error("请检查配置文件[%s]是否存在！" % cfgfile)
            raise
    else:
        logging.error(u"请检查该程序运行方法是否有误")

