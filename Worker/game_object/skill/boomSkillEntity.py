
import copy

from common.battle_queue_module import BattleMessage
from game.utils import Collide
from setting import keyType
from skillEntity import SkillEntity
from typing import TYPE_CHECKING
import logging
logger = logging.getLogger()
if TYPE_CHECKING:
    from game_object.entity import Entity
    from game.utils import Vector3


class BoomSkillEntity(SkillEntity):
    def __init__(self, rid, boom_radius, source, power, position, target_type=keyType.Monster, **kwargs):
        # type: (int, int, Entity, int, Vector3, str, ...) -> None
        super(BoomSkillEntity, self).__init__(rid)
        self.position = position
        self.source = source
        self.power = power
        self.target_type = target_type
        self.radius = boom_radius
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def __getattr__(self, item):
        return None

    def tick(self, tick_time=0.02):
        entity_list = []
        room = self.data_center.getRoom(self.room_id)
        target_entity_list = self.data_center.getRoomEntity(self.target_type, self.room_id)
        target_entity_list += self.data_center.getRoomEntity(keyType.Chest, self.room_id)
        for target in target_entity_list:
            r = self.radius + target.radius
            if Collide.trigger(self.position, target.transform.position, r):
                entity_list.append(target)
        self.battle_queue.push_msg(0, BattleMessage("monsterDamaged", self.source, entity_list, dmg=self.power))
        room.removeSkill(self.entity_id)
