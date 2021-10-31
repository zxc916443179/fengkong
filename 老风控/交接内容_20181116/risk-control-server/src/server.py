# -*- coding: utf-8 -*-
import gevent.monkey
gevent.monkey.patch_all()

import os
import io
import re
import sys
import csv
import time
import json
import math
import socket
import pickle
import gevent
import codecs
import logging
import datetime
import functools
import configparser

import numpy as np
import pandas as pd
import tushare as ts
import traceback as tb

from dbfread import DBF
from gevent.pool import Pool
from calculator import Trade, Calculator, TradeAnalyzer, RiskControlUtil
from collections import defaultdict


TODAY = time.strftime('%Y%m%d',time.localtime(time.time()))
if not os.path.exists('log/'):
    os.mkdir('log/')

logging.basicConfig(level=logging.INFO,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                datefmt='%a, %d %b %Y %H:%M:%S',
                filename='log/server_%s.log'%TODAY,
                filemode='a')

console = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
console.setFormatter(formatter)
console.setLevel(logging.INFO)

logging.getLogger('').addHandler(console)

DBF_FILE_P = re.compile(r'Trealdeal_(\d{8})\.log')


def clean_log(keep_day=30):
    old_day = str(datetime.date.today() - datetime.timedelta(days=keep_day)).replace('-', '')
    logging.info("清除早于[%s]的日志文件。" % old_day)
    logfile_list = os.listdir('log/')
    for logfile in logfile_list:
        if logfile < 'server_%s' % old_day:
            os.remove('log/%s' % logfile)


class Handler():

    def __init__(self, traders_info, dbf_file, costs, ip, port):
        self.dbf_file = dbf_file

        self.ta = TradeAnalyzer()
        self.ta.set_taxs(costs)
        self.ta.traders_code = traders_info.keys()
        tname_dict, tloss_dict = dict(), dict()
        self.traders_info = traders_info
        for t in traders_info.keys():
            tname_dict[t] = traders_info[t][0]
            tloss_dict[t] = traders_info[t][1]
        self.ta.traders_name = tname_dict
        self.ta.traders_loss = tloss_dict

        self.lock = False
        self.detail_dt = self.ta.get_detail_df()
        self.unbalanaced_dt = self.ta.get_unbalanced_df()
        self.trader_dt = self.ta.get_trader_df()
        self.system_dt = self.ta.get_system_df()

        self.init_server(ip, port)
        self.pool = Pool()
        self.pool.add(gevent.spawn(self.update_done))
        self.pool.add(gevent.spawn(self.update_hq))
        self.pool.add(gevent.spawn(self.create_conn))
        self.pool.join()

    def update_done(self):
        _gap = 1
        while 1:
            gevent.sleep(_gap)
            while self.lock:
                gevent.sleep(0.1)
            try:
                result = dict()
                for record in DBF(self.dbf_file, recfactory=dict):
                    result[record['CJXH']] = record
                records = list(result.values())
                logging.debug("开始更新成交。")
                self.lock = True
                self.ta.clean_trade()
                for row in records:
                    scode = str(int(row['ZQDM'])).zfill(6)
                    if scode in ['204001']:
                        continue
                    tcode = str(int(row['TZGW'])).zfill(8)
                    vol = int(row['CJSL'])
                    price = float(row['CJJG'])
                    direct = int(row['WTFX'])
                    if direct == 2:
                        direct = -1
                    t = Trade(vol, price, direct, tcode, scode)
                    logging.debug("更新成交[%s]。" % t)
                    self.ta.add_trade(t)
                logging.info("更新[%s]条成交记录" % len(records))
                self.detail_dt = self.ta.get_detail_df()
                self.unbalanaced_dt = self.ta.get_unbalanced_df()
                self.trader_dt = self.ta.get_trader_df()
                self.system_dt = self.ta.get_system_df()
            except:
                logging.warning(tb.format_exc())
                logging.warning('更新成交记录失败，可能是资源上锁。')
            self.lock = False

    def update_hq(self):
        _gap = 1
        while 1:
            gevent.sleep(_gap)
            while self.lock:
                gevent.sleep(0.1)
            try:
                current_codes = self.ta.secs_code
                if len(current_codes) == 0:
                    logging.info("目前没有交易的股票。")
                    continue

                hq_data = ts.get_realtime_quotes(current_codes)
                prices_dict = dict()
                self.scode_info = dict()
                for idx, row in hq_data.iterrows():
                    try:
                        price = float(row['price'])
                    except:
                        price = 0.0
                    prices_dict[row['code']] = price
                    self.scode_info[row['code']] = {
                            "sname": row['name'],
                            "recent_price": price
                            }
                self.ta.set_current_price(prices_dict)

                self.lock = True
                self.detail_dt = self.ta.get_detail_df()
                self.unbalanaced_dt = self.ta.get_unbalanced_df()
                self.trader_dt = self.ta.get_trader_df()
                self.system_dt = self.ta.get_system_df()
                logging.info("目前成交了[%d]只股票，成功从网络获取它们的行情。" % len(current_codes))
            except:
                logging.warning(tb.format_exc())
                logging.warning('更新行情失败，可能是资源上锁，也可能是网络问题。')
            self.lock = False

    def init_server(self, ip, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((ip, port))
        s.listen(1)
        self.soc = s

    def create_conn(self):
        while 1:
            try:
                logging.debug("等待链接")
                conn, addr = self.soc.accept()
                #conn.settimeout(5)
                logging.info("新的客户端链接[%s]" % str(addr))
                self.pool.add(gevent.spawn(self.handle_new_conn, conn, addr))
            except:
                logging.warning(tb.format_exc())
                logging.warning('Establish Connection Failed!')

    def handle_new_conn(self, conn, addr):
        while 1:
            try:
                with gevent.Timeout(5, False) as timeout:
                    data = conn.recv(1024)
                try:
                    data = data.decode('utf-8')
                except:
                    logging.warning("收到的数据无法用utf-8解码")
                    logging.warning("关闭[%s]的链接！" % str(addr))
                    break
                logging.info("收到客户端[%s]的请求[%s]" % (str(addr), data))
                if len(data) == 0:
                    logging.info('正常关闭[%s]的链接。' % str(addr) )
                    break
                elif data == 'request_web':
                    while self.lock:
                        gevent.sleep(0.1)
                    doc = dict()
                    doc["trader"] = RiskControlUtil.make_trader_matrix(self.trader_dt, self.traders_info)
                    temp = json.dumps(doc)
                    with gevent.Timeout(5, False) as timeout:
                        conn.sendall(temp.encode('utf-8'))
                elif data == 'request':
                    while self.lock:
                        gevent.sleep(0.1)
                    with gevent.Timeout(5, False) as timeout:
                        conn.sendall(pickle.dumps("未知请求", protocol=2))
                elif data == 'request_split':
                    while self.lock:
                        gevent.sleep(0.1)
                    big_dt = RiskControlUtil.make_big_matrix(self.ta, self.scode_info)
                    res = []
                    #res = [["测试人员", "浮动盈亏", "止损线", "***"], ['总计', 12345]]
                    total = 0
                    personal_profit = defaultdict(list)
                    for i in big_dt:
                        if len(personal_profit[i["tcode"]]) == 0:
                            personal_profit[i["tcode"]] = [i["tname"], i["profit_float"]+i["profit_land"], i["tloss"]]
                        else:
                            personal_profit[i["tcode"]][1] += i["profit_float"] + i["profit_land"]
                        total += i["profit_float"] + i["profit_land"]
                    for tcode in personal_profit.keys():
                        ele = personal_profit[tcode]
                        ele[1] = int(ele[1])
                        _flag = ''
                        if ele[2] != 0:
                            rate = ele[1] / ele[2]
                            if rate < 0.3333:
                                _flag = ''
                            elif rate < 0.6666:
                                _flag = '*'
                            elif rate < 0.9999:
                                _flag = '**'
                            else:
                                _flag = '***'
                        ele.append(_flag)
                        res.append(ele)
                    res.append(["总计", int(total)])

                    res_status = []
                    #res_status = [["long", "测试人员", "600837", "海通证券", "浮动盈亏", "持仓股数", '50%', '***']]
                    for i in big_dt:
                        if i["direct"] == "close":
                            continue
                        percent = "--"
                        if i["sprice"] != 0:
                            percent = round(i["profit_float"] / (i["unbalanced"] * i["sprice"]) * 100, 2)
                            percent = "{}%".format(percent)
                        _flag = ''
                        if i["tloss"] != 0:
                            rate = i["profit_float"] / i["tloss"]
                            if rate < 0.3333:
                                _flag = ''
                            elif rate < 0.6666:
                                _flag = '*'
                            elif rate < 0.9999:
                                _flag = '**'
                            else:
                                _flag = '***'
                        res_status.append([i["direct"], i["tname"], i["scode"], i["sname"], round(i["profit_float"],3), i["unbalanced"], percent, _flag])
                    new_data = (res, res_status)
                    with gevent.Timeout(5, False) as timeout:
                        conn.sendall(pickle.dumps(new_data, protocol=2) +
                                b'\x00\x00\xee\xee\x00\x00')
                elif data == 'close':
                    conn.sendall('ok'.encode('utf-8'))
                    logging.info('响应客户端[%s]的请求，关闭链接。'%str(addr))
                    break
                elif data[:4] == 'ver3':
                    interface = dict()

                    brief_dict = dict()
                    for tcode in self.traders_info.keys():
                        tname, tloss = self.traders_info[tcode]
                        if math.isnan(tloss):
                        	tloss = 1000
                        brief_dict[tcode] = {"tcode": tcode, "tname": tname,
                                "tloss": tloss,
                                "profit_land": 0,
                                "profit_float": 0,
                                "trader_cost": 0,
                                }

                    # 多空，姓名，代码，证券名称，暴露头寸，现价，市值，成本金额，浮动盈亏，盈亏占用仓位百分比，警示信息
                    detail = list()

                    for key in self.ta.calculators.keys():
                        tcode, scode = key
                        tname, tloss = self.traders_info[tcode]
                        sname = self.scode_info[scode]["sname"]
                        price = self.scode_info[scode]["recent_price"]
                        self.ta.calculators[key].set_price_current(price)
                        _brief = brief_dict[tcode]
                        _brief["trader_cost"] += self.ta.calculators[key].trader_cost
                        _brief["profit_land"] += self.ta.calculators[key].profit_land
                        _brief["profit_float"] += self.ta.calculators[key].profit_float
                        if self.ta.calculators[key].remain_vol != 0:
                            detail.append("long")
                            detail.append(tname)
                            detail.append(scode)
                            detail.append(sname)
                            detail.append("{}".format(abs(self.ta.calculators[key].remain_vol)))
                            detail.append("{}".format(price))
                            detail.append("{}".format(int(price * self.ta.calculators[key].remain_vol)))
                            detail.append("{}".format(int(self.ta.calculators[key].remain_amt)))
                            detail.append("{}".format(int(self.ta.calculators[key].profit_float)))
                            detail.append("{}%".format(int(self.ta.calculators[key].profit_float / self.ta.calculators[key].remain_amt * 100)))
                            detail.append("**")

                    # 姓名，落地盈亏，浮动盈亏，止损线，警示信息
                    brief = list()
                    for key in brief_dict:
                        brief.append(brief_dict[key]["tname"])
                        brief.append("{}".format(int(brief_dict[key]["profit_land"] - brief_dict[key]["trader_cost"])))
                        brief.append("{}".format(int(brief_dict[key]["profit_float"])))
                        brief.append("{}".format(int(float(brief_dict[key]["tloss"]))))
                        brief.append("**")

                    interface['brief'] = brief
                    interface['detail'] = detail
                    document = json.dumps(interface)
                    conn.sendall(document.encode('utf-8'))
                elif data[:4] == 'test':
                    interface = dict()
                    v = (int(time.time()) % 100)+1
                    brief = ["测试账号", "{}".format(v*100), "-{}".format(v), "**"]
                    # 多空方向，交易员姓名，证券代码，证券名称，浮动盈亏，暴露头寸，盈亏占用仓位百分比，警示信息
                    detail = ["long", "测试账号", "600837", "海通证券", "{}".format(v*100), "-{}".format(v), "{}%".format(v), "**",
                              "short", "测试账号2", "600837", "海通证券", "{}".format(v*100+1), "-{}".format(v+1), "{}%".format(v+1), "*",]

                    interface['brief'] = brief
                    interface['detail'] = detail

                    document = json.dumps(interface)
                    conn.sendall(document.encode('utf-8'))
                    logging.info('收到测试请求')
                elif data == 'h':
                    conn.sendall('o'.encode('utf-8'))
                else:
                    logging.warning("收到非法数据[%s]！" % data)
                    logging.warning("关闭[%s]的链接！" % str(addr))
                    break
            except:
                logging.warning('处理客户端[%s]的链接时出错！断开链接！' % str(addr))
                logging.warning(tb.format_exc())
                break
        conn.close()


if __name__ == '__main__':
    if (len(sys.argv) == 1):
        cfgfile = "conf/setting.ini"
    elif (len(sys.argv) == 2):
        cfgfile = sys.argv[1]
    else:
        logging.error("程序调用错误！")
        raise Exception("Program Usage Error.")
    if not os.path.exists(cfgfile):
        logging.error("指定的配置文件[%s]不存在！" % cfgfile)
        raise Exception("File[%s] Do Not Exists." % cfgfile)

    clean_log()

    logging.debug("指定配置文件[%s]。" % cfgfile)
    config = configparser.ConfigParser()
    config.readfp(codecs.open(cfgfile, "r", "utf-8-sig"))

    server_name = str(config['server']['server_name'])
    names_to_account = config['server']['names_to_account']
    log_dir = str(config['server']['log_dir'])
    ip = config['server']['ip']
    port = int(config['server']['port'])

    logging.info("初始化手续费等费率信息")
    costs = None
    try:
        costs = {
                "trader": float(config["server"]["trader_tax_rate"]),
                "system": float(config["server"]["system_tax_rate"]),
                "stamp": float(config["server"]["stamp_tax_rate"]),
                "shanghai": float(config["server"]["sh_tax_rate"])
                }
        logging.debug("从配置文件中读入手续费率的配置[%s]" % costs)
    except:
        logging.warning("配置文件[%s]中关于手续费率的配置错误，设置为程序内置默认手续费率")

    logging.info("初始化交易员信息")
    traders_info = dict()
    if os.path.exists(names_to_account):
        names_df = pd.read_excel(names_to_account, encoding="gb2312")
        for idx, row in names_df.iterrows():
            try:
                tcode = str(int(row["Account"])).zfill(8)
                name = str(row["Names"]).strip()
                loss = float(row["Stop"])
            except:
                logging.warning("交易员配置行[%s]读取错误" % re.sub('\s+', '~', row.to_string()))
                continue
            if tcode in traders_info.keys():
                logging.warning("交易员配置文件[%s]中，编号[%s]重复出现" % (names_to_account, tcode))
            traders_info[tcode] = (name, loss)
    else:
    	logging.error("交易员配置文件[{}]没找到！".format(names_to_account))
    	raise Exception("Traders Info File[{}] Do Not Exists!".format(names_to_account))
    for t in traders_info.keys():
        logging.debug("t=%s, n=%s, l=%s" % (t, traders_info[t][0], traders_info[t][1]))

    logging.info("查找成交记录文件")
    if not os.path.exists(log_dir):
        logging.error("没找到 pbrc log 目录[%s]" % log_dir)
        raise Exception("PBRC Log Folder[%s] Do Not Exists!" % log_dir)
    filenames = os.listdir(log_dir)
    files = []
    for f in filenames:
        match = DBF_FILE_P.match(f)
        if match:
            files.append(f)
    if len(files) == 0:
        logging.error("PBRC log 目录[%s]中没有 dbf log 文件！" % log_dir)
        logging.error("请确认 PB 开启了成交记录生成功能！")
        raise Exception("PBRC Log Do Not Exists!")
    files.sort()
    latest = files[-1]
    match = DBF_FILE_P.match(latest)
    log_day = match.group(1)
    if log_day != TODAY:
        logging.warning("成交记录日志日期[%s]与当前日期[%s]不符" % (log_day, TODAY))
    dbf_file = log_dir + latest
    logging.info("当前最新日志文件是[%s]" % dbf_file)

    ip_port = "%s:%s" % (ip, port)
    len_short = len(server_name)
    len_long = len(server_name.encode('utf-8'))
    len_right = int((len_long - len_short) / 2 + len_short)
    server_name = " " * (29-len_right) + server_name

    logging.info("+--------------------------------------------+")
    logging.info("|           风控服务端开始提供服务           |")
    logging.info("| 版本号     =             V3.1, REL20180927 |")
    logging.info("| 服务器名称 = %s |" % server_name)
    logging.info("| ip:port    = %29s |" % ip_port)
    logging.info("+--------------------------------------------+")
    main_obj = Handler(traders_info, dbf_file, costs, ip, port)

