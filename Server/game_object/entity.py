
from game.utils import Transform
from common_server.data_module import DataCenter
from common.rpc_queue_module import RpcMessage, RpcQueue
import logging
logger = logging.getLogger()


class Entity(object):
    def __init__(self, rid):
        self.transform = Transform(None, None)
        self.entity_id = -1
        self.room_id = rid
        self.dmg_rate = 1.
        self.timer = None
        self.sync_rpc_url = ""
        self.cold_data_list = ["entity_id", "speed", "hp"]
        self.keyType = "Players"
        self.flag = 0
        self.rpc_queue = RpcQueue()
        self.data_center = DataCenter()
        self.deleted = False

    def tick(self, tick_time=0.02):
        return NotImplementedError

    def getColdData(self):
        ret = {}
        for cold_param in self.cold_data_list:
            ret[cold_param.capitalize()] = getattr(self, cold_param)
        return {self.keyType: [ret]}

    def writeAttr(self, name, value):
        # type: (str, object) -> None
        setattr(self, name, value)
        if self.sync_rpc_url != "" and name in self.cold_data_list:
            self.rpc_queue.push_msg(0,
                                    RpcMessage(self.sync_rpc_url, self.data_center.getRoom(self.room_id).client_id_list,
                                               [], self.getColdData()))

    def onDestroy(self):
        pass

    def writeAttrs(self, names, values):
        # type: (list[str], list[object]) -> None
        is_need_sync = False
        for name, value in zip(names, values):
            setattr(self, name, value)
            if name in self.cold_data_list:
                is_need_sync = True
        if is_need_sync and self.sync_rpc_url != "":
            self.rpc_queue.push_msg(0,
                                    RpcMessage(self.sync_rpc_url, self.data_center.getRoom(self.room_id).client_id_list,
                                               [], self.getColdData()))
