from common import conf
from game_object.entity import Entity
from setting import keyType
from common_server.data_module import DataCenter
import logging
from common.rpc_queue_module import RpcMessage, RpcQueue
from collections import defaultdict

logger = logging.getLogger()


class Buff(object):
    data_center = DataCenter()

    def __init__(self, room_id, source, target, target_entity_type, data):
        self.entity_id = 0
        self.buff_id = data["buff_id"]
        self.room_id = room_id
        self.state = 0

        self.data_center = DataCenter()

        self.pack_max = data["pack_max"]
        self.time = data["time"]
        self.same_priority_replace_rule = data["same_priority_replace_rule"]
        self.buff_type = data["buff_type"]
        self.source = source
        self.target = target
        self.target_entity_type = target_entity_type

        self.effects = data["effects"]

        self.prior = data["prior"]
        self.icon = data["icon_type"]
        self.group = data["group"]
        self.is_instant = data["is_instant"]
        self.buff_name = data["buff_name"]
        self.packs = 0
        self.timer = None
        self.invoke_time = data["invoke_time"]
        self.invoke_time_copy = 0

        self.rpc_queue = RpcQueue()
        self.deleted = False
        self.onCreate()

        logger.info("buff created %s, id is %d" % (self.buff_name, self.buff_id))

    def onCreate(self):
        room = self.data_center.getRoom(self.room_id)
        targets = defaultdict(dict)
        for buff in self.data_center.getRoomEntity(keyType.Buff, self.room_id):
            if not targets[buff.target].__contains__("Buff"):
                targets[buff.target]["Buff"] = []
            if not targets[buff.target].__contains__("Entity_id"):
                targets[buff.target]["Entity_id"] = buff.target
            targets[buff.target]["Buff"].append(buff.getDict())

        if not targets[self.target].__contains__("Buff"):
            targets[self.target]["Buff"] = []
        if not targets[self.target].__contains__("Entity_id"):
            targets[self.target]["Entity_id"] = self.target
        targets[self.target]["Buff"].append(self.getDict())
        url = "PlayerSyncHandler/UpdatePlayerAttribute" if self.target_entity_type == keyType.Player else "MonsterSyncHandler/SyncMonsterState"
        self.rpc_queue.push_msg(0, RpcMessage(url, room.client_id_list, [], {
            "Players" if self.target_entity_type == keyType.Player else "monsters": targets.values()
        }))
        logger.info({"Players" if self.target_entity_type == keyType.Player else "monsters": targets.values()})

    def onRemove(self):
        room = self.data_center.getRoom(self.room_id)
        targets = defaultdict(dict)
        for buff in self.data_center.getRoomEntity(keyType.Buff, self.room_id):
            if buff.entity_id == self.entity_id:
                continue
            if not targets[buff.target].__contains__("Buff"):
                targets[buff.target]["Buff"] = []
            if not targets[buff.target].__contains__("Entity_id"):
                targets[buff.target]["Entity_id"] = buff.target
            targets[buff.target]["Buff"].append(buff.getDict())
        ret = {"Players" if self.target_entity_type == keyType.Player else "monsters": targets.values()}
        logger.info(ret)
        url = "PlayerSyncHandler/UpdatePlayerAttribute" if self.target_entity_type == keyType.Player else "MonsterSyncHandler/SyncMonsterState"
        self.rpc_queue.push_msg(0, RpcMessage(url, room.client_id_list, [], ret))

    def removeBuff(self):
        self.onRemove()
        room = self.data_center.getRoom(self.room_id)
        room.removeEntity(keyType.Buff, self.entity_id)

    def addPack(self):
        pass

    def tick(self, tick_time=0.02):
        entity = self.data_center.getEntityByID(self.target_entity_type, self.target)
        if entity is None or not entity.isAlive:
            self.removeBuff()
            self.state = 1
            return

        self.time -= conf.STATE_CHECK_TIME
        if self.time <= 0:
            self.removeBuff()

    def getDict(self):
        return {
            "type": self.buff_type,
            "target": self.target
        }

    def onDestroy(self):
        pass
