from buffBase import Buff
import time
import logging

from common import conf
from setting import keyType
from game.utils import Collide, Vector3, Transform
from game_object.skill.lightning2SkillEntity import Lightning2SkillEntity

logger = logging.getLogger()


class LightningBuff(Buff):
    def __init__(self, room_id, source, target, target_entity_type, data):
        self.lightning_entity = None
        super(LightningBuff, self).__init__(room_id, source, target, target_entity_type, data)

    def onCreate(self):
        super(LightningBuff, self).onCreate()
        self.initLighting2Skill()
        logger.info("light buff added")

    def onRemove(self):
        super(LightningBuff, self).onRemove()
        if self.lightning_entity is not None:
            self.lightning_entity.removeSkill()
        logger.info("light buff removes")

    def initLighting2Skill(self):
        room = self.data_center.getRoom(self.room_id)
        lighting2Skill = Lightning2SkillEntity(self.room_id)
        self.data_center.registerEntity(keyType.Skill, lighting2Skill)
        room.joinSkill(lighting2Skill.entity_id)
        lighting2Skill.initSkillData({
            keyType.Source: self.target
        })
        self.lightning_entity = lighting2Skill

    def tick(self, tick_time=0.02):
        super(LightningBuff, self).tick(tick_time)
        if self.state == 1:
            return
        room = self.data_center.getRoom(self.room_id)
        target_entity = self.data_center.getEntityByID(self.target_entity_type, self.target)
        if target_entity:
            for buff in self.data_center.getRoomEntity(keyType.Buff, self.room_id):
                if buff is not None:
                    chose_entity = self.data_center.getEntityByID(buff.target_entity_type, buff.target)
                    if chose_entity:
                        if buff.buff_id == 10 and buff.target != self.target \
                                and Vector3.Distance(target_entity.transform.position, chose_entity.transform.position) <= \
                                self.data_center.skill_tree[conf.NORMAL_LIGHTNING_ALL_SKILL]['value'][0] ** 2 \
                                and room.lightning_vis_dic.get(buff.target) is None:
                            buff.time = 0.3
                            self.time = 0.3
                            if self.lightning_entity is not None:
                                self.lightning_entity.child.append(buff.target)
                                room.lightning_vis_dic[self.target] = self.target
                                room.lightning_vis_dic[buff.target] = self.target
        else:
            self.removeBuff()

