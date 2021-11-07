from pandas.core.frame import DataFrame
import os, logging, re
from dbfread import DBF
import numpy as np
import pandas as pd
import csv


PATTERN = re.compile(r'Trealdeal_\d{8}\.log')


class Reader(object):
    def __init__(self, mid_dir, log_dir, mid_csv_file, final_csv_file, names_to_account) -> None:
        self.logger = logging.getLogger()
        self.mid_dir = mid_dir
        self.log_dir = log_dir
        self.mid_csv_file = mid_csv_file
        self.final_csv_file = final_csv_file
        self.names_to_account = names_to_account
        if not os.path.exists(self.log_dir):
            self.logger.error(u"没找到 pbrc Log 目录[%s]！" % self.log_dir)
            raise Exception("Pbrc Log Folder Do Not Exists.")
        if not os.path.exists(self.mid_dir):
            self.logger.warning(u"中间目录[%s]不存在，自动创建。" % self.mid_dir)
            os.mkdir(self.mid_dir)
        self.names_to_account = None
        self.run()  # 初始化的时候先run一遍

    def run(self):
        fileNames = os.listdir(self.log_dir)
        files = []
        for filename in fileNames:
            match = PATTERN.match(filename)
            if match:
                files.append(filename)
        if len(files) == 0:
            self.logger.warning(u"Pbrc Log 目录[%s]中没有 dbf log 文件！" % self.log_dir)
            self.logger.error(u"请确保[%s]目录中有 dbf log 文件后，重新启动程序。" % self.log_dir)
            raise Exception(u"Pbrc Log Do Not Exists.")
        files.sort()
        latestFile = files[-1]
        #self.logger.info(u"解析最近的 dbf log 文件[%s]。" % latestFile)

        # Old style
        #mydf = read_dbf(self.log_dir + latestFile)
        #mydf.to_csv("real/last_dbf.csv", encoding="gb2312", index=True)
        #mydf = get_risk_manage_df(mydf)
        #mydf.to_csv("real/zy01.csv", encoding="gb2312", index=False)

        my_dic = self.transformDbfToCsv(self.log_dir + latestFile)
        #self.logger.info(u"dbf log 文件[%s]解析完成！" % latestFile)
        records = list(my_dic.values())
        #with open('real/zy011.csv', 'w', newline='') as csvfile:
        #self.logger.info(u"dbf log 转化为 csv 文件[%s]。" % mid_csv_file)
        #print(records)
        if len(records) == 0:
            self.logger.warning(u"Pbrc log[%s]中没有成交记录！")
            input(u"按任意键继续。")
            raise Exception("No Entrust Found.")
        with open(self.mid_csv_file, 'w', newline='') as csvfile:
            fieldnames = records[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        csvfile.close()
        #self.logger.info(u"中间文件[%s]写入成功！" % mid_csv_file)

        df = pd.read_csv(self.mid_csv_file, encoding="gb2312")
        names_file = self.names_to_account
        if not os.path.exists(names_file):
            self.logger.error(u"交易员配置文件[%s]没有找到！" % names_file)
            raise Exception("Trader Configuration File Do Not Exists.")
        else:
            #self.logger.info(u"解析交易员配置文件[%s]" % names_file)
            names_df = pd.read_excel(names_file)
            names_df.dropna()
            #self.logger.info(u"重组委托记录。")
            df = self.reassembe(df, names_df)
            #self.logger.info(u"将重组后的委托记录写入最终CSV[%s]中。" % final_csv_file)
            df.to_csv(self.final_csv_file, encoding="gb2312", index=False)

    def reassembe(self, df: DataFrame, names_df: DataFrame) -> DataFrame:
        total_save_head = ['CJSJ', 'TZGW', 'ZQDM', 'CJSL', 'CJJG', 'WTFX'] # Limit head
        df = df.dropna(subset=total_save_head)
        df = df.loc[:, total_save_head]

        # Delete ZQDM = 204001
        total_save_loc = df.ZQDM != 204001
        # Only keep the recorded trader
        account_list = np.unique(list(names_df['Account']))
        save_loc = [x in account_list for x in df.TZGW] # List Comprehension 列表解析
        #for val in df.TZGW:
        #    save_loc.append(val in account_list)
        total_save_loc = np.logical_and(total_save_loc, save_loc)

        self.logger.debug("df size before reassembe: %d" % len(df))
        df = df.loc[total_save_loc, :]
        self.logger.debug("df size after reassembe: %d" % len(df))

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
        for _, row in names_df.iterrows():
            names_dic[row['Account']] = row['Names']
        df["投顾姓名"] = [names_dic[x] for x in df["投顾编号"]]

        return df

    def transformDbfToCsv(self, filepath):
        count = 0
        result = {}
        for record in DBF(filepath, recfactory=dict):
            count += 1
            result[record['CJXH']] = record
        self.logger.debug("There are %s rows in dbf and %s unique rows in dbf" % (count, len(result.keys())))
        return result
