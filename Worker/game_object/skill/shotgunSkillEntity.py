from typing import TYPE_CHECKING

from skillEntity import SkillEntity
from common.battle_queue_module import BattleMessage
from setting import keyType
from game.utils import Collide, Vector3
import logging
logger = logging.getLogger()

if TYPE_CHECKING:
    from game_object.entity import Entity


class ShotgunSkillEntity(SkillEntity):
    def __init__(self, rid, attack_range, shoot_angle, source, power, target_type=keyType.Monster, **kwargs):
        # type: (int, int, int, Entity, int, int, str) -> None
        super(ShotgunSkillEntity, self).__init__(rid)
        self.attack_range = attack_range
        self.shoot_angle = shoot_angle
        self.source = source
        self.power = power
        self.radius = 0.2
        self.target_type = target_type
        self.kwargs = kwargs

    def cast(self, rand_seed=None):
        # type:(int) -> list[Entity]
        start_angle = self.source.transform.rotation.y - self.shoot_angle
        angle_this = start_angle
        dis_men = self.attack_range ** 2
        target_list = []

        target_entity_list = self.data_center.getRoomEntity(self.target_type, self.room_id)
        target_entity_list += self.data_center.getRoomEntity(keyType.Chest, self.room_id)
        target_dis = [Vector3.Distance(target.transform.position, self.source.transform.position) for target in target_entity_list]
        target_angle = [Collide.rayDir(self.source.transform.position, target.transform.position) for target in target_entity_list]
        for _ in xrange(6):
            _target = None
            _attack_range = dis_men
            for dis, angle, target in zip(target_dis, target_angle, target_entity_list):
                if Collide.angleEquals(angle_this, angle, dis, self.radius + target.radius) and dis < _attack_range:
                    _target = target
                    _attack_range = dis
            if _target is not None:
                target_list.append(_target)
            angle_this += 5
        if len(target_list) > 0:
            self.battle_queue.push_msg(0, BattleMessage("monsterDamaged", self.source, target_list, dmg=self.power))
        return target_list
