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

from collections import defaultdict, deque, OrderedDict

from calculator import TradeAnalyzer as TA
from calculator import Calculator
from calculator import Trade

__VERSION__ = '3.1'

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
#console.setLevel(logging.DEBUG)

logging.getLogger('').addHandler(console)


if __name__ == '__main__':
    logging.info(u"结算程序[V%s]开始执行。" % __VERSION__)
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
    ta = TA()

    names_excel_file = str(config['names']['names_to_account'])
    if os.path.exists(names_excel_file):
        names_dic = {}
        df = pd.read_excel(names_excel_file, encoding='gb2312')
        df.dropna()
        for idx, row in df.iterrows():
            try:
                account = str(int(row['Account'])).zfill(8)
                name = str(row['Names'])
                names_dic[account] = name
            except:
                logging.warning(u"在读取交易员配置[%s]第[%s]行[%s]时出错！"
                        %(names_excel_file, idx, row))
                continue
        ta.traders_name = names_dic
    else:
        logging.error("交易员配置文件[%s]没有找到！" % names_excel_file)
        raise Exception("File[%s] Do Not Exists!" % names_excel_file)
    logging.info("成功读取交易员配置文件，读入[%s]个交易员。" % len(names_dic))

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
    record_df = pd.read_excel(record_excel_file, encoding='gb2312')
    trade_date = list(record_df["业务日期"])[0]
    logging.info("读入的成交记录的成交日期是：%s。" % trade_date)

    head_convert = 'HeadConvert.xls'
    if not os.path.exists(head_convert):
        logging.error(u"头转换文件[%s]没有找到！" % head_convert)
        raise Exception(u"File[%s] Do Not Exists!" % head_convert)
    else:
        df = pd.read_excel(head_convert, encoding='gb2312')
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
        record_df = record_df[list(head_cols.keys())]
        record_df.rename(columns=head_cols, inplace=True)
        long_loc = record_df['posit'] == long_str
        short_loc = record_df['posit'] == short_str
        record_df.loc[long_loc, 'posit'] = 1
        record_df.loc[short_loc, 'posit'] = -1
        loc = np.logical_or(long_loc, short_loc)
        record_df = record_df.loc[loc, :]

    taxes = {}
    taxes['stamp']  = float(config['tax']['stamp_tax_rate'])
    taxes['trader'] = float(config['tax']['trader_tax_rate'])
    taxes['system'] = float(config['tax']['system_tax_rate'])
    taxes['shanghai'] = float(config['tax']['sh_tax_rate'])
    
    for idx, row in record_df.iterrows():
        tcode = str(int(row["tcode"])).zfill(8)
        scode = str(int(row["scode"])).zfill(6)
        direct = int(row["posit"])
        vol = int(row["vol"])
        price = float(row["price"])
        t = Trade(vol, price, direct, tcode, scode, taxes)
        ta.add_trade(t)

    logging.debug(ta.trades_df.keys())
    logging.debug([len(x) for x in ta.trades_df.values()])
    logging.info("总共读取到[%d]条记录。" % sum([len(x) for x in ta.trades_df.values()]))
    logging.info("涉及到的交易员编号：%s" % ",".join(ta.traders_code))
    logging.info("涉及到的证券代码：%s" % ",".join(ta.secs_code))

    ta.update_result_df()

    hq_file = config["hq"]["excel_file"]
    hq_price = dict()
    hq_names = dict()
    hq_gains = dict()
    hq_ampli = dict()
    if hq_file != "" and os.path.exists(hq_file):
        logging.info(u"从行情文件[%s]中获取收盘价、涨幅和振幅。" % hq_file)
        hq_df = pd.read_excel(hq_file, encoding="gb2312")
        for idx, row in hq_df.iterrows():
            try:
                scode = str(int(row["代码"])).zfill(6)
            except:
                continue
            sname = row["名称"]
            try:
                price = float(row["现价"])
            except:
                price = 0
            try:
                gains = float(row["涨跌"])
            except:
                gains = 0
            try:
                ampli = float(row["振幅%%"])
            except:
                ampli = 0
            hq_names[scode] = sname
            hq_price[scode] = price
            hq_gains[scode] = gains
            hq_ampli[scode] = ampli
            logging.debug(u"股票代码：[%s|%s] 收盘价：[%s] 涨幅：[%s] 振幅：[%s]" % (scode, sname, price, gains, ampli))
        logging.info(u"所有股票收盘价获取结束。")
    else:
        logging.info(u"行情文件[%s]未找到，尝试从网络获取。" % hq_file)
        raise Exception("File[%s] Do Not Exists" % hq_file)
        """
        ts_today_all_df = myAnalyzer.fetch_close_price()
        if ts_today_all_df:
            ts_today_all_df.to_excel('TSHQ%s.xlsx' % TODAY , encoding='gb2312')
        else:
            logging.error(u"从网络获取行情失败！")
            raise Exception("Get Quotes From Internet Failed!")
        """
    ta.set_current_price(hq_price)

    main_name = record_excel_file[:-4]
    system_df = ta.get_system_df()
    system_df = {
            "系统佣金":         round(system_df["system_tax"],2),
            "印花税":           round(system_df["stamp_tax"],2),
            "上海市场经手费":   round(system_df["sh_tax"],2),
            "毛盈亏":           round(system_df["profit_land"],2),
            "浮动盈亏":         round(system_df["profit_float"],2),
            "净盈亏":           round(system_df["snp"],2)
            }
    system_df = pd.DataFrame(system_df, index=[trade_date])
    system_df = system_df.ix[:, ["系统佣金", "印花税", "上海市场经手费", "毛盈亏", "浮动盈亏", "净盈亏"]]
    system_df.to_excel("%s_system.xlsx" % main_name, encoding="gb2312")
    logging.info(u"成功输出系统盈亏到[%s_system.xlsx]文件。" % main_name)

    trader_dict = ta.get_trader_df()
    trader_df = None
    dtdc = {u"日期": trade_date,
            u"交易员编号": None,
            u"交易员姓名": None,
            u"个人佣金": 0,
            u"印花税": 0,
            u"上海市场经手费": 0,
            u"毛盈亏": 0,
            u"浮动盈亏": 0,
            u"净盈亏": 0
            }
    names_dic = ta.traders_name
    for tcode in trader_dict.keys():
        dtdc["交易员编号"] = tcode
        try:
            dtdc["交易员姓名"] = names_dic[tcode]
        except:
            dtdc["交易员姓名"] = tcode
        dtdc["个人佣金"] =          round(trader_dict[tcode]["trader_tax"], 2)
        dtdc["印花税"] =            round(trader_dict[tcode]["stamp_tax"], 2)
        dtdc["上海市场经手费"] =    round(trader_dict[tcode]["sh_tax"], 2)
        dtdc["毛盈亏"] =            round(trader_dict[tcode]["profit_land"], 2)
        dtdc["浮动盈亏"] =          round(trader_dict[tcode]["profit_float"], 2)
        dtdc["净盈亏"] =            round(trader_dict[tcode]["tnp"], 2)
        if trader_df is None:
            trader_df = pd.DataFrame(dtdc, index=[0])
        else:
            trader_df = trader_df.append(dtdc, ignore_index=True)
    if trader_df is None:
        _msg = "没有找到指定的交易员成交，请查看[%s]文件是否正确" % names_excel_file
        logging.warning(_msg)
        trader_df = pd.DataFrame({"信息": _msg}, ignore_index=True)
    else:
        trader_df = trader_df.ix[:, ["日期", "交易员编号", "交易员姓名", "个人佣金", "印花税", "上海市场经手费", "毛盈亏", "浮动盈亏", "净盈亏"]]
    trader_df.to_excel("%s_trader.xlsx" % main_name, encoding="gb2312")
    logging.info(u"成功输出交易员盈亏到[%s_trader.xlsx]文件。" % main_name)

    unbalanced_list = ta.get_unbalanced_df()
    legacy_df, pieces_df = None, None
    dt  =  {"日期": trade_date,
            "交易员编号": None,
            "交易员姓名": None,
            "股票代码": None,
            "股票名称": None,
            "数量": None,
            "成本价": None,
            "收盘价": None,
            "多空": None,
            "浮动盈亏": None
            }
    for i in unbalanced_list:
        dt["交易员编号"] = i["tcode"]
        dt["交易员姓名"] = names_dic[i["tcode"]]
        dt["股票代码"] = i["scode"]
        dt["股票名称"] = hq_names[i["scode"]]
        dt["数量"] = i["vol"]
        dt["成本价"] = i["price"]
        dt["收盘价"] = hq_price[i["scode"]]
        dt["多空"] = i["direct"]
        dt["浮动盈亏"] = (hq_price[i["scode"]]-i["price"])*i["vol"]*i["direct"]
        if i["vol"] == 0:
            # Ignore balanced
            pass
        if i["vol"] < 100:
            if pieces_df is None:
                pieces_df = pd.DataFrame(dt, index=[0])
            else:
                pieces_df = pieces_df.append(dt, ignore_index=True)
        else:
            if legacy_df is None:
                legacy_df = pd.DataFrame(dt, index=[0])
            else:
                legacy_df = legacy_df.append(dt, ignore_index=True)
    if legacy_df is None:
        legacy_df = pd.DataFrame({"信息":"隔夜仓为空"}, index=[0])
    else:
        legacy_df = legacy_df.ix[:, ["日期", "交易员编号", "交易员姓名", "股票代码", "股票名称", "数量", "成本价", "收盘价", "多空", "浮动盈亏"]]
    legacy_df.to_excel('%s_legacy.xlsx' % main_name, encoding='gb2312')
    logging.info(u"成功输出隔夜仓到[%s_legacy.xlsx]文件。" % main_name)
    if pieces_df is None:
        pieces_df = pd.DataFrame({"信息": "零头股为空"},index=[0])
    else:
        pieces_df = pieces_df.ix[:, ["日期", "交易员编号", "交易员姓名", "股票代码", "股票名称", "数量", "成本价", "收盘价", "多空", "浮动盈亏"]]
    pieces_df.to_excel('%s_pieces.xlsx' % main_name, encoding='gb2312')
    logging.info(u"成功输出零头股到[%s_pieces.xlsx]文件。" % main_name)

    detail_list = ta.get_detail_df()
    detail_df = None
    dt = {
            "日期": trade_date,
            "交易员编号": None,
            "交易员姓名": None,
            "股票代码": None,
            "股票名称": None,
            "个人佣金": None,
            "系统佣金": None,
            "印花税": None,
            "上海市场经手费": None,
            "毛盈亏": None,
            "浮动盈亏": None,
            "个人盈亏": None,
            }
    for i in detail_list:
        dt["交易员编号"] = i["tcode"]
        dt["交易员姓名"] = names_dic[i["tcode"]]
        dt["股票代码"] = i["scode"]
        dt["股票名称"] = hq_names[i["scode"]]
        dt["个人佣金"] = round(i["trader_tax"],2)
        dt["系统佣金"] = round(i["system_tax"],2)
        dt["印花税"] = round(i["stamp_tax"],2)
        dt["上海市场经手费"] = round(i["sh_tax"],2)
        dt["毛盈亏"] = round(i["profit_land"],2)
        dt["浮动盈亏"] = i["profit_float"]
        dt["个人盈亏"] = i["profit_land"] - i["trader_tax"] - i["stamp_tax"] - i["sh_tax"]
        if detail_df is None:
            detail_df = pd.DataFrame(dt, index=[0])
        else:
            detail_df = detail_df.append(dt, ignore_index=True)
    detail_df = detail_df.ix[:,["日期","交易员编号","交易员姓名","股票代码","股票名称","个人佣金","系统佣金","印花税","上海市场经手费","毛盈亏","浮动盈亏","个人盈亏"]]
    detail_df.to_excel("%s_detail.xlsx" % main_name, encoding="gb2312")
    logging.info(u"成功输出详情到[%s_detail.xlsx]文件。" % main_name)

    hold_excel = str(config['hold']['hold_file'])
    if hold_excel != "" and os.path.exists(hold_excel):
        analyz_df = None
        dt = {
                "日期": trade_date,
                "股票代码": None,
                "股票名称": None,
                "股票振幅": None,
                "交易员编号": None,
                "交易员姓名": None,
                "持仓市值(万元)": None,
                "盈亏(元)": None,
                "交易振幅": None
                }
        hold_df = pd.read_excel(hold_excel, encoding='gb2312')
        for idx, row in hold_df.iterrows():
            scode = str(int(row["证券代码"])).zfill(6)
            tcode = str(int(row["交易员"])).zfill(8)
            value = float(row["分配市值"])
            if value == 0.0:
                continue
            dt["交易员编号"] = tcode
            dt["股票代码"] = scode
            dt["股票名称"] = row["证券名称"]
            try:
                dt["股票振幅"] = hq_ampli[scode]
            except:
                dt["股票振幅"] = None
            dt["交易员姓名"] = names_dic[tcode]
            dt["持仓市值(万元)"] = round(value/10000.0,2)
            personal_profit = 0.0
            for idx, row in detail_df.iterrows():
                if row["交易员编号"]==tcode and row["股票代码"]==scode:
                    personal_profit = row["个人盈亏"]
                    break
            dt["盈亏(元)"] = round(float(personal_profit),2)
            dt["交易振幅"] = round(personal_profit * 100.0 / value,2)
            if analyz_df is None:
                analyz_df = pd.DataFrame(dt, index=[0])
            else:
                analyz_df = analyz_df.append(dt, ignore_index=True)
        analyz_df = analyz_df.sort_values("股票代码")
        analyz_df = analyz_df.ix[:, ["股票代码","股票名称","股票振幅","交易员姓名","持仓市值(万元)","盈亏(元)","交易振幅"]]
        analyz_df.to_excel("%s_analyz.xlsx" % main_name, encoding="gb2312", index=False)
        logging.info(u"成功输出分析到[%s_analyz.xlsx]文件。" % main_name)
    else:
        logging.info(u"交易员持仓文件[%s]没有找到！" % hold_excel)
    input(u"程序执行完成，请按回车结束。")

