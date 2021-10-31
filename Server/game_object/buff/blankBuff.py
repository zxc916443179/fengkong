from common import conf
from setting import keyType
from common_server.data_module import DataCenter
import logging
from buffBase import Buff
from common.rpc_queue_module import RpcMessage, RpcQueue
from collections import defaultdict

logger = logging.getLogger()


class BlankBuff(Buff):
    def __init__(self, room_id, source, target, target_entity_type, data):
        super(BlankBuff, self).__init__(room_id, source, target, target_entity_type, data)

    def onCreate(self):
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
        if not targets[self.target].__contains__("Buff"):
            targets[self.target]["Buff"] = []
        if not targets[self.target].__contains__("Entity_id"):
            targets[self.target]["Entity_id"] = self.target
        targets[self.target]["Buff"].append({
            "type": self.buff_type * 100,
            "target": self.target
        })
        url = "PlayerSyncHandler/UpdatePlayerAttribute" if self.target_entity_type == keyType.Player else "MonsterSyncHandler/SyncMonsterState"
        self.rpc_queue.push_msg(0, RpcMessage(url, room.client_id_list, [], {
            "Players" if self.target_entity_type == keyType.Player else "monsters": targets.values()
        }))
        logger.info({"Players" if self.target_entity_type == keyType.Player else "monsters": targets.values()})

        entity = self.data_center.getEntityByID(self.target_entity_type, self.target)
        if entity and entity.isAlive:
            for effect in self.effects:
                for param, value in effect.iteritems():
                    entity.reduceHp(-value, eid = self.source)
        else:
            self.removeBuff()



