from skillEntity import SkillEntity
from setting import keyType
from game.utils import Collide
from common.rpc_queue_module import RpcMessage
from common.battle_queue_module import BattleMessage
from game_object.buff import CreateBuff
import copy
import logging

logger = logging.getLogger()


class WaterSputteringSkillEntity(SkillEntity):
    def __init__(self, rid):
        super(WaterSputteringSkillEntity, self).__init__(rid)
        self.radius = 3
        self.target = None
        self.position = None
        self.sync_rpc_url = "PlayerSyncHandler/UpdateSkillEffectInScene"

    def initSkillData(self, data):
        logger.info("watersputter skill added")
        self.target = data[keyType.Target]
        self.source = data[keyType.Source]
        self.position = data[keyType.Position]
        CreateBuff(self.room_id, self.source.entity_id, self.target.entity_id, keyType.Monster,
                   self.data_center.buff_info[9])
        # self.radius = data[keyType.SkillRadius]
        position = self.position.getDict()
        position["y"] = 0.1
        send_list = {
            "Entity_id": self.entity_id,
            "Effect_type": keyType.EFFECT_TYPE_MAP.WATER_SPUTTERING,
            "Effect_args": {
                "Type": 1,
                "Position": position,
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

    def tick(self, tick_time=0.02):
        target_get_hurt = self.hurt_deal()
        self.battle_queue.push_msg(0, BattleMessage("monsterDamagedByWater", self.source, target_get_hurt))
        room = self.data_center.getRoom(self.room_id)
        room.removeSkill(self.entity_id)
        logger.info("watersputter skill remove")
