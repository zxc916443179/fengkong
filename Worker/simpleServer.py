import logging
import time
import json
from common import conf
from common.message_queue_module import MsgQueue, Message
from common.rpc_queue_module import RpcQueue
from common_server.data_module import DataCenter
from common_server.thread_pool_module import ThreadPool
from common_server.timer import TimerManager
from network.netStream import NetStream
from setting import keyType
from typing import Dict, List
import argparse


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


class Worker(object):
    def __init__(self, config=None):
        # type: (argparse.Namespace) -> None
        self.netstream = NetStream()
        self.netstream.connect(config.ip, config.port)
        self.queue = []  # type: List
        self.state = 0
        self.max_consume = 10
        self.message_queue = MsgQueue()
        self.rpc_queue = RpcQueue()
        self.data_center = DataCenter()
        self.data_center.setConfig(config)

    def tick(self, tick_time=0.02):
        if self.state == -1:
            raise Exception
        self.netstream.process()
        while self.netstream.status() == conf.NET_STATE_ESTABLISHED:
            data = self.netstream.recv()
            if data == '':
                break
            self.queue.append((conf.NET_CONNECTION_DATA, self.netstream.hid, data))
        self.consumeMessage()
        self.consumeRpcMessage()

    def consumeMessage(self):
        for _ in range(max(self.max_consume, len(self.queue))):
            if len(self.queue) <= 0:
                return
            code, wparam, data = self.queue[0]
            self.queue = self.queue[1:]
            if code == conf.NET_CONNECTION_LEAVE or self.netstream.state == -1:
                logger.error("lose connection, leave now")
                self.state = -1
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

    def broadCast(self):
        for room in self.data_center.allRooms:
            if room.isOnGoing:
                player_data = parseRpcMessage("PlayerSyncHandler/UpdatePlayerSituation",
                                              room.client_id_list, [], {"Players": room.getPlayersPosition()})
                self.netstream.send(json.dumps(player_data))
                monster_data = parseRpcMessage("MonsterSyncHandler/SyncMonsterPosition",
                                               room.client_id_list, [], {"monsters": [
                        self.data_center.getEntityByID(keyType.Monster, monster_eid).getMonsterPositionData()
                        for monster_eid in room.monster_list
                    ]})
                self.netstream.send(json.dumps(monster_data))

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
                        level=logging.DEBUG, format=LOG_FORMAT, datefmt=DATE_FORMAT)
    logger = logging.getLogger()
    if arguments.verbose:
        logger.addHandler(logging.StreamHandler())
    worker = Worker(config=arguments)
    thread_pool = ThreadPool()
    thread_pool.start()
    TimerManager.addRepeatTimer(2, worker.heartbeat)
    try:
        while 1:
            worker.tick()
            TimerManager.scheduler()
    except KeyboardInterrupt:
        logger.error("", exc_info=True)
        thread_pool.stop()
