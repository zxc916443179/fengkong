import copy
import logging
from common import conf
from skillEntity import SkillEntity
from common.battle_queue_module import BattleMessage
from common.rpc_queue_module import RpcMessage
from setting import keyType
from game.utils import Collide

logger = logging.getLogger()


class FlashSwirlSkillEntity(SkillEntity):
    def __init__(self, rid):
        super(FlashSwirlSkillEntity, self).__init__(rid)
        self.entity_id = 0
        self.room_id = rid
        self.position = None
        self.cd = 0
        self.time = 0
        self.radius = self.data_center.skill_tree[conf.FLASH_SWIRL_GET][keyType.Value][2]
        self.sync_rpc_url = "PlayerSyncHandler/UpdateSkillEffectInScene"

    def initSkillData(self, data):
        self.cd = data[keyType.Cd]
        self.source = data[keyType.Source]
        self.position = copy.copy(data[keyType.Position])
        send_list = {
            "Entity_id": self.entity_id,
            "Effect_type": keyType.EFFECT_TYPE_MAP.FLASH_SWIRL,
            "Effect_args": {
                "Position": self.position.getDict(),
                "Radius": self.radius
            }
        }
        self.rpc_queue.push_msg(0, RpcMessage(self.sync_rpc_url, self.data_center.getRoom(self.room_id).client_id_list,
                                              [], send_list))

    def hurt_deal(self):
        target_get_hurt = []
        target_entity_list = self.data_center.getRoomEntity(keyType.Monster, self.room_id)
        for target in target_entity_list:
            if Collide.trigger(target.transform.position, self.position, self.radius):
                target_get_hurt.append(target)
        return target_get_hurt

    def onDestroy(self):
        send_list = {
            "Entity_id": self.entity_id,
            "Effect_type": keyType.EFFECT_TYPE_MAP.DELETE
        }
        self.rpc_queue.push_msg(0,
                                RpcMessage(self.sync_rpc_url, self.data_center.getRoom(self.room_id).client_id_list,
                                           [], send_list))

    def tick(self, tick_time=0.02):
        room = self.data_center.getRoom(self.room_id)
        self.time += tick_time
        if self.cd <= self.time:
            room.removeSkill(self.entity_id)
            send_list = {
                "Entity_id": self.entity_id,
                "Effect_type": keyType.EFFECT_TYPE_MAP.DELETE
            }
            self.rpc_queue.push_msg(0,
                                    RpcMessage(self.sync_rpc_url, self.data_center.getRoom(self.room_id).client_id_list,
                                               [], send_list))
        if int(self.time * 100) % 30 <= 0:
            target_get_hurt = self.hurt_deal()
            self.battle_queue.push_msg(0, BattleMessage("monsterDamagedBySwirl", self.source, target_get_hurt))
