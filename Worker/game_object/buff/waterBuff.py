from math import fabs

from buffBase import Buff

import logging

from common import conf

logger = logging.getLogger()


class WaterBuff(Buff):
    def __init__(self, room_id, source, target, target_entity_type, data):
        super(WaterBuff, self).__init__(room_id, source, target, target_entity_type, data)

    def onCreate(self):
        super(WaterBuff, self).onCreate()
        entity = self.data_center.getEntityByID(self.target_entity_type, self.target)
        entity.element["water"] = 1
        logger.info("water buff added")

    def onRemove(self):
        super(WaterBuff, self).onRemove()
        entity = self.data_center.getEntityByID(self.target_entity_type, self.target)
        if entity is None:
            return
        entity.element["water"] = 0
        logger.info("water buff removes")


