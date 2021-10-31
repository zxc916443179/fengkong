import copy
import logging
import time
from typing import TYPE_CHECKING

from skillEntity import SkillEntity
from common.battle_queue_module import BattleMessage
from setting import keyType
from game.utils import Collide, Vector3, Transform

logger = logging.getLogger()

if TYPE_CHECKING:
    from game_object.entity import Entity


class RaySkillEntity(SkillEntity):
    def __init__(self, rid, attack_range, source, power, target_type=keyType.Monster, **kwargs):
        # type: (int, int, Entity, int, str, ...) -> None
        super(RaySkillEntity, self).__init__(rid)
        self.room_id = rid
        self.radius = 0.5
        self.source = source
        self.transform = Transform(Vector3(0, 0, 0), Vector3(0, 0, 0))
        self.attack_range = attack_range
        self.target_type = target_type
        self.power = power
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def __getattr__(self, item):
        return None

    def cast(self, rand_seed=None):
        # type: (int) -> None
        dis_men = self.attack_range ** 2
        targetEntity = []
        target_entity_list = self.data_center.getRoomEntity(self.target_type, self.room_id)
        target_entity_list += self.data_center.getRoomEntity(keyType.Chest, self.room_id)
        begin_position = copy.copy(self.source.weapon_position)

        # check bullet hit the wall
        room = self.data_center.getRoom(self.room_id)
        map = room.currentMap.mapList
        top = room.currentMap.top
        lef = room.currentMap.left
        cross_list = Collide.cross(begin_position.x - lef, begin_position.z + top,
                                   self.transform.rotation.y, map, self.attack_range)
        if len(cross_list) > 0:
            position = Vector3(cross_list[0] + lef, 0, cross_list[1] - top)
            if dis_men > Vector3.Distance(position, self.transform.position):
                dis_men = Vector3.Distance(position, self.transform.position)
        angle_player = self.source.transform.rotation.y
        if rand_seed is not None:
            angle_player += rand_seed
        for target in target_entity_list:
            end_position = copy.copy(target.transform.position)

            angle_true = Collide.rayDir(begin_position, end_position)
            print "angle_true", angle_true
            distance2 = Vector3.Distance(begin_position, end_position)
            if Collide.angleEquals(angle_true, angle_player, distance2, self.radius + target.radius):
                if distance2 < dis_men:
                    if self.penetrated:
                        targetEntity.append(target)
                    else:
                        targetEntity = target
                        dis_men = distance2
        if type(targetEntity) is list:
            if len(targetEntity) > 0:
                self.battle_queue.push_msg(0,
                                           BattleMessage("monsterDamaged", self.source, targetEntity, dmg=self.power))
        else:
            self.battle_queue.push_msg(0, BattleMessage("monsterDamaged", self.source, [targetEntity], dmg=self.power))

    def tick(self, tick_time=0.02):
        pass
