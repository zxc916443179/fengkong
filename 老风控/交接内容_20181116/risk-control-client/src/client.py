# -*- coding: utf-8 -*-

import PyQt5
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

import io
import os
import sys
import time
import socket
import pickle
import logging
import threading

import numpy as np
import traceback as tb

#if os.name == "nt":
#    pyqt_plugins = os.path.join(os.path.dirname(PyQt5.__file__),
#            "..", "..", "..", "Library", "plugins")
#    QApplication.addLibraryPath(pyqt_plugins)

if not os.path.exists('log/'):
    os.mkdir('log/')

TODAY = time.strftime('%Y%m%d',time.localtime(time.time()))

logging.basicConfig(level=logging.DEBUG,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                datefmt='%a, %d %b %Y %H:%M:%S',
                filename='log/client%s.log'%TODAY,
                filemode='a')


def _fromUtf8(s):
    return s

try:
    _encoding = QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig)


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName(_fromUtf8("Form"))
        Form.resize(240, 30)

        self.retranslateUi(Form)
        QMetaObject.connectSlotsByName(Form)
        self.textBrowsers = []

    def setupText(self, Form, n=3, m=3, resize=True, bgColor=None):
        self.textBrowsers = []
        for i in range(n):
            row = []
            for j in range(m):
                temp = QTextBrowser(Form)
                temp.setGeometry(QRect(j*80, i*30, 80, 30))
                temp.setObjectName(_fromUtf8("textBrowser"+str(i)+str(j)))
                if bgColor:
                    #temp.setTextBackgroundColor(QColor.fromRgb(255, 0, 0))
                    temp.setTextBackgroundColor(bgColor)
                temp.show()
                row.append(temp)
            self.textBrowsers.append(row)
        if resize:
            Form.setFixedSize(m*80, n*30)

    def destroyText(self):
        for row in self.textBrowsers:
            for item in row:
                item.close()
                item.destroy()
        self.textBrowsers = []

    def retranslateUi(self, Form):
        Form.setWindowTitle(_translate("Form", "Form", None))


class MyWidget(QWidget):

    def __init__(self):
        QWidget.__init__(self, None, Qt.WindowStaysOnTopHint)

    On_refresh = pyqtSignal([list])


class main():

    def __init__(self, path, name):
        ip_address, port = path
        logging.info('Connecting to %s:%d' % path)
        self.connect_server(ip_address, port)

        self.name = name
        self.total_record = []
        self.on_sending = False
        self.on_closing = False
        self.connected = False

    def connect_server(self, ip_address, port):
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.connect((ip_address, port))
            return True
        except:
            ErrorMsg = tb.format_exc()
            logging.warning(ErrorMsg)
            return False

    def showgui(self):
        widget = MyWidget()
        win = Ui_Form()
        win.setupUi(widget)
        widget.setWindowTitle(_translate("Form", self.name + "_Humans", None))

        pushButton = QPushButton(widget)
        pushButton.setGeometry(QRect(0, 0, 80, 30))
        pushButton.setObjectName(_fromUtf8("pushButton"))
        pushButton.setText(_translate("Form", "Detail", None))
        pushButton.setVisible(False)
        pushButton.clicked.connect(self.show_stock_status)
        win.pushButton = pushButton

        widget.show()
        widget.On_refresh.connect(self.refresh, Qt.QueuedConnection)

        self.win = win
        self.widget = widget

        widget2 = MyWidget()
        win2 = Ui_Form()
        win2.setupUi(widget2)
        widget2.setWindowTitle(_translate("Form", self.name+"_Stocks", None))
        self.win2 = win2
        self.widget2 = widget2

    def show_stock_status(self):
        self.load_pre_stock_status()
        self.widget2.show()

    def stock_status_closed(self):
        pass

    def set_texts(self, data, win):
        for i in range(len(win.textBrowsers)):
            row = win.textBrowsers[i]
            for j in range(len(row)):
                item = row[j]
                try:
                    text = str(data[i][j])
                except:
                    text = ""
                if text=='*':
                    item.setTextBackgroundColor(QColor.fromRgb(255, 255, 0))
                    item.setText('*         ')
                elif text=='**':
                    item.setTextBackgroundColor(QColor.fromRgb(255, 69, 0))
                    item.setText('**        ')
                elif text=='***':
                    item.setTextBackgroundColor(QColor.fromRgb(255, 0, 0))
                    item.setText('***       ')
                else:
                    item.setText(text)

    def refresh(self, data):
        self.win.pushButton.setVisible(True)
        record, status = data
        try:
            if len(self.win.textBrowsers) != len(record):
                self.win.destroyText()
                self.win.setupText(self.widget, len(record), 4, resize = False)
        except Exception as e:
            #print(e)
            logging.warning(tb.format_exc())
            self.win.destroyText()
            self.win.setupText(self.widget, len(record), 4, resize = False)
        self.win.pushButton.setGeometry(QRect(0, len(record)*30, 80, 30))
        self.set_texts(record, self.win)
        self.widget.setFixedSize(320, (len(record)+1)*30)

        try:
            if self.widget2.isVisible():
                if len(status) != len(self.win2.textBrowsers):
                    self.win2.destroyText()
                    self.win2.setupText(self.widget2, len(status), 8)
                self.set_texts(status, self.win2)
            else:
                self.stock_status_closed()
        except:
            self.stock_status_closed()
        self.record = record
        self.status = status
        self.total_record.append(int(record[-1][-1]))

    def load_pre_stock_status(self):
        status = self.status
        self.win2.destroyText()
        if len(status) != 0:
            self.win2.setupText(self.widget2, len(status), 8)
            self.set_texts(status, self.win2)

    def on_app_close(self):
        self.on_closing = True
        while self.on_sending:
            time.sleep(0.1)
        try:
            if self.connected:
                self.s.sendall('close'.encode('utf-8'))
                data = self.s.recv(1024).decode('utf-8')
                if data == 'ok':
                    return
                else:
                    raise Exception('exit error')
        except:
            ErrorMsg = tb.format_exc()
            logging.warning(ErrorMsg)

    def timer(self, interval = 1):
        while True:
            if self.on_closing:
                break
            self.on_sending = True
            try:
                self.s.sendall('request_split'.encode('utf-8'))
                data = b''
                temp = self.s.recv(1024)
                while temp[-6:] != b'\x00\x00\xee\xee\x00\x00' and temp != b'':
                    data += temp
                    temp = self.s.recv(1024)
                data += temp[:-6]
                record, status = pickle.loads(data)
                self.connected = True
            except Exception as e:
                #print(e)
                logging.warning(tb.format_exc())
                self.on_sending = False
                self.s.close()
                self.connected = False
                #print('Reconnecting...')
                logging.warning('Reconnecting...')
                self.connect_server(ip_address, port)
                time.sleep(interval)
                continue
            self.on_sending = False
            self.widget.On_refresh.emit([record, status])
            time.sleep(interval)


def load_params(args):
    start_flag = False
    dic = {}
    for i in range(len(args)):
        temp = args[i].replace(' ', '').lower()
        if start_flag:
            if len(temp) > 0:
                temp = temp.split('=')
                dic[temp[0]] = temp[1]
        if temp == '[global]':
            start_flag = True
    return dic


def load_stop_loss_dic(stop_loss_file):
    dic = {}
    lines = stop_loss_file.readlines()
    for line in lines:
        name, value = line.split(' ')
        dic[name] = (int)(value)
    return dic


if __name__ == '__main__':
    app = QApplication([])

    arg_num = len(sys.argv)
    if arg_num == 1:
        logging.info("No setting file specified.")
        if os.path.exists('conf/setting.ini'):
            file = io.open('conf/setting.ini', 'r')
            args = file.read().split('\n')
            file.close()
            dic = load_params(args)
            name = dic['name']
            ip_address, port = dic['ip'], int(dic['port'])
        else:
            logging.error("Default setting file do not exists!")
    elif arg_num == 2:
        logging.info("Setting file specified: %s" % sys.argv[1])
        if os.path.exists(sys.argv[1]):
            file = io.open(sys.argv[1], 'r')
            file = io.open('conf/setting.ini', 'r')
            args = file.read().split('\n')
            file.close()
            dic = load_params(args)
            name = dic['name']
            ip_address, port = dic['ip'], int(dic['port'])
        else:
            logging.error("Specified setting file do not exists!")

    logging.info("name=%s" % name)
    logging.info("ip_address=%s" % ip_address)
    logging.info("port=%d" % port)
    if ip_address == None or port == None:
        logging.error("Either ip_address or port is None!")
    else:
        main_obj = main((ip_address, port), name)
        main_obj.showgui()
        t = threading.Thread(target = main_obj.timer)
        t.setDaemon(True)
        t.start()
        app.aboutToQuit.connect(main_obj.on_app_close)
        sys.exit(app.exec_())
