from skillEntity import SkillEntity
from setting import keyType
from game.utils import Collide
from common.rpc_queue_module import RpcMessage
from common.battle_queue_module import BattleMessage
from game_object.buff import CreateBuff
import copy
import logging

logger = logging.getLogger()


class WaterSkillEntity(SkillEntity):
    def __init__(self, rid):
        super(WaterSkillEntity, self).__init__(rid)
        self.cd = 3
        self.time = 0
        self.radius = 3
        self.target = None
        self.position = None
        self.sync_rpc_url = "PlayerSyncHandler/UpdateSkillEffectInScene"

    def initSkillData(self, data):
        # self.cd = data[keyType.Cd]
        self.source = data[keyType.Source]
        self.position = data[keyType.Position]
        self.target = data[keyType.Target]
        position = self.position.getDict()
        position["y"] = 0.2
        send_list = {
            "Entity_id": self.entity_id,
            "Effect_type": keyType.EFFECT_TYPE_MAP.WATER,
            "Effect_args": {
                "Position": position,
                "Radius": self.radius
            }
        }
        self.rpc_queue.push_msg(0, RpcMessage(self.sync_rpc_url, self.data_center.getRoom(self.room_id).client_id_list,
                                              [], send_list))
        logger.info("water skill added")

    def onDestroy(self):
        send_list = {
            "Entity_id": self.entity_id,
            "Effect_type": keyType.EFFECT_TYPE_MAP.DELETE
        }
        self.rpc_queue.push_msg(0,
                                RpcMessage(self.sync_rpc_url, self.data_center.getRoom(self.room_id).client_id_list,
                                           [], send_list))
        logger.info("water skill remove")

    def tick(self, tick_time=0.02):
        target_get_hurt = []
        room = self.data_center.getRoom(self.room_id)
        self.time += tick_time
        target_entity_list = self.data_center.getRoomEntity(keyType.Monster, self.room_id)
        for target in target_entity_list:
            if Collide.trigger(target.transform.position, self.position, self.radius):
                CreateBuff(self.room_id, self.source.entity_id, target.entity_id, keyType.Monster,
                           self.data_center.buff_info[9])
                if int(self.time * 100) % 30 <= 0:
                    target_get_hurt.append(target)
                    self.battle_queue.push_msg(0, BattleMessage("monsterDamagedByWater", self.source, target_get_hurt))

        if self.cd <= self.time:
            send_list = {
                "Entity_id": self.entity_id,
                "Effect_type": keyType.EFFECT_TYPE_MAP.DELETE
            }
            self.rpc_queue.push_msg(0,
                                    RpcMessage(self.sync_rpc_url, self.data_center.getRoom(self.room_id).client_id_list,
                                               [], send_list))
            room.removeSkill(self.entity_id)
            logger.info("water skill remove")
