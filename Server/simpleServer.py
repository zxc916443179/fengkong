import logging
import time

from common import conf
from common.message_queue_module import MsgQueue, Message
from common.rpc_queue_module import RpcMessage, RpcQueue
from common_server.data_module import DataCenter
from common_server.thread_pool_module import ThreadPool
from common_server.timer import TimerManager
from gameEntity import GameEntity
from network.simpleHost import SimpleHost
from setting import keyType
from typing import Dict
from risk_manager.risk_manager import RiskManager
import argparse


class SimpleServer(object):

    def __init__(self, config=None):
        # type: (argparse.Namespace) -> None
        super(SimpleServer, self).__init__()

        self.entities = {}  # type: Dict[int, GameEntity]
        self.host = SimpleHost()
        self.rpc_queue = RpcQueue()
        self.msg_queue = MsgQueue()
        self.data_center = DataCenter()
        self.data_center.setConfig(config)

        self.max_consume = 10
        self.logger = logging.getLogger()

    def startup(self):
        self.host.startup(8888)

    def generateEntityID(self):
        raise NotImplementedError

    def registerEntity(self, entity):
        # type: (GameEntity) -> None
        # eid = self.generateEntityID()
        eid = entity.netstream.hid
        entity.id = eid

        self.entities[eid] = entity
        self.data_center.regClient(eid)

        return

    def syncData(self):
        self.logger.debug("send data to client")
        self.rpc_queue.push_msg(0, RpcMessage("syncData", self.data_center.getClientList(), [], {"data": list(self.data_center.getData())}))

    def tick(self, tick_time=0.02):
        self.data_center.checkZombieClient()
        self.host.process()
        event, wparam, data = self.host.read()
        if event == conf.NET_CONNECTION_NEW:
            self.logger.debug("new client")
            code, client_netstream = self.host.getClient(wparam)
            assert code == 0
            self.registerEntity(GameEntity(client_netstream))

        elif event == conf.NET_CONNECTION_DATA:
            self.entities[wparam].caller.parse_rpc(data)

        if self.entities.__contains__(wparam) and (
                self.entities[wparam].stat == -1 or event == conf.NET_CONNECTION_LEAVE):
            self.entities[wparam].destroy()
            self.host.closeClient(wparam)
            self.entities.pop(wparam)
            self.msg_queue.push_msg(0, Message("closeClient", wparam, (), {}, ""))
            # self.data_center.removePlayer(wparam)
            self.logger.debug("close connect %d" % wparam)

        # process send queue:
        for _ in range(min(self.max_consume, len(self.rpc_queue))):
            msg = self.rpc_queue.pop_msg()
            if msg is not None:
                method, targets, args, kwargs = msg.parseMsg()
                for target in targets:
                    if self.entities.__contains__(target) and self.data_center.isClientAlive(target):
                        self.entities[target].caller[method](*args, **kwargs)
        return


if __name__ == "__main__":
    import os

    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="enable debug mode")
    parser.add_argument("--verbose", "-v", action="store_true", help="enable verbose mode")
    parser.add_argument("--config_file", "-cfg", default="conf/setting.ini")
    arguments = parser.parse_args()

    if not os.path.exists("log"):
        os.mkdir("log")
    else:
        log_files = os.listdir("log")
        if len(log_files) > 5:
            print("exceed max keep log files, removing")
            for i, log_file in enumerate(log_files):
                os.remove(os.path.join("log", log_file))
                print("remove file ", os.path.join("log", log_file))
                if i == 4:
                    break

    LOG_FORMAT = "%(asctime)s - %(levelname)s[%(module)s/%(funcName)s(%(lineno)d)] - %(message)s"
    DATE_FORMAT = "%Y/%m/%d %H:%M:%S %p"
    print(arguments.debug, arguments.verbose)
    log_level = logging.DEBUG if arguments.debug else logging.INFO

    logging.basicConfig(filename='log/debug%s.log' % time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()), filemode="w",
                        level=log_level, format=LOG_FORMAT, datefmt=DATE_FORMAT)
    logger = logging.getLogger()
    if arguments.verbose:
        logger.addHandler(logging.StreamHandler())
    server = SimpleServer(config=arguments)
    server.startup()
    thread_pool = ThreadPool()
    thread_pool.start()
    risk_manager = RiskManager()
    TimerManager.addRepeatTimer(server.data_center.getCfgValue("server", "tick_time", default=1.0), risk_manager.renew_status)
    TimerManager.addRepeatTimer(5.0, server.syncData)
    try:
        while 1:
            server.tick()
            TimerManager.scheduler()
    except KeyboardInterrupt:
        logger.error("", exc_info=True)
        thread_pool.stop()
