import sip
#from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import threading
import time
import sys
import socket
import pickle
import io
import numpy
import traceback as tb

try:
    _fromUtf8 = QString.fromUtf8
except AttributeError:
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

    def setupText(self,Form,n=3,m=3,resize = True, bgColor = None):
        self.textBrowsers = []
        for i in range(n):
            row = []
            for j in range(m):
                temp = QTextBrowser(Form)
                temp.setGeometry(QRect(j*80,i*30, 80, 30))
                temp.setObjectName(_fromUtf8("textBrowser"+str(i)+str(j)))
                if bgColor:
                    #temp.setTextBackgroundColor(QColor.fromRgb(255, 0, 0))
                    temp.setTextBackgroundColor(bgColor)
                temp.show()
                row.append(temp)
            self.textBrowsers.append(row)
        if resize:
            Form.setFixedSize(m*80,n*30)

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

    def __init__(self,path,name):
        ip_address,port = path
        print('Connecting...')
        self.connect_server(ip_address,port)

        self.name = name
        self.total_record = []
        self.on_sending = False
        self.on_closing = False
        self.connected = False

    def connect_server(self,ip_address,port):
        try:
            self.s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.s.connect((ip_address,port))
            return True
        except:
            tb.print_exc()
            return False

    def showgui(self):
        widget = MyWidget()
        win = Ui_Form()
        win.setupUi(widget)
        widget.setWindowTitle(_translate("Form", self.name+"_Humans", None))

        pushButton = QPushButton(widget)
        pushButton.setGeometry(QRect(0, 0, 80, 30))
        pushButton.setObjectName(_fromUtf8("pushButton"))
        pushButton.setText(_translate("Form", "Detail", None))
        pushButton.setVisible(False)
        pushButton.clicked.connect(self.show_stock_status)
        win.pushButton = pushButton

        widget.show()
        widget.On_refresh.connect(self.refresh,Qt.QueuedConnection)

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

    def set_texts(self,data,win):
        for i in range(len(win.textBrowsers)):
            row = win.textBrowsers[i]
            for j in range(len(row)):
                item = row[j]
                try:
                    text = unicode(data[i][j])
                except:
                    text = ""
                item.setText(text)

    def refresh(self, data):
        self.win.pushButton.setVisible(True)
        record, status = data
        try:
            if len(self.win.textBrowsers) != len(record):
                self.win.destroyText()
                self.win.setupText(self.widget, len(record), 3, resize = False)
        except Exception as e:
            print(e)
            self.win.destroyText()
            self.win.setupText(self.widget, len(record), 3, resize = False)
        self.win.pushButton.setGeometry(QRect(0, len(record)*30, 80, 30))
        self.set_texts(record,self.win)
        self.widget.setFixedSize(240,(len(record)+1)*30)

        try:
            if self.widget2.isVisible():
                if len(status) != len(self.win2.textBrowsers):
                    self.win2.destroyText()
                    self.win2.setupText(self.widget2,len(status),8)
                self.set_texts(status,self.win2)
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
            self.win2.setupText(self.widget2,len(status),8)
            self.set_texts(status,self.win2)

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
            tb.print_exc()

    def timer(self,interval = 1):
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
                text,record,status = pickle.loads(data)
                self.connected = True
            except Exception as e:
                print(e)
                self.on_sending = False
                self.s.close()
                self.connected = False
                print('Reconnecting...')
                self.connect_server(ip_address,port)
                time.sleep(interval)
                continue
            self.on_sending = False
            self.widget.On_refresh.emit([record,status])
            time.sleep(interval)


def load_params(args):
    start_flag = False
    dic = {}
    for i in range(len(args)):
        temp = args[i].replace(' ','').lower()
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
    app = QApplication( sys.argv )

    stop_loss_file = io.open('stop_loss.ini', 'r')
    stop_loss_dic = load_stop_loss_dic(stop_loss_file)
    for entry in stop_loss_dic:
        print(entry + " : %d" % stop_loss_dic[entry])

    file = io.open('setting.ini','r')
    args = file.read().split('\n')
    file.close()
    dic = load_params(args)
    name = dic['name']
    ip_address,port = dic['ip'],int(dic['port'])
    main_obj = main((ip_address,port),name)
    main_obj.showgui()

    t = threading.Thread(target = main_obj.timer)
    t.setDaemon(True)
    t.start()

    app.aboutToQuit.connect(main_obj.on_app_close)

    sys.exit(app.exec_())

