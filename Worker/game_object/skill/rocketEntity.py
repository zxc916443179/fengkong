import copy

from game_object.skill.boomSkillEntity import BoomSkillEntity
from skillEntity import SkillEntity
from common.battle_queue_module import BattleMessage
from setting import keyType
from game.utils import Collide
from typing import TYPE_CHECKING
import logging
from game.utils import Transform, Vector3

logger = logging.getLogger()
if TYPE_CHECKING:
    from game_object.entity import Entity


class RocketEntity(SkillEntity):
    def __init__(self, rid, attack_range, source, power, speed, target_type=keyType.Monster, **kwargs):
        # type: (int, int, Entity, int, int, str, ...) -> None
        super(RocketEntity, self).__init__(rid)
        self.transform = None
        self.speed = speed
        self.attack_range = attack_range
        self.source = source
        self.power = power
        self.target_type = target_type
        self.radius = 1
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
        self.transform = Transform(copy.deepcopy(self.source.weapon_position), copy.deepcopy(self.source.transform.rotation))

    def __getattr__(self, item):
        return None

    def tick(self, tick_time=0.02):
        entity_list = []
        forward = self.transform.forward()
        forward.multiply(self.speed * tick_time)
        self.transform.translate(forward)
        self.attack_range -= self.speed * tick_time
        room = self.data_center.getRoom(self.room_id)
        if self.attack_range <= 0:
            room.removeSkill(self.entity_id)
        target_entity_list = self.data_center.getRoomEntity(self.target_type, self.room_id)
        target_entity_list += self.data_center.getRoomEntity(keyType.Chest, self.room_id)
        for target in target_entity_list:
            position1 = copy.copy(self.transform.position)
            position2 = copy.copy(target.transform.position)
            r = self.radius + target.radius
            if Collide.trigger(position1, position2, r):
                boom = BoomSkillEntity(self.room_id, 5, self.source, self.power, self.transform.position)
                self.data_center.registerEntity(keyType.Skill, boom)
                room.joinSkill(boom.entity_id)
                room.removeSkill(self.entity_id)
                return
