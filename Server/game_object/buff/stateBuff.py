from math import fabs

from buffBase import Buff

import logging

from common import conf

logger = logging.getLogger()


class StateBuff(Buff):
    def __init__(self, room_id, source, target, target_entity_type, data):
        super(StateBuff, self).__init__(room_id, source, target, target_entity_type, data)

    def onCreate(self):
        super(StateBuff, self).onCreate()
        entity = self.data_center.getEntityByID(self.target_entity_type, self.target)
        for effect in self.effects:
            for param, value in effect.iteritems():
                # origin = getattr(entity, param)
                # names.append(param)
                # value = 2 >> value
                # values.append(origin | value)
                func = getattr(entity, "set" + param.capitalize(), None)
                if func is not None:
                    func()
        logger.info("state buff added")

    def onRemove(self):
        super(StateBuff, self).onRemove()
        entity = self.data_center.getEntityByID(self.target_entity_type, self.target)
        if entity is None:
            return
        for effect in self.effects:
            for param, value in effect.iteritems():
                func = getattr(entity, "remove" + param.capitalize(), None)
                if func is not None:
                    func()
                # origin = getattr(entity, param)
                # names.append(param)
                # value = 2 >> value
                # values.append(origin ^ value)
        logger.info("state buff removes")


