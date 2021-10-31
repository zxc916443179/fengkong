from buffBase import Buff
import time
import logging
from common import conf
from setting import keyType

logger = logging.getLogger()


class HurtBuff(Buff):
    def __init__(self, room_id, source, target, target_entity_type, data):
        super(HurtBuff, self).__init__(room_id, source, target, target_entity_type, data)

    def onCreate(self):
        super(HurtBuff, self).onCreate()
        self.invoke_time_copy = 0
        logger.info("hurt buff added")

    def hurt(self):
        self.invoke_time_copy = self.invoke_time
        entity = self.data_center.getEntityByID(self.target_entity_type, self.target)
        if entity is not None:
            for effect in self.effects:
                for param, value in effect.iteritems():
                    if self.buff_id == 11:
                        entity.reduceHp(-value, dmg_type=33, eid=self.source)
                    else:
                        entity.reduceHp(-value, eid=self.source)
        else:
            self.removeBuff()

    def addPack(self):
        if self.packs < self.pack_max:
            self.packs += 1

    def tick(self, tick_time=0.02):
        super(HurtBuff, self).tick(tick_time)
        if self.state == 1:
            return
        self.invoke_time_copy -= conf.STATE_CHECK_TIME
        if self.invoke_time_copy <= 0:
            self.hurt()
