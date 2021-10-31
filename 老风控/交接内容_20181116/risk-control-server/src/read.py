# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
from dbfread import DBF
import datetime
import os
import sys
import re
import time
import traceback as tb
import configparser
import logging
import functools
import csv

TODAY = time.strftime('%Y%m%d',time.localtime(time.time()))

logging.basicConfig(level=logging.DEBUG,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                datefmt='%a, %d %b %Y %H:%M:%S',
                filename='log/read_%s.log'%TODAY,
                filemode='a')


def time_me(fn):
    def _wrapper(*args, **kwargs):
        start = time.clock()
        val = fn(*args, **kwargs)
        logging.info("Time consumed in %s: %s second" % (fn.__name__, time.clock() - start))
        return val
    return _wrapper


@time_me
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

    logging.info("df size before reassembe: %d" % len(df))
    df = df.loc[total_save_loc, :]
    logging.info("df size after reassembe: %d" % len(df))

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


@time_me
def transform_dbf_to_csv(filepath):
    count = 0
    result = {}
    for record in DBF(filepath, recfactory=dict):
        count += 1
        #if record['ZQDM'] == '204001':
        #    continue
        #else:
        #    account = None
        #    try:
        #        account = int(record['TZGW'])
        #    except:
        #        logging.warning('TZGW(%s) cannot is not int' % record['TZGW'])
        #        logging.warning('count: %d, record: %s', (count, record))
        #        continue
        #    result[record['CJXH']] = record
        result[record['CJXH']] = record
    logging.info("There are %s rows in dbf and %s unique rows in dbf" % (count, len(result.keys())))
    return result


@time_me
def read_dbf(filepath, date=None, calc=None):
    df = None
    records = {}
    count = 0
    #for record in DBF(filepath, recfactory=dict): #Method 1, slow down when test
    for record in DBF(filepath):
        count += 1
        if record['ZQDM'] == '204001':
            continue
        else:
            records[record['CJXH']] = record
    for cjxh in records.keys():
        try:
            df = df.append(records[cjxh], ignore_index=True)
        except:
            df = pd.DataFrame(records[cjxh], index=[0])
    logging.info("There are %s rows in dbf and %s unique rows in dbf" % (count, len(df)))
    return df


@time_me
def get_names(names_to_account_file):
    names_data = pd.read_excel(names_to_account_file, encoding="gb2312")
    res = {}
    for idx, row in names_data.iterrows():
        if row['Account']==None or row['Names']==None:
            logging.warning("Either account[%s] or names[%s] is None" % (row['Account'], row['Names']))
            continue
        else:
            try:
                account = int(row['Account'])
                res[account] = row['Names']
            except:
                logging.error(tb.format_exc())
    return res


@time_me
def get_risk_manage_df(ipt):
    ipt = ipt.loc[:, ['WTBH', 'CJSJ', 'TZGW', 'ZQDM', 'CJSL', 'CJJG', 'WTFX']]
    loc = ipt['WTFX'].values == '1'
    ipt.loc[loc, 'WTFX'] = '买入'
    loc = ipt['WTFX'].values == '2'
    ipt.loc[loc, 'WTFX'] = '卖出'

    names_dic = get_names("conf/names_to_account.xlsx")
    accounts = names_dic.keys()

    cols = {}
    cols['CJSJ'] = '委托时间'
    cols['TZGW'] = '投顾姓名'
    cols['ZQDM'] = '证券代码'
    cols['CJSL'] = '成交数量'
    cols['CJJG'] = '成交均价'
    cols['WTFX'] = '操作'
    cols['WTBH'] = '委托编号'
    ipt.rename(columns = cols, inplace=True)
    ipt['理财产品'] = '致远1号'
    ipt['投顾编号'] = 'Converted'
    ipt['状态'] = '已转换'
    ipt['证券名称'] = ipt['证券代码']
    #ipt['委托编号'] = 'BNS000'
    #ipt["投顾姓名"] = get_names(ipt["投顾姓名"].values)
    return ipt


pattern = re.compile(r'Trealdeal_\d{8}\.log')


@time_me
def main():
    logging.info("compute")
    config = configparser.ConfigParser()
    logDir = 'Logs/'
    fileNames = os.listdir(logDir)
    files = []
    for filename in fileNames:
        match = pattern.match(filename)
        if match:
            files.append(filename)
    if len(files) == 0:
        logging.warning("Dbf log do not exists in %s" % logDir)
        return
    files.sort()
    latestFile = files[-1]
    logging.info("Reading latest file[%s]" % latestFile)

    # Old style
    #mydf = read_dbf(logDir + latestFile)
    #mydf.to_csv("real/last_dbf.csv", encoding="gb2312", index=True)
    #mydf = get_risk_manage_df(mydf)
    #mydf.to_csv("real/zy01.csv", encoding="gb2312", index=False)

    my_dic = transform_dbf_to_csv(logDir + latestFile)
    records = list(my_dic.values())
    #with open('real/zy011.csv', 'w', newline='') as csvfile:
    with open('real/zy011.csv', 'w', newline='') as csvfile:
        fieldnames = records[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    csvfile.close()
    logging.info("med file zy011.csv write success")

    df = pd.read_csv("real/zy011.csv", encoding="gb2312")
    names_df = pd.read_excel("conf/names_to_account.xlsx", encoding="gb2312")
    names_df.dropna()
    df = reassembe(df, names_df)
    df.to_csv("real/zy01.csv", encoding="gb2312")


if __name__ == '__main__':
    logging.info("sys args: %s" % sys.argv)
    if len(sys.argv)==2 and sys.argv[1] == 'debug':
        logging.info("debugging")
        main()
    else:
        while 1:
            try:
                main()
            except Exception as e:
                logging.error(tb.format_exc())
                raise e

