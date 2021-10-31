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

from collections import deque, OrderedDict

__VERSION__ = '2.3.2'

if not os.path.exists('log/'):
    os.mkdir('log/')

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


def time_me(fn):
    def _wrapper(*args, **kwargs):
        start = time.clock()
        val = fn(*args, **kwargs)
        logging.debug("Time consumed in %s: %s second" % (fn.__name__, time.clock() - start))
        return val
    return _wrapper


class Calculator:

    def __init__(self, r_f, l_f, p_f):
        self.record_file = r_f
        self.today = '%s-%s-%s' % (TODAY[:4], TODAY[4:6], TODAY[6:])
        self.record_df = pd.read_excel(r_f, encoding='gb2312')
        if len(self.record_df) == 0:
            logging.error(u"读入的成交文件[%s]没有数据！" % r_f)
            raise Exception('No Record In Record File[%s]!' % r_f)
        if l_f:
            self.legacy_df = pd.read_excel(l_f, encoding='gb2312')
        else:
            self.legacy_df = None
        if p_f:
            self.pieces_df = pd.read_excel(p_f, encoding='gb2312')
        else:
            self.pieces_df = None
        self.names_dic = {}

    def read_names(self, nm_excel_file):
        self.names_dic = {}
        df = pd.read_excel(nm_excel_file, encoding='gb2312')
        df.dropna()
        for idx, row in df.iterrows():
            try:
                account = int(row['Account'])
                name = str(row['Names'])
                self.names_dic[account] = name
            except:
                logging.warning(u"在读取交易员配置[%s]第[%s]行[%s]时出错！"
                        %(nm_excel_file, idx, row))
                continue

    def convert_head(self, head_convert_file):
        df = pd.read_excel(head_convert_file, encoding='gb2312')
        head_cols = {}
        long_str = ''
        short_str = ''
        for idx, row in df.iterrows():
            if row['target']=='long':
                long_str = row['origin']
            elif row['target']=='short':
                short_str = row['origin']
            else:
                head_cols[row['origin']] = row['target']
        self.record_df = self.record_df[list(head_cols.keys())]
        self.record_df.rename(columns=head_cols, inplace=True)
        long_loc = self.record_df['posit'] == long_str
        short_loc = self.record_df['posit'] == short_str
        self.record_df.loc[long_loc, 'posit'] = 1
        self.record_df.loc[short_loc, 'posit'] = -1
        loc = np.logical_or(long_loc, short_loc)
        self.record_df = self.record_df.loc[loc, :]

    def preprocess_record(self):
        self.record_df.loc[:, 'scode'] = [str(int(c)).zfill(6) for c in self.record_df['scode'] ]
        self.record_df.loc[:, 'tcode'] = [int(t) for t in self.record_df['tcode'] ]
        self.date = self.record_df['date'].unique()
        if len(self.date) == 1:
            self.date = self.date[0]
            self.is_today = self.today == self.date
        else:
            logging.error(u"委托记录存在不止一个日期[%s]" % self.date)
            raise Exception('Not Only One Date!')
        account_list = self.names_dic.keys()
        loc = [int(i) in account_list for i in self.record_df['tcode'].values]
        # tmp block start
        l = [int(i) not in account_list for i in self.record_df['tcode'].values]
        tmp_df = self.record_df.loc[l, :]
        accounts = tmp_df['tcode'].unique()
        accounts = ', '.join([str(i) for i in accounts])
        logging.warning(u'编号为[%s]交易员的成交记录被忽视！' % accounts)
        # tmp block end
        self.record_df = self.record_df.loc[loc, :]

    def read_close_price(self, excel_f, scode_head, price_head, sname_head):
        fp = open(excel_f, "r")
        lines = fp.readlines()

        head_line = lines.pop(0)
        head_row = head_line.strip().split("\t")
        head_row = [x.strip() for x in head_row]
        col_num = len(head_row)
        scode_idx, price_idx, sname_idx = -1, -1, -1
        for i in range(col_num):
            if head_row[i] == scode_head:
                scode_idx = i
            if head_row[i] == price_head:
                price_idx = i
            if head_row[i] == sname_head:
                sname_idx = i

        self.close_price = {}
        self.codes_dic = {}
        scodes = self.record_df['scode'].unique()
        total = len(scodes)
        index = 0
        for line in lines:
            row = line.strip().split("\t")
            row = [x.strip() for x in row]
            if len(row) == col_num:
                scode = row[scode_idx][2:]
                if scode in scodes:
                    index += 1
                    price = float(row[price_idx])
                    sname = row[sname_idx]
                    self.close_price[scode] = price
                    self.codes_dic[scode] = sname
                    logging.info(u"[%03d/%03d] 股票代码：[%s|%s] 收盘价：[%s]" % (index, total, scode, sname, price))
        logging.debug(u"close_price: %s" % self.close_price)
        logging.info(u"所有股票收盘价获取结束。")
        return True

    def fetch_close_price(self):
        logging.info(u"获取股票的收盘价。")

        _attempts = 0
        today_all_flag = False
        while self.is_today and _attempts < 3 and not today_all_flag:
            try:
                today_all_df = ts.get_today_all()
                today_all_flag = True
            except:
                _attempts += 1
                logging.warn(u"第 %d 次尝试 get_today_all 失败" % _attempts)
                time.sleep(0.5)
                if _attempts==3:
                    logging.warn(u"尝试 get_today_all %d次，均失败，请检查您的网络连接。" % _attempts)
                    break

        self.close_price = {}
        scodes = self.record_df['scode'].unique()
        total = len(scodes)
        for index, scode in enumerate(scodes):
            c_price = -1000

            if self.is_today and today_all_flag:
                i = today_all_df["code"] == scode
                row = today_all_df.loc[i, ["trade", "settlement"]]
                trade_p = row["trade"].values[0]
                close_p = row["settlement"].values[0]
                if trade_p:
                    c_price = trade_p
                    logging.info(u"今日收盘价：%s" % c_price)
                else:
                    c_price = close_p
                    logging.info(u"今日没有价格，使用昨日收盘价：%s" % c_price)
            elif self.is_today:
                _attempts = 0
                _success = False
                while _attempts < 3 and not _success:
                    try:
                        nowDf = ts.get_realtime_quotes(scode)
                        c_price = list(nowDf['price'])[0]
                    except:
                        _attempts += 1
                        logging.warn(u"第 %d 次尝试 get_realtime_quotes 失败" % _attempts)
                        time.sleep(0.5)
                        if _attempts==3:
                            logging.error(u"尝试 get_realtime_quotes %d次，均失败，请检查您的网络连接。" % _attempts)
                            break
            else:
                _attempts = 0
                _success = False
                while _attempts < 3 and not _success:
                    try:
                        hisDf = ts.get_k_data(scode, start=self.date, end=self.date)
                        c_price = list(hisDf['close'])[0]
                    except:
                        _attempts += 1
                        logging.warn(u"第 %d 次尝试 get_k_data 失败" % _attempts)
                        time.sleep(0.5)
                        if _attempts==3:
                            logging.error(u"尝试 get_k_data %d次，均失败，请检查您的网络连接。" % _attempts)
                            break

            self.close_price[scode] = c_price
            logging.info(u"[%03d/%03d] 股票代码：[%s] 收盘价：[%s]" % (index, total, scode, c_price))
        logging.debug(u"close_price: %s" % self.close_price)
        logging.info(u"所有股票收盘价获取结束。")
        if today_all_flag:
            return today_all_df
        else:
            return None

    def get_unbalanced(self):
        legacy_df = None
        pieces_df = None
        for idx, row in self.trader_detail.iterrows():
            for vol, price in row['buy_pairs']:
                data = OrderedDict()
                data[u'日期'] = self.date
                data[u'交易员编号'] = row['tcode']
                data[u'交易员姓名'] = self.names_dic[row['tcode']]
                data[u'股票代码'] = row['scode']
                data[u'股票名称'] = row['scode']
                data[u'数量'] = vol
                data[u'成本价'] = price
                data[u'收盘价'] = self.close_price[row['scode']]
                data[u'多空'] = 1
                #data[u'浮动盈亏'] = row['float_profit']
                data[u'浮动盈亏'] = vol * data[u'多空'] * (data[u'收盘价'] - price)
                if vol < 100:
                    if type(pieces_df) != type(None):
                        pieces_df = pieces_df.append(data, ignore_index=True)
                    else:
                        pieces_df = pd.DataFrame(data, index=[0])
                else:
                    if type(legacy_df) != type(None):
                        legacy_df = legacy_df.append(data, ignore_index=True)
                    else:
                        legacy_df = pd.DataFrame(data, index=[0])
            for vol, price in row['sell_pairs']:
                data = OrderedDict()
                data[u'日期'] = self.date
                data[u'交易员编号'] = row['tcode']
                data[u'交易员姓名'] = self.names_dic[row['tcode']]
                data[u'股票代码'] = row['scode']
                data[u'股票名称'] = row['scode']
                data[u'数量'] = vol
                data[u'成本价'] = price
                data[u'收盘价'] = self.close_price[row['scode']]
                data[u'多空'] = -1
                #data[u'浮动盈亏'] = row['float_profit']
                data[u'浮动盈亏'] = vol * data[u'多空'] * (data[u'收盘价'] - price)
                if vol < 100:
                    if type(pieces_df) != type(None):
                        pieces_df = pieces_df.append(data, ignore_index=True)
                    else:
                        pieces_df = pd.DataFrame(data, index=[0])
                else:
                    if type(legacy_df) != type(None):
                        legacy_df = legacy_df.append(data, ignore_index=True)
                    else:
                        legacy_df = pd.DataFrame(data, index=[0])
        if type(legacy_df)==type(None):
            empty = OrderedDict()
            empty[u'日期'] = []
            empty[u'交易员编号'] = []
            empty[u'交易员姓名'] = []
            empty[u'股票代码'] = []
            empty[u'股票名称'] = []
            empty[u'数量'] = []
            empty[u'成本价'] = []
            empty[u'收盘价'] = []
            empty[u'多空'] = []
            empty[u'浮动盈亏'] = []
            legacy_df = pd.DataFrame(empty, index=[])
        if type(pieces_df)==type(None):
            empty = OrderedDict()
            empty[u'日期'] = []
            empty[u'交易员编号'] = []
            empty[u'交易员姓名'] = []
            empty[u'股票代码'] = []
            empty[u'股票名称'] = []
            empty[u'数量'] = []
            empty[u'成本价'] = []
            empty[u'收盘价'] = []
            empty[u'多空'] = []
            empty[u'浮动盈亏'] = []
            pieces_df = pd.DataFrame(empty, index=[])
        return legacy_df, pieces_df

    def get_trader_df(self):
        res = None
        for tcode, df in self.trader_detail.groupby('tcode'):
            try:
                name = self.names_dic[tcode]
            except:
                name = str(tcode).zfill(8)
            tcode = str(tcode).zfill(8)
            sum_val = df.sum(axis=0, numeric_only=True)
            dt_dic = OrderedDict()
            dt_dic[u'日期'] = self.date
            dt_dic[u'交易员编号'] = tcode
            dt_dic[u'交易员姓名'] = name
            dt_dic[u'个人佣金'] = sum_val['trader_tax']
            dt_dic[u'印花税'] = sum_val['stamp_tax']
            dt_dic[u'上海市场经手费'] = sum_val['sh_tax']
            dt_dic[u'毛盈亏'] = sum_val['gross_profit']
            dt_dic[u'浮动盈亏'] = sum_val['float_profit']
            dt_dic[u'净盈亏'] = sum_val['retained_profit']
            if type(res) != type(None):
                res = res.append(dt_dic, ignore_index=True)
            else:
                res = pd.DataFrame(dt_dic, index=[0])
        return res

    def get_system_df(self):
        sum_val = self.system_detail.sum(axis=0, numeric_only=True)
        dt_dic = OrderedDict()
        dt_dic[u'系统佣金'] = sum_val['system_tax']
        dt_dic[u'印花税'] = sum_val['stamp_tax']
        dt_dic[u'上海市场经手费'] = sum_val['sh_tax']
        dt_dic[u'毛盈亏'] = sum_val['gross_profit']
        dt_dic[u'浮动盈亏'] = sum_val['float_profit']
        dt_dic[u'净盈亏'] = sum_val['retained_profit']
        res = pd.DataFrame(dt_dic, index=[self.date])
        return res

    def get_detail_df(self):
        self.detail_df = None
        for idx, row in self.trader_detail.iterrows():
            data = OrderedDict()
            total_vol = 0
            for vol, price in row['buy_pairs']:
                total_vol += vol
            for vol, price in row['sell_pairs']:
                total_vol -= vol
            data[u'date'] = self.date
            data[u'tcode'] = str(int(row['tcode'])).zfill(8)
            data[u'tname'] = self.names_dic[row['tcode']]
            data[u'scode'] = row['scode']
            data[u'sname'] = self.codes_dic[row['scode']]
            data[u'vol'] = total_vol
            data[u'price'] = self.close_price[row['scode']]
            data[u'broker_tax'] = row['sh_tax']
            data[u'stamp_tax'] = row['stamp_tax']
            data[u'system_tax'] = row['system_tax']
            data[u'trader_tax'] = row['trader_tax']
            data[u'trader_profit'] = row['retained_profit']
            data[u'system_profit'] = row['retained_profit'] + row['trader_tax'] - row['system_tax']
            if type(self.detail_df) != type(None):
                self.detail_df = self.detail_df.append(data, ignore_index=True)
            else:
                self.detail_df = pd.DataFrame(data, index=[0])
        return self.detail_df

    def compute_pieces(self):
        pass

    def compute_legacy(self):
        pass

    def compute_fluctuate(self):
        pass

    def compute_all(self):
        self.compute_pieces()
        self.compute_legacy()
        self.compute_system()
        self.compute_trader()
        self.compute_fluctuate()

    def compute_tax(self, taxes):
        logging.info(u"开始计算手续费和印花税。")
        self.record_df['stamp'] = [taxes['stamp'] * row['vol'] * row['price'] for idx, row in self.record_df.iterrows()]
        # 买入没有印花税
        self.record_df.loc[self.record_df['posit'] == 1, 'stamp'] = 0
        self.record_df['system'] = [taxes['system'] * row['vol'] * row['price'] for idx, row in self.record_df.iterrows()]
        self.record_df['trader'] = [taxes['trader'] * row['vol'] * row['price'] for idx, row in self.record_df.iterrows()]
        self.record_df['sh'] = [taxes['sh'] * row['vol'] * row['price'] for idx, row in self.record_df.iterrows()]
        # 股票代码非 60 开头 ( 非上海市场 ) 的没有经手费
        self.record_df.loc[[s[:2]!='60' for s in self.record_df['scode']], 'sh'] = 0
        logging.info(u"输出详细的手续费记录到[log/%s_tax_detail.xls]文件。" % self.date)
        self.record_df.to_excel('log/%s_tax_detail.xls' % self.date, encoding='gb2312', index=False)
        logging.info(u"计算手续费和印花税结束。")

    def compute_system(self):
        logging.info(u"开始计算系统收入。")
        tmp_dict = {'date':[], 'scode':[], 'stamp_tax':[], 'system_tax':[],
                'sh_tax':[], 'gross_profit':[], 'float_profit':[],
                'retained_profit':[], 'buy_pairs':[], 'sell_pairs':[]}
        self.system_detail = pd.DataFrame(tmp_dict, index=[])
        for scode, subDf in self.record_df.groupby('scode'):
            try:
                c_price = self.close_price[scode]
            except:
                logging.warning(u"没有获得[%s]的收盘价！" % scode)
                logging.warning(u"设置[%s]的收盘价为零！" % scode)
                logging.warning(u"股票价：%s" % self.close_price)
                c_price = 0.0
            result = self.simple_compute_df(subDf, c_price)
            p, fp, stamp, system, trader, sh, b_l, s_l = result
            final_system_profit = p - stamp - system - sh
            data = {}
            data['date'] = self.date
            data['scode'] = scode
            data['stamp_tax'] = stamp
            data['system_tax'] = system
            data['sh_tax'] = sh
            data['gross_profit'] = p
            data['float_profit'] = fp
            data['retained_profit'] = final_system_profit
            data['buy_pairs'] = b_l
            data['sell_pairs'] = s_l
            self.system_detail = self.system_detail.append(data, ignore_index=True)
        logging.info(u"输出系统详细记录到[log/%s_system_detail.xlsx]文件。" % self.date)
        self.system_detail.to_excel('log/%s_system_detail.xlsx' % self.date, encoding='gb2312')
        logging.info(u"计算系统收入结束。")

    def compute_trader(self):
        logging.info(u"开始计算交易员收入。")
        tmp_dict = {'date':[], 'tcode':[], 'scode':[], 'stamp_tax':[],
                'system_tax':[], 'sh_tax':[], 'gross_profit':[],
                'float_profit':[], 'retained_profit':[], 'buy_pairs':[],
                'sell_pairs':[]}
        self.trader_detail = pd.DataFrame(tmp_dict, index=[])
        for tcode, df in self.record_df.groupby('tcode'):
            for scode, subdf in df.groupby('scode'):
                try:
                    c_price = self.close_price[scode]
                except:
                    logging.warning(u"没有获得[%s]的收盘价！" % scode)
                    logging.warning(u"设置[%s]的收盘价为零！" % scode)
                    logging.warning(u"股票价：%s" % self.close_price)
                    c_price = 0.0
                result = self.simple_compute_df(subdf, c_price)
                p, fp, stamp, system, trader, sh, b_l, s_l = result
                final_system_profit = p - stamp - trader - sh
                data = {}
                data['date'] = self.date
                data['tcode'] = tcode
                data['scode'] = scode
                data['stamp_tax'] = stamp
                data['system_tax'] = system
                data['trader_tax'] = trader
                data['sh_tax'] = sh
                data['gross_profit'] = p
                data['float_profit'] = fp
                data['retained_profit'] = final_system_profit
                data['buy_pairs'] = b_l
                data['sell_pairs'] = s_l
                self.trader_detail = self.trader_detail.append(data, ignore_index=True)
        logging.info(u"输出交易员详细记录到[log/%s_trader_detail.xlsx]文件。" % self.date)
        self.trader_detail.to_excel('log/%s_trader_detail.xlsx' % self.date, encoding='gb2312')
        logging.info(u"开始计算交易员收入。")

    def simple_compute_df(self, df, c_price):
        df.sort_values('time')
        b_list = [(r['vol'], r['price']) for i, r in df.loc[df['posit']==1, :].iterrows()]
        s_list = [(r['vol'], r['price']) for i, r in df.loc[df['posit']==-1,:].iterrows()]
        profit, f_profit, b_ret_list, s_ret_list = self.simple_compute(b_list, s_list, c_price)
        sum_val = df.sum(axis=0, numeric_only=True)
        stamp_tax, system_tax, trader_tax, sh_tax = sum_val[['stamp', 'system', 'trader', 'sh']]
        return (profit, f_profit, stamp_tax, system_tax, trader_tax, sh_tax, b_ret_list, s_ret_list)

    def simple_compute(self, b_list, s_list, c_price):
        b_deque = deque(b_list)
        s_deque = deque(s_list)
        profit = 0.0
        float_profit = 0.0
        while len(b_deque) > 0 and len(s_deque) > 0:
            b_vol, b_price = b_deque.popleft()
            s_vol, s_price = s_deque.popleft()
            delta_price = s_price - b_price
            volumn = min(b_vol, s_vol)
            profit += delta_price * volumn
            if b_vol > s_vol:
                b_deque.appendleft((b_vol - volumn, b_price))
            if b_vol < s_vol:
                s_deque.appendleft((s_vol - volumn, s_price))
        for b_vol, b_price in b_deque:
            float_profit += (c_price - b_price) * b_vol
        for s_vol, s_price in s_deque:
            float_profit += (s_price - c_price) * s_vol
        return (profit, float_profit, list(b_deque), list(s_deque))


if __name__ == '__main__':
    logging.info(u"结算程序[%s]开始执行。" % __VERSION__)
    if len(sys.argv) == 1:
        cfgfile = 'setting.ini'
    elif len(sys.argv) == 2:
        cfgfile = sys.argv[1]
    else:
        logging.error(u"程序使用错误！")
        raise Exception("Program Usage Error!")
    if not os.path.exists(cfgfile):
        logging.error(u"配置文件[%s]没有找到！" % cfgfile)
        raise Exception('Configuration File[%s] Do Not Exists!' % cfgfile)
    config = configparser.ConfigParser()
    config.readfp(codecs.open(cfgfile, 'r', 'utf-8-sig'))
    record_excel_file = str(config['input']['record'])
    legacy_excel_file = str(config['input']['legacy'])
    pieces_excel_file = str(config['input']['pieces'])
    if not os.path.exists(record_excel_file):
        logging.error(u"成交记录文件[%s]没有找到！" % record_excel_file)
        raise Exception('File[%s] Do Not Exists!' % record_excel_file)
    if not os.path.exists(legacy_excel_file):
        logging.warning(u"隔夜仓文件[%s]没有找到！" % legacy_excel_file)
        legacy_excel_file = None
    if not os.path.exists(pieces_excel_file):
        logging.warning(u"零头股文件[%s]没有找到！" % pieces_excel_file)
        pieces_excel_file = None
    myCalc = Calculator(record_excel_file, legacy_excel_file, pieces_excel_file)

    head_convert = 'HeadConvert.xls'
    if not os.path.exists(head_convert):
        logging.error(u"头转换文件[%s]没有找到！" % head_convert)
        raise Exception(u"File[%s] Do Not Exists!" % head_convert)
    else:
        myCalc.convert_head(head_convert)

    names_excel_file = str(config['names']['names_to_account'])
    if os.path.exists(names_excel_file):
        myCalc.read_names(names_excel_file)
    myCalc.preprocess_record()
    taxes = {}
    taxes['stamp']  = float(config['tax']['stamp_tax_rate'])
    taxes['trader'] = float(config['tax']['trader_tax_rate'])
    taxes['system'] = float(config['tax']['system_tax_rate'])
    taxes['sh']     = float(config['tax']['sh_tax_rate'])
    myCalc.compute_tax(taxes)

    hq_file = config["hq"]["excel_file"]
    if hq_file != "" and os.path.exists(hq_file):
        scode_head = config["hq"]["scode_head"]
        price_head = config["hq"]["price_head"]
        logging.info(u"从行情文件[%s]中获取收盘价。" % hq_file)
        myCalc.read_close_price(hq_file, scode_head, price_head, u"名称")
    else:
        logging.info(u"行情文件[%s]未找到，尝试从网络获取。" % hq_file)
        ts_today_all_df = myCalc.fetch_close_price()
        if ts_today_all_df:
            ts_today_all_df.to_excel('TSHQ%s.xlsx' % TODAY , encoding='gb2312')
        else:
            logging.error(u"从网络获取行情失败！")
            raise Exception("Get Quotes From Internet Failed!")

    myCalc.compute_all()

    main_name = record_excel_file[:-4]
    myCalc.get_system_df().to_excel('%s_system.xlsx' % main_name, encoding='gb2312')
    logging.info(u"成功输出系统盈亏到[%s_system.xlsx]文件。" % main_name)
    myCalc.get_trader_df().to_excel('%s_trader.xlsx' % main_name, encoding='gb2312')
    logging.info(u"成功输出交易员盈亏到[%s_trader.xlsx]文件。" % main_name)
    legacy_df, pieces_df = myCalc.get_unbalanced()
    legacy_df.to_excel('%s_legacy.xlsx' % main_name, encoding='gb2312')
    logging.info(u"成功输出隔夜仓到[%s_legacy.xlsx]文件。" % main_name)
    pieces_df.to_excel('%s_pieces.xlsx' % main_name, encoding='gb2312')
    logging.info(u"成功输出零头股到[%s_pieces.xlsx]文件。" % main_name)
    myCalc.get_detail_df().to_excel("%s_detail.xlsx" % main_name, encoding="gb2312")
    logging.info(u"成功输出详情到[%s_detail.xlsx]文件。" % main_name)
    input(u"程序执行完成，请按回车结束。")
