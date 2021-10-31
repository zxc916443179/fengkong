# import copy
#
# from skillEntity import SkillEntity
# from common.battle_queue_module import BattleMessage, BattleMsgQueue
# from setting import keyType
# from game.utils import Collide
#
#
# class BulletEntity(SkillEntity):
#     def __init__(self, rid):
#         super(BulletEntity, self).__init__()
#         self.room_id = rid
#         self.transform = None
#         self.radius = 0
#         self.maxTime = 0
#         self.speed = 0
#         self.distance = 0
#
#     def initSkillInfo(self, data):
#         self.source = data[keyType.Source]
#         self.radius = data[keyType.SkillRadius]
#
#     def tick(self, tick_time=0.02):
#         entity_list = []
#         room = self.data_center.getRoom(self.room_id)
#         target_entity_list = self.data_center.getRoomEntity(keyType.Player, self.room_id)
#         target_entity_list += self.data_center.getRoomEntity(keyType.Chest, self.room_id)
#         for target in target_entity_list:
#             position1 = copy.copy(self.transform.position)
#             position2 = copy.copy(target.transform.position)
#             r = self.radius + target.radius
#             if Collide.trigger(position1, position2, r):
#                 entity_list.append(target)
#                 self.battle_queue.push_msg(0, BattleMessage("playerDamaged", self.source, entity_list, {}))
#         room.removeSkill(self.entity_id)
