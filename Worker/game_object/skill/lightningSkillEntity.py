#
# import time
# from collections import deque
# from skillEntity import SkillEntity
# from common.battle_queue_module import BattleMessage, BattleMsgQueue
# from setting import keyType
#
#
# class LightningSkillEntity(SkillEntity):
#     def __init__(self, rid):
#         super(LightningSkillEntity, self).__init__()
#         self.lightning_can_linked_entity_list = []
#         self.entity_id = 0
#         self.room_id = rid
#         self.source = None
#         self.aim = None
#         self.lightning = {}
#         self.cd = 0
#         self.hurt_time = {}
#         self.may_damaged = []
#         self.vis = {}
#         self.send_list = []
#         self.time = 0
#
#     def removeSkill(self):
#         room = self.data_center.getRoom(self.room_id)
#         room.removeSkill(self.entity_id)
#
#     def tick(self, tick_time=0.02):
#         self.time = time.time()
#         # target_entity_list = self.data_center.getRoomEntity(keyType.Monster, self.room_id)
#         for target_id in self.lightning_can_linked_entity_list:
#             target = self.data_center.getEntityByID(keyType.Monster, target_id)
#             if self.hurt_time.get(target_id) is not None:
#                 self.time = self.hurt_time[target_id]
#             if self.vis.get(target_id) is None:
#                 self.may_damaged.append(target_id)
#                 # bfs
#                 bfs_queue = deque()
#                 bfs_queue.append(target_id)
#                 self.vis[target_id] = 1
#                 while len(bfs_queue) > 0:
#                     entity_id = bfs_queue.pop()
#                     for next_entity_id in self.lightning[entity_id]:
#                         if self.vis[next_entity_id] is None:
#                             self.may_damaged.append(next_entity_id)
#                             self.send_list.append((entity_id, next_entity_id))
#                             if self.hurt_time.get(next_entity_id) is not None:
#                                 if self.hurt_time[next_entity_id] < self.hurt_time[target_id]:
#                                     self.time = self.hurt_time[next_entity_id]
#                                 #     self.hurt_time[target_id] = self.hurt_time[next_entity_id]
#                                 # else:
#                                 #     self.hurt_time[next_entity_id] = self.hurt_time[target_id]
#                             self.vis[next_entity_id] = 1
#             if (time.time() - self.time) % 3 == 0:
#                 for target in self.may_damaged:
#                     target_entity = self.data_center.getEntityByID(keyType.Monster, target)
#                     target_entity.reduceHp(10)
#             self.may_damaged = []
#         # self.battle_queue.push_msg(0, BattleMessage(self.source, 5, self.send_list))
#         self.send_list = []
#         self.vis.clear()
#         self.lightning.clear()
#         self.lightning_can_linked_entity_list = []
