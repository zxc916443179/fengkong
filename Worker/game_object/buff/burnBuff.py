from buffBase import Buff
from common import conf
from game.utils import Collide, Vector3, Transform
from common.rpc_queue_module import RpcMessage, RpcQueue
from common_server.timer import TimerManager
import logging

from setting import keyType

logger = logging.getLogger()


class BurnBuff(Buff):
    def __init__(self, room_id, source, target, target_entity_type, data):
        super(BurnBuff, self).__init__(room_id, source, target, target_entity_type, data)

    def onCreate(self):
        super(BurnBuff, self).onCreate()
        entity = self.data_center.getEntityByID(self.target_entity_type, self.target)
        if entity is not None:
            entity.element["burn"] = 1
            logger.info("burn buff added")
        else:
            return

    def hurt(self):
        self.invoke_time_copy = self.invoke_time
        entity = self.data_center.getEntityByID(self.target_entity_type, self.target)
        if entity is not None:
            for effect in self.effects:
                for param, value in effect.iteritems():
                    entity.reduceHp(-value, dmg_type=14, eid=self.source)
        else:
            self.removeBuff()

    def boom(self):
        source_list = self.data_center.getRoomEntity(keyType.Player, self.room_id)
        for source in source_list:
            if source.setFlag(keyType.SITUATION_FLAG_MAP.BOOM):
                source.writeAttr("flag", source.flag)
                TimerManager.addTimer(0.02, lambda x: source.removeFlag(keyType.SITUATION_FLAG_MAP.BOOM), source)
        entity = self.data_center.getEntityByID(self.target_entity_type, self.target)
        if entity is None:
            self.removeBuff()
        else:
            entity.dmg_target[1] = 0
            position = entity.transform.position.getDict()
            position["y"] = self.data_center.skill_tree[conf.BURN_TO_BOOM]["value"][1] / 2.0
            send_list = {
                "Entity_id": self.entity_id,
                "Effect_type": keyType.EFFECT_TYPE_MAP.BURN,
                "Effect_args": {
                    "Type": 1,
                    "Position": position,
                    "Radius": self.data_center.skill_tree[conf.BURN_TO_BOOM]["value"][1]
                }
            }
            url = "PlayerSyncHandler/UpdateSkillEffectInScene"
            self.rpc_queue.push_msg(0,
                                    RpcMessage(url, self.data_center.getRoom(self.room_id).client_id_list, [],
                                               send_list))
            entity = self.data_center.getEntityByID(self.target_entity_type, self.target)
            if entity is not None:
                target_entity_list = self.data_center.getRoomEntity(keyType.Chest, self.room_id)
                target_entity_list += self.data_center.getRoomEntity(keyType.Monster, self.room_id)
                for target in target_entity_list:
                    if target != entity and Vector3.Distance(target.transform.position, entity.transform.position) <= \
                            self.data_center.skill_tree[conf.BURN_TO_BOOM]["value"][1] ** 2:
                        target.reduceHp(self.data_center.skill_tree[conf.BURN_TO_BOOM]["value"][0], dmg_type=14,
                                        eid=self.source)
            else:
                self.removeBuff()

    def onRemove(self):
        super(BurnBuff, self).onRemove()
        entity = self.data_center.getEntityByID(self.target_entity_type, self.target)
        if entity is None:
            return
        entity.element["burn"] = 0
        logger.info("burn buff removes")

    def tick(self, tick_time=0.02):
        super(BurnBuff, self).tick(tick_time)
        if self.state == 1:
            return
        self.invoke_time_copy -= conf.STATE_CHECK_TIME
        if self.invoke_time_copy <= 0:
            self.hurt()
        entity = self.data_center.getEntityByID(self.target_entity_type, self.target)
        if entity is None:
            return
        if entity.dmg_target[1] >= 100:
            entity = self.data_center.getEntityByID(keyType.Player, self.source)
            if entity.skill_dict.skill_dict.get(conf.BURN_TO_BOOM) is not None and \
                    entity.skill_dict.skill_dict[conf.BURN_TO_BOOM]['active'] == 1:
                self.boom()
                self.removeBuff()
