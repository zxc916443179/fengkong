from math import fabs

from buffBase import Buff

import logging

from common import conf

logger = logging.getLogger()


class NumericBuff(Buff):
    def __init__(self, room_id, source, target, target_entity_type, data):
        super(NumericBuff, self).__init__(room_id, source, target, target_entity_type, data)

    def onCreate(self):
        super(NumericBuff, self).onCreate()
        entity = self.data_center.getEntityByID(self.target_entity_type, self.target)
        if entity:
            if self.buff_id == 10:
                entity.element["light"] = 1
            names = []
            values = []
            for effect in self.effects:
                for param, value in effect.iteritems():
                    origin = getattr(entity, param)
                    if fabs(value) < 1:
                        value = origin * value
                        effect[param] = round(value)
                    names.append(param)
                    values.append(origin + value)
            entity.writeAttrs(names, values)
            logger.info("numeric buff added")
        else:
            self.removeBuff()

    def addPack(self):
        if self.packs < self.pack_max:
            self.packs += 1

    def onRemove(self):
        super(NumericBuff, self).onRemove()
        entity = self.data_center.getEntityByID(self.target_entity_type, self.target)
        if entity is None:
            return
        if self.buff_id == 10:
            entity.element["light"] = 0
        names = []
        values = []
        for effect in self.effects:
            for param, value in effect.iteritems():
                origin = getattr(entity, param)
                names.append(param)
                values.append(origin - value)
        entity.writeAttrs(names, values)
        logger.info("numeric buff removes")

    def tick(self, tick_time=0.02):
        super(NumericBuff, self).tick(tick_time)
        if self.state == 1:
            return

