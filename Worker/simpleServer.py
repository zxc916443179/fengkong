import argparse
import json
import logging
import sys
import time
from threading import Thread
from typing import Dict, List

from PyQt5 import QtWidgets

from common import conf
from common.message_queue_module import Message, MsgQueue
from common.rpc_queue_module import RpcQueue
from common_server.data_module import DataCenter
from common_server.thread_pool_module import ThreadPool
from common_server.timer import TimerManager
from network.netStream import NetStream
from Controller import Controller

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


class RedirectorIO(object):
    '''
    重定向标准输出
    添加一些信息方便debug
    '''
    origin_out = sys.stdout

    def __init__(self, filename="") -> None:
        super(RedirectorIO).__init__()
        self.filename = filename
        self.newline = True
        # self.logger = logging.getLogger()

    def write(self, out_stream):
        if out_stream == "\n":
            self.origin_out.write(out_stream)
            self.newline = True
            return
        # self.logger.info(out_stream)
        if self.newline:
            stack = sys._getframe(1)
            timeStr = time.strftime("%Y/%m/%d %H:%M:%S %p", time.localtime())
            prefix = "%s - PRINT[%s:%s %s] - " % (timeStr, stack.f_code.co_filename,
                                       stack.f_lineno, stack.f_code.co_name)
            self.origin_out.write(prefix + out_stream)
            self.newline = False
        else:
            self.origin_out.write(out_stream)

    def flush(self):
        pass


class Worker(Thread):
    def __init__(self, config=None):
        super(Worker, self).__init__()
        # type: (argparse.Namespace) -> None
        self.config = config

        self.data_center = DataCenter()
        self.data_center.setConfig(config)
        self.retry_times = 10
        self.netstream = NetStream()
        self.netstream.connect(self.data_center.getCfgValue("client", "ip"), self.data_center.getCfgValue("client", "port"))
        self.logger = logging.getLogger(__name__)
        self.queue = []  # type: List
        self.state = 0
        self.max_consume = 10
        self.message_queue = MsgQueue()
        self.rpc_queue = RpcQueue()

    def run(self):
        try:
            while 1:
                self.tick()
        except Exception as e:
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
                try:
                    info = json.loads(data)
                    self.message_queue.push_msg(0,
                                                Message(info["method"], wparam, info["args"], info["kwargs"]))
                except:
                    self.logger.error("parse json failed, pass", data)
                    continue

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
    sys.stdout = RedirectorIO()
    import os

    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="enable debug mode")
    parser.add_argument("--verbose", "-v", action="store_true", help="enable verbose mode")
    parser.add_argument("--config_file", default="conf/setting.ini", type=str)
    parser.add_argument("--worker_id", default=0)
    arguments = parser.parse_args()
    if not os.path.exists("logs"):
        os.mkdir("logs")
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
    try:
        app = QtWidgets.QApplication(sys.argv)
        controller = Controller()
        worker = Worker(config=arguments)
        worker.start()

        thread_pool = ThreadPool()
        thread_pool.start()

        controller.showMainWindows()
        TimerManager.addRepeatTimer(10, worker.heartbeat)
        code = app.exec_()
        thread_pool.stop()
        sys.exit(code)
    except Exception as e:
        logger.error("", exc_info=True)
