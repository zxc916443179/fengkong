from skillEntity import SkillEntity
from setting import keyType
from common.rpc_queue_module import RpcMessage
import logging

logger = logging.getLogger()


class Lightning2SkillEntity(SkillEntity):
    def __init__(self, rid):
        super(Lightning2SkillEntity, self).__init__(rid)
        self.lightning_can_linked_entity_list = []
        self.entity_id = 0
        self.child = []
        self.room_id = rid
        self.source = None
        self.target = None
        self.lightning = {}
        self.cd = 0
        self.hurt_time = {}
        self.may_damaged = []
        self.vis = {}
        self.send_list = []
        self.time = 0
        self.sync_rpc_url = "PlayerSyncHandler/UpdateSkillEffectInScene"

    def removeSkill(self):
        send_list = {
            "Entity_id": self.entity_id,
            "Effect_type": keyType.EFFECT_TYPE_MAP.DELETE
        }
        self.rpc_queue.push_msg(0,
                                RpcMessage(self.sync_rpc_url, self.data_center.getRoom(self.room_id).client_id_list, [],
                                           send_list))
        room = self.data_center.getRoom(self.room_id)
        room.removeSkill(self.entity_id)

    def tick(self, tick_time=0.02):
        self.cd += tick_time
        room = self.data_center.getRoom(self.room_id)
        if self.cd >= 1:
            target_entity = self.data_center.getEntityByID(keyType.Monster, self.source)
            if target_entity is not None:
                if len(self.child) > 0:
                    target_entity.reduceHp(3)
                    send_list = {
                        "Entity_id": self.entity_id,
                        "Effect_type": keyType.EFFECT_TYPE_MAP.LIGHTNING,
                        "Effect_args": {
                            "Entity_id": target_entity.entity_id,
                            "Child": self.child
                        }
                    }
                    self.rpc_queue.push_msg(0, RpcMessage(self.sync_rpc_url,
                                                          self.data_center.getRoom(self.room_id).client_id_list, [],
                                                          send_list))
                for target_entity_id in self.child:
                    target_entity = self.data_center.getEntityByID(keyType.Monster, target_entity_id)
                    if target_entity is not None:
                        target_entity.reduceHp(1, dmg_type=16)
            self.cd = 0
        for target_entity_id in self.child:
            if room.lightning_vis_dic.__contains__(target_entity_id):
                del room.lightning_vis_dic[target_entity_id]
        if room.lightning_vis_dic.__contains__(self.source):
            del room.lightning_vis_dic[self.source]
        self.child = []
