import copy
import math
import logging

from skillEntity import SkillEntity
from common.battle_queue_module import BattleMessage
from setting import keyType
from game.utils import Collide, Vector3, Transform

logger = logging.getLogger()


class FlashMeetSkillEntity(SkillEntity):
    def __init__(self, rid, source_pos):
        # type: (int, Vector3) -> None
        super(FlashMeetSkillEntity, self).__init__(rid)
        self.entity_id = 0
        self.room_id = rid
        self.distance = 10
        self.position = None
        self.transform = None
        self.source_pos = copy.deepcopy(source_pos)

    def initSkillData(self, data):
        self.source = data[keyType.Source]
        self.position = copy.copy(data[keyType.Position])
        self.transform = Transform(copy.copy(data[keyType.Position]), self.source.walk_rotation)

    def PathMeetTarget(self):
        room = self.data_center.getRoom(self.room_id)
        map = room.currentMap.mapList
        top = room.currentMap.top
        lef = room.currentMap.left
        cross_list = Collide.cross(self.transform.position.x - lef, self.transform.position.z + top,
                                   self.transform.rotation.y, map, self.distance)
        if len(cross_list) > 0:
            position = Vector3(cross_list[0] + lef, 0, cross_list[1] - top)
            source_to_war_distance = Vector3.Distance(position, self.transform.position) ** 0.5
            if source_to_war_distance < self.distance:
                self.distance = source_to_war_distance

        path_meet_target_angle_list = []
        path_meet_target_list = []
        target_entity_list = self.data_center.getRoomEntity(keyType.Monster, self.room_id)
        for target in target_entity_list:
            angle_target_source = Collide.rayDir(self.position, target.transform.position)
            angle_source_flash = self.source.walk_rotation.y
            distance_target_source = Vector3.Distance(target.transform.position, self.position)
            target_r = self.source.radius + target.radius
            if Collide.angleEquals(angle_target_source, angle_source_flash, distance_target_source, target_r):
                if distance_target_source <= self.distance ** 2:
                    path_meet_target_list.append(target)
                    # calculation repulsed angle
                    player_angle = self.source.walk_rotation.y
                    player_to_monster_angle = Collide.rayDir(self.position, target.transform.position)
                    angle = player_angle - player_to_monster_angle
                    distance_player_monster = Vector3.Distance(target.transform.position, self.position) ** 0.5
                    distance_r = self.source.radius + target.radius
                    if distance_player_monster <= distance_r:
                        angle1 = Collide.rayDir(self.position, target.transform.position)
                    else:
                        angle1 = (math.degrees(math.asin((math.sin(math.radians(
                            angle)) * distance_player_monster) / distance_r)) + player_angle)  # A/sina = B/sinb
                    path_meet_target_angle_list.append(angle1)
        return path_meet_target_list, path_meet_target_angle_list

    def tick(self, tick_time=0.02):
        room = self.data_center.getRoom(self.room_id)
        path_meet_target_list, path_meet_target_angle_list = self.PathMeetTarget()
        self.battle_queue.push_msg(0, BattleMessage("flashSkillDeal", self.source, path_meet_target_list,
                                                    path_meet_target_angle_list=path_meet_target_angle_list))
        room.removeSkill(self.entity_id)
