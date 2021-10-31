import copy
import logging

from skillEntity import SkillEntity
from setting import keyType
from game.utils import Collide

logger = logging.getLogger()


class BoomMonsterSkillEntity(SkillEntity):
    def __init__(self, rid):
        super(BoomMonsterSkillEntity, self).__init__(rid)
        self.room_id = rid
        self.position = None
        self.radius = 0
        self.dam = 0

    def initSkillInfo(self, data):
        self.source = data[keyType.Source]
        self.radius = data[keyType.SkillRadius]
        self.position = data[keyType.Position]

    def tick(self, tick_time=0.02):
        entity_list = []
        room = self.data_center.getRoom(self.room_id)
        target_entity_list = self.data_center.getRoomEntity(keyType.Player, self.room_id)
        target_entity_list += self.data_center.getRoomEntity(keyType.Chest, self.room_id)
        for target in target_entity_list:
            position1 = copy.copy(self.position)
            position2 = copy.copy(target.transform.position)
            r = self.radius + target.radius
            if Collide.trigger(position1, position2, r):
                entity_list.append(target)
        # self.battle_queue.push_msg(0, BattleMessage(self.source, 16, entity_list))
        room.removeSkill(self.entity_id)
