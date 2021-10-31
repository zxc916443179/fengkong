# import sys
# import copy
#
# sys.path.append("./common_server")
# sys.path.append("./common")
# sys.path.append("./game")
#
# from skillEntity import SkillEntity
# from battle_queue_module import BattleMessage, BattleMsgQueue
# from setting import keyType
# from utils import Collide, Vector3
#
#
# class LaserSkillEntity(SkillEntity):
#     def __init__(self, rid):
#         super(LaserSkillEntity, self).__init__()
#         self.room_id = rid
#         self.monster = None
#         self.source = None
#
#     def LaserShoot(self):
#         dis_men = 2000
#         target_entity_list = self.data_center.getRoomEntity(keyType.Monster, self.room_id)
#         target_entity_list += self.data_center.getRoomEntity(keyType.Chest, self.room_id)
#         target_may_get_hurt_list = []
#         target_damaged_list = []
#         for monster in target_entity_list:
#             begin_position = copy.copy(self.source.transform.position)
#             end_position = copy.copy(monster.transform.position)
#             angle_true = Collide.rayDir(begin_position, end_position)
#             angle_player = self.source.transform.rotation.y
#             distance2 = Vector3.Distance(begin_position, end_position)
#             if Collide.angleEquals(angle_true, angle_player, distance2, 2):
#                 target_may_get_hurt_list.append(monster)
#         for target in target_may_get_hurt_list:
#             begin_position = copy.copy(self.source.transform.position)
#             end_position = copy.copy(target.transform.position)
#             dis = Vector3.Distance(begin_position, end_position)
#             if dis < dis_men ** 2:
#                 target_damaged_list.append(target)
#         return target_damaged_list
#
#     def tick(self, tick_time=0.02):
#         room = self.data_center.getRoom(self.room_id)
#         entity_list = self.LaserShoot()
#         self.battle_queue.push_msg(0, BattleMessage("monsterDamagedBySwirl", self.source, entity_list, {}))
#         room.removeSkill(self.entity_id)
