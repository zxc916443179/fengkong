import argparse
import json
import logging
import sys
import time
from threading import Thread
from typing import Dict, List

from PyQt5 import QtCore, QtWidgets

from common import conf
from common.message_queue_module import Message, MsgQueue
from common.rpc_queue_module import RpcQueue
from common_server.data_module import DataCenter
from common_server.thread_pool_module import ThreadPool
from common_server.timer import TimerManager
from network.netStream import NetStream
from ui_folder.uiDetailPage import uiDetailWindow
from ui_folder.uiWidget import uiWidgetWindow


def parseRpcMessage(method, targets, args, kwargs):
    # type: (str, List[int], List[object], Dict) -> Dict
    if not kwargs.__contains__("code"):
        kwargs["code"] = 0
    if not kwargs.__contains__("msg"):
        kwargs["msg"] = conf.RET_CODE_MAP[kwargs["code"]]
    data = {
        "method": method,
        "targets": targets,
        "args": args,
        "kwargs": kwargs
    }
    return data

class Controller(object):
    def __init__(self, info: dict):
        self.logger = print
        self.windows = []
        self.details = []
        self.info = info
        self.data_center = DataCenter()
        pass
    
    def showMainWindows(self):
        for i, v in self.info.items():
            self.show_mainUi(i, v['main'], v['detail'])
        
    def show_mainUi(self, key, mainList, detailList):
        mainUi = MyMainForm(key, mainList)
        mainUi.switch_Detail.connect(lambda:self.show_detailUi(detailList))
        mainUi.show()
        TimerManager.addRepeatTimer(1.0, mainUi.update)
        self.windows.append(mainUi)

    def show_detailUi(self, datailList):
        detailUi = DetailWindow(datailList)
        self.details.append(detailUi)
        return detailUi.show()
    
    def destroyAllWindows(self):
        for detail in self.details:
            detail.close()
            del detail
        for main in self.windows:
            main.close()
            del main

def saveItem(data, QTableWidgetItem, formWindow):
    for i in range(len(data)):
        for j in range(len(data[i])):
            if data[i][j] != None:
                save=str(data[i][j])
                newItem = QTableWidgetItem(save)
                formWindow.tableWidget.setItem(i,j,newItem)

class MyMainForm(QtWidgets.QMainWindow, uiWidgetWindow):
    switch_Detail = QtCore.pyqtSignal()
    def __init__(self, key, mainList):
        super(MyMainForm, self).__init__()
        self.setupUi(self)
        self.setWindowTitle(key)
        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableWidget.setRowCount(len(mainList))
        saveItem(mainList, QtWidgets.QTableWidgetItem, self)
        self.pushButton.clicked.connect(self.goDetail)
    def goDetail(self):
        self.switch_Detail.emit()

    def update(self):
        pass

class DetailWindow(QtWidgets.QMainWindow, uiDetailWindow):
    def __init__(self, detailList):
        super(DetailWindow, self).__init__()
        self.setupUi(self)
        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableWidget.setRowCount(len(detailList))
        saveItem(detailList, QtWidgets.QTableWidgetItem, self)

class Worker(Thread):
    def __init__(self, config=None):
        super(Worker, self).__init__()
        # type: (argparse.Namespace) -> None
        self.config = config
        self.retry_times = 10
        self.netstream = NetStream()
        self.netstream.connect(config.ip, config.port)
        self.logger = logging.getLogger(__name__)
        self.queue = []  # type: List
        self.state = 0
        self.max_consume = 10
        self.message_queue = MsgQueue()
        self.rpc_queue = RpcQueue()
        self.data_center = DataCenter()
        self.data_center.setConfig(config)

    def run(self):
        try:
            while 1:
                self.tick()
        except (KeyboardInterrupt, SystemExit):
            logger.error("", exc_info=True)

    def tick(self, tick_time=0.02):
        if self.state == -1:
            return
        self.netstream.process()
        while self.netstream.status() == conf.NET_STATE_ESTABLISHED:
            data = self.netstream.recv()
            if data == b'':
                break

            self.queue.append((conf.NET_CONNECTION_DATA, self.netstream.hid, data))
        self.consumeMessage()
        self.consumeRpcMessage()
        
        TimerManager.scheduler()

    def consumeMessage(self):
        for _ in range(max(self.max_consume, len(self.queue))):
            if len(self.queue) <= 0:
                return
            code, wparam, data = self.queue[0]
            self.queue = self.queue[1:]
            if code == conf.NET_CONNECTION_LEAVE or self.netstream.state == -1:
                logger.error("失去连接，尝试重连")
                self.state = -1
                self.message_queue.push_msg(0,
                                            Message("closeClient", wparam, [], {}))
                break
            elif code == conf.NET_CONNECTION_DATA:
                info = json.loads(data)
                self.message_queue.push_msg(0,
                                            Message(info["method"], wparam, info["args"], info["kwargs"]))

    def consumeRpcMessage(self):
        for _ in range(max(self.max_consume, len(self.rpc_queue))):
            msg = self.rpc_queue.pop_msg()
            if msg is not None:
                self.netstream.send(json.dumps(parseRpcMessage(*msg.parseMsg())))
            else:
                break


    def heartbeat(self):
        data = parseRpcMessage("heartBeat", [-1], [], {})
        self.netstream.send(json.dumps(data))


if __name__ == "__main__":
    import os

    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="enable debug mode")
    parser.add_argument("--verbose", "-v", action="store_true", help="enable verbose mode")
    parser.add_argument("--show_map", "-sm", action="store_true", help="enable debug map mode")
    parser.add_argument("--ip", default="127.0.0.1", type=str)
    parser.add_argument("--port", default=8888, type=int)
    parser.add_argument("--worker_id", default=0, type=int)
    arguments = parser.parse_args()

    if not os.path.exists("logs/log_%d" % arguments.worker_id):
        os.mkdir("logs/log_%d" % arguments.worker_id)
    else:
        log_files = os.listdir("logs/log_%d" % arguments.worker_id)
        if len(log_files) > 5:
            print("exceed max keep log files, removing")
            for i, log_file in enumerate(log_files):
                os.remove(os.path.join("logs/log_%d" % arguments.worker_id, log_file))
                print("remove file ", os.path.join("logs/log_%d" % arguments.worker_id, log_file))
                if i == 4:
                    break

    LOG_FORMAT = "%(asctime)s - %(levelname)s[%(module)s/%(funcName)s(%(lineno)d)] - %(message)s"
    DATE_FORMAT = "%Y/%m/%d %H:%M:%S %p"

    log_level = logging.DEBUG if arguments.debug else logging.INFO

    logging.basicConfig(filename='logs/log_%d/debug%s.log' % (
        arguments.worker_id, time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())), filemode="w",
                        level=log_level, format=LOG_FORMAT, datefmt=DATE_FORMAT)
    logger = logging.getLogger()
    if arguments.verbose:
        logger.addHandler(logging.StreamHandler())
    worker = Worker(config=arguments)
    worker.start()
    thread_pool = ThreadPool()
    thread_pool.start()
    TimerManager.addRepeatTimer(2, worker.heartbeat)
    app = QtWidgets.QApplication(sys.argv)
    moskInfo = {
        "ppit1": {
            "main":[
                ['a',111,17000,66,],
                ['b',122,18000,33,'good']
                ]
            ,
            "detail":[
                ['long','a',600171, 'shbl', 111, 17000,'66%',],
                ['short','b',600133, 'shbg', 111, 2300,'11%',]
                ] 
            },
        "ppit2": {
            "main":[
                ['c',111,17000,66,],
                ['d',122,18000,33,'good']]
            ,
            "detail":[
                ['long','c',600171, 'shbl', 111, 17000,'66%',],
                ['short','d',600133, 'shbg', 111, 2300,'11%',]
            ]
            }
        }
    controller = Controller(moskInfo)
    controller.showMainWindows()
    sys.exit(app.exec_() & thread_pool.stop())
    
