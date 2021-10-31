# -*- coding: utf-8 -*-

from riskmanage import *
from gevent.pool import Pool

import io
import sys
import time
import socket
import pickle
import gevent
import codecs
import logging
import gevent.monkey

import traceback as tb

gevent.monkey.patch_all()

if not os.path.exists('log/'):
    os.mkdir('log/')

TODAY = time.strftime('%Y%m%d',time.localtime(time.time()))

#logging.basicConfig(level=logging.DEBUG,
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


#class Logger():
#
#    def __init__(self):
#        self.lock = False
#        current_day = time.strftime("%Y%m%d", time.localtime())
#        self.file_name = './log/ServerLog-' + current_day + '.log'
#
#    def add_log(self, data):
#        while self.lock:
#            gevent.sleep(0.1)
#        self.lock = True
#        try:
#            file = io.open(self.file_name,'a')
#            log_content = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
#            log_content = "[%s] %s" % (log_content, data)
#            print(log_content)
#            file.write(log_content + '\n')
#            file.close()
#        except Exception as e:
#            print(e)
#            print('Logger_Error')
#        self.lock = False
#
#    def close_log(self):
#        self.file.close()

class Handler():

    def __init__(self, mid_csv_file, names_to_account, costs, ip, port):
        self.rm = riskmanage(mid_csv_file, names_to_account, costs)
        self.lock = False
        self.rm.renew_status()
        self.new_data = self.rm.get_current_status2()
        self.init_server(ip, port)
        #self.logger = Logger()
        self.pool = Pool()
        self.pool.add(gevent.spawn(self.renew_obj))
        self.pool.add(gevent.spawn(self.create_conn))
        self.pool.join()

    def renew_obj(self):
        while 1:
            gevent.sleep(3)
            while self.lock:
                gevent.sleep(0.1)
            self.lock = True
            try:
                self.rm.renew_status()
                self.new_data = self.rm.get_current_status2()
                logging.debug("Data Recieved.")
                #self.logger.add_log('Data Recieved')
            except:
                logging.warning("Error at renew_obj")
                logging.warning(tb.format_exc())
                logging.warning('file may not be available now')
                #self.logger.add_log('Error at renew_obj')
                #self.logger.add_log(tb.format_exc())
                #self.logger.add_log('file may not be available now')
            self.lock = False

    def init_server(self, ip, port):
        HOST = ip
        PORT = port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        self.soc = s

    def create_conn(self):
        while 1:
            try:
                logging.debug("Waiting for connection.")
                #self.logger.add_log('Waiting for connection')
                conn, addr = self.soc.accept()
                conn.settimeout(5)
                logging.info("New Connection Address is %s" % str(addr))
                #self.logger.add_log('New Connection Address is ' + str(addr))
                self.pool.add(gevent.spawn(self.handle_new_conn, conn, addr))
            except:
                logging.warning('Error at create_conn')
                logging.warning(tb.format_exc())
                logging.warning('Connection Creation failed')
                #self.logger.add_log('Error at create_conn')
                #self.logger.add_log(tb.format_exc())
                #self.logger.add_log('Connection Creation failed')

    def concat_list(self, l, split=","):
        temp = ""
        for i in l:
            temp += str(i)+split
        return temp[:-1]

    def handle_new_conn(self, conn, addr):
        while 1:
            try:
                with gevent.Timeout(5, True) as timeout:
                    data = conn.recv(1024)
                data = data.decode('utf-8')
                if len(data) == 0:
                    logging.info('Connection of %s Closed' % str(addr) )
                    #self.logger.add_log('Connection of ' + str(addr) + ' Closed')
                    break
                elif data == 'request_web':
                    while self.lock:
                        gevent.sleep(0.1)
                    # old version
                    #temp = self.new_data[0].replace('\n','<br>')

                    # new version
                    str1 = self.new_data[0]
                    str2 = self.new_data[1]
                    str1 = [self.concat_list(x) for x in str1]
                    str2 = [self.concat_list(x) for x in str2]
                    temp = "|".join(str1)+"\n"+"|".join(str2)
                    print(temp)

                    with gevent.Timeout(5,True) as timeout:
                        conn.sendall(temp.encode('utf-8'))
                elif data == 'request':
                    while self.lock:
                        gevent.sleep(0.1)
                    with gevent.Timeout(5,True) as timeout:
                        conn.sendall(pickle.dumps(self.new_data, protocol=2))
                elif data == 'request_split':
                    while self.lock:
                        gevent.sleep(0.1)
                    with gevent.Timeout(5,True) as timeout:
                        conn.sendall(pickle.dumps(self.new_data, protocol=2) + b'\x00\x00\xee\xee\x00\x00')
                elif data == 'close':
                    conn.sendall('ok'.encode('utf-8'))
                    logging.info('Connection of %s Closed!' % str(addr) )
                    #self.logger.add_log('Connection of ' + str(addr) + ' Closed')
                    break
            except:
                logging.warning('Error at handle_mew_conn')
                logging.warning('Address is %s.' % str(addr))
                logging.warning(tb.format_exc())
                #self.logger.add_log('Error at handle_mew_conn')
                #self.logger.add_log('Address is ' + str(addr))
                #self.logger.add_log(tb.format_exc())
                break
        conn.close()

if __name__ == '__main__':
    if (len(sys.argv) == 1):
        cfgfile = "conf/setting.ini"
    elif (len(sys.argv) == 2):
        cfgfile = sys.argv[1]
    else:
        logging.error(u"程序调用错误！")
        raise Exception(u"Program Usage Error.")
    if os.path.exists(cfgfile):
        logging.debug(u"指定配置文件[%s]。" % cfgfile)
        config = configparser.ConfigParser()
        config.readfp(codecs.open(cfgfile, "r", "utf-8-sig"))
        name = str(config['input']['name'])
        mid_csv_file = config['input']['mid_csv_file']
        names_to_account = config['input']['names']
        ip = config['input']['ip']
        port = int(config['input']['port'])
        costs = None
    else:
        logging.error(u"指定的配置文件[%s]不存在！" % cfgfile)
        raise Exception("Configuration File Do Not Exists.")
    logging.info("Server name: %s" % name)
    logging.info("Listening on %s:%d" %(ip, port))
    main_obj = Handler(mid_csv_file, names_to_account, costs, ip, port)

