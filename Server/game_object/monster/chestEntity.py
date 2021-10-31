
from monsterEntity import MonsterEntity
from setting import keyType
from game.utils import Vector3, Transform

import logging
logger = logging.getLogger()


class ChestEntity(MonsterEntity):
    def __init__(self, rid, position=None, rotation=None):
        # type: (int, Vector3, Vector3) -> None
        super(ChestEntity, self).__init__(rid)
        self.transform = Transform(position, rotation)
        self.radius = 2

    def updateState(self):
        if self.state == keyType.MONSTER_STATE_MAP.Die:
            self.dieHandle()
    
    def dieHandle(self):
        logger.info("chest[%d] destroyed" % self.entity_id)
        self.sendStateToClient(self.state)
        self.tryDropItem(self.roomEntity)
        self.roomEntity.removeEntity(keyType.Chest, self.entity_id)
