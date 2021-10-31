# -*- coding: utf-8 -*-

from dbfread import DBF

import os
import re
import sys
import csv
import time
import codecs
import logging
import functools
import configparser

import numpy as np
import pandas as pd
import traceback as tb

if not os.path.exists('log/'):
    os.mkdir('log/')

TODAY = time.strftime('%Y%m%d',time.localtime(time.time()))

#logging.basicConfig(level=logging.DEBUG,
logging.basicConfig(level=logging.INFO,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                datefmt='%a, %d %b %Y %H:%M:%S',
                filename='log/reader_%s.log'%TODAY,
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


#@time_me
def reassembe(df, names_df):
    total_save_head = ['CJSJ', 'TZGW', 'ZQDM', 'CJSL', 'CJJG', 'WTFX'] # Limit head
    df = df.dropna(subset=total_save_head)
    df = df.ix[:, total_save_head]

    # Delete ZQDM = 204001
    total_save_loc = df.ZQDM != 204001
    # Only keep the recorded trader
    account_list = np.unique(list(names_df['Account']))
    save_loc = [x in account_list for x in df.TZGW] # List Comprehension 列表解析
    #for val in df.TZGW:
    #    save_loc.append(val in account_list)
    total_save_loc = np.logical_and(total_save_loc, save_loc)

    logging.debug("df size before reassembe: %d" % len(df))
    df = df.loc[total_save_loc, :]
    logging.debug("df size after reassembe: %d" % len(df))

    loc = df.WTFX == 1
    df.loc[loc, 'WTFX'] = '买入'
    loc = df.WTFX == 2
    df.loc[loc, 'WTFX'] = '卖出'

    cols = {}
    cols['CJSJ'] = '委托时间'
    cols['TZGW'] = '投顾编号'
    cols['ZQDM'] = '证券代码'
    cols['CJSL'] = '成交数量'
    cols['CJJG'] = '成交均价'
    cols['WTFX'] = '操作'
    cols['WTBH'] = '委托编号'
    df.rename(columns = cols, inplace=True)

    df['理财产品'] = '致远1号'
    df['状态'] = '已转换'
    df['证券名称'] = df['证券代码']
    df['委托编号'] = 'BNS000'

    names_dic = {}
    for idx, row in names_df.iterrows():
        names_dic[row['Account']] = row['Names']
    df["投顾姓名"] = [names_dic[x] for x in df["投顾编号"]]

    return df


#@time_me
def transform_dbf_to_csv(filepath):
    count = 0
    result = {}
    for record in DBF(filepath, recfactory=dict):
        count += 1
        result[record['CJXH']] = record
    logging.debug("There are %s rows in dbf and %s unique rows in dbf" % (count, len(result.keys())))
    return result


PATTERN = re.compile(r'Trealdeal_\d{8}\.log')


#@time_me
def main(cfgfile):
    #logging.info(u"解析配置文件[%s]。" % cfgfile)
    cf = configparser.ConfigParser()
    with codecs.open(cfgfile, 'r', encoding="utf-8") as f:
        cf.readfp(f)
    program_name = cf.get("reader", "program_name")
    logging.info(u"程序名：%s" % program_name)
    logDir = cf.get("reader", "log_dir")
    midDir = cf.get("reader", "mid_dir")
    if not os.path.exists(logDir):
        logging.error(u"没找到 pbrc Log 目录[%s]！" % logDir)
        raise Exception("Pbrc Log Folder Do Not Exists.")
    if not os.path.exists(midDir):
        logging.warning(u"中间目录[%s]不存在，自动创建。" % midDir)
        os.mkdir(midDir)
    fileNames = os.listdir(logDir)
    files = []
    for filename in fileNames:
        match = PATTERN.match(filename)
        if match:
            files.append(filename)
    if len(files) == 0:
        logging.warning(u"Pbrc Log 目录[%s]中没有 dbf log 文件！" % logDir)
        logging.error(u"请确保[%s]目录中有 dbf log 文件后，重新启动程序。" % logDir)
        raise Exception(u"Pbrc Log Do Not Exists.")
    files.sort()
    latestFile = files[-1]
    #logging.info(u"解析最近的 dbf log 文件[%s]。" % latestFile)

    # Old style
    #mydf = read_dbf(logDir + latestFile)
    #mydf.to_csv("real/last_dbf.csv", encoding="gb2312", index=True)
    #mydf = get_risk_manage_df(mydf)
    #mydf.to_csv("real/zy01.csv", encoding="gb2312", index=False)

    my_dic = transform_dbf_to_csv(logDir + latestFile)
    #logging.info(u"dbf log 文件[%s]解析完成！" % latestFile)
    records = list(my_dic.values())
    #with open('real/zy011.csv', 'w', newline='') as csvfile:
    mid_csv_file = midDir + cf.get("reader", "mid_csv_file")
    #logging.info(u"dbf log 转化为 csv 文件[%s]。" % mid_csv_file)
    #print(records)
    if len(records) == 0:
        logging.warning(u"Pbrc log[%s]中没有成交记录！")
        input(u"按任意键继续。")
        raise Exception("No Entrust Found.")
    with open(mid_csv_file, 'w', newline='') as csvfile:
        fieldnames = records[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    csvfile.close()
    #logging.info(u"中间文件[%s]写入成功！" % mid_csv_file)

    df = pd.read_csv(mid_csv_file, encoding="gb2312")
    names_file = cf.get("input", "names")
    if not os.path.exists(names_file):
        logging.error(u"交易员配置文件[%s]没有找到！" % names_file)
        raise Exception("Trader Configuration File Do Not Exists.")
    else:
        #logging.info(u"解析交易员配置文件[%s]" % names_file)
        names_df = pd.read_excel(names_file, encoding="gb2312")
        names_df.dropna()
        #logging.info(u"重组委托记录。")
        df = reassembe(df, names_df)
        final_csv_file = midDir + cf.get("reader", "final_csv_file")
        #logging.info(u"将重组后的委托记录写入最终CSV[%s]中。" % final_csv_file)
        df.to_csv(final_csv_file, encoding="gb2312", index=False)


if __name__ == '__main__':
    if len(sys.argv)==1:
        # default reader.ini
        cfgfile = "conf/setting.ini"
    elif len(sys.argv)==2:
        cfgfile = sys.argv[1]
    else:
        logging.error(u"程序调用错误！")
        raise Exception(u"Program Usage Error.")
    if not os.path.exists(cfgfile):
        logging.error(u"指定的配置文件[%s]不存在！" % cfgfile)
        raise Exception("Configuration File Do Not Exists.")
    else:
        logging.info(u"指定配置文件[%s]。" % cfgfile)
        while 1:
            try:
                main(cfgfile)
            except Exception as e:
                logging.debug(tb.format_exc())
                raise e


