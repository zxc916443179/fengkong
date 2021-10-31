# coding=utf-8
import random
import math

from setting import keyType
from common import conf

from common.common_library_module import Singleton
from common_server.timer import TimerManager
from common.rpc_queue_module import RpcQueue, RpcMessage
from common.battle_queue_module import BattleMsgQueue, BattleMessage
from common_server.data_module import DataCenter
from game.utils import Vector3, Transform, Collide
from game_object.buff import CreateBuff
from game_object.monster.chestEntity import ChestEntity
from game_object.skill.waterSkillEntity import WaterSkillEntity
from game_object.skill.waterSputteringSkillEntity import WaterSputteringSkillEntity
# from roomEntity import Room
import logging

logger = logging.getLogger()


@Singleton
class BattleModule(object):
    def __init__(self):
        self.rpc_queue = RpcQueue()
        self.battle_queue = BattleMsgQueue()
        self.target = []
        self.data_center = DataCenter()
        self.max_consume = 10

    def skillBeLit(self, source, eid):
        if source.skill_dict.skill_dict.__contains__(eid):
            if source.skill_dict.skill_dict[eid]['active'] == 1:
                return 1
        return 0

    def tick(self, tick_time=0.02):
        for _ in xrange(min(self.max_consume, self.battle_queue.count)):
            if self.battle_queue.count <= 0:
                break
            msg = self.battle_queue.pop_msg()
            self.handleMessage(msg)

    def handleMessage(self, msg):
        # type: (Message) -> None
        func = getattr(self, msg.method, None)
        if func is not None:
            func(msg)
        else:
            logger.error("not implement: %s" % msg.method)

    def monsterDamagedBySwirl(self, msg):
        target_list = msg.target
        source = msg.source
        dmg = self.data_center.skill_tree[conf.FLASH_SWIRL_GET]['value'][0]
        for monster in target_list:
            monster.reduceHp(dmg, eid=source.entity_id)

    def monsterDamagedByWater(self, msg):
        target_list = msg.target
        source = msg.source
        dmg = self.data_center.skill_tree[conf.NORMAL_WATER_SKILL]['value'][1]
        for monster in target_list:
            monster.reduceHp(dmg, dmg_type=source.skill_dict.flag, eid=source.entity_id)

    def shotgunMonsterDamaged(self, msg):
        source = msg.source
        target_list = msg.target
        room_id = source.room_id
        dmg = 10
        for monster in target_list:
            monster.reduceHp(dmg, eid=source.entity_id)

    def createBuff(self, msg):
        CreateBuff(msg.room_id, msg.source, msg.target, msg.target_entity_type, self.data_center.buff_info[msg.buff_id])

    def monsterDamaged(self, msg):
        source = msg.source
        target_list = msg.target
        rid = source.room_id
        is_critical = False
        damage_value = msg.dmg/19
        # critic skill
        source.n += 1
        source.n = min(source.n, 100)
        probability = source.prd_c * source.n
        rand = random.randint(0, 100)
        if rand < probability * 100:
            source.n = 0
            damage_value *= source.magnification
            is_critical = True
        for monster in target_list:
            if monster.deleted:
                continue
            monster.reduceHp(damage_value, dmg_type=source.skill_dict.flag, eid=source.entity_id,
                             is_critical=is_critical, is_bullet=True)
            if not monster.isAlive or monster is None:
                continue
            # burn skill
            if self.skillBeLit(source, conf.NORMAL_BURN_SKILL) and isinstance(monster, ChestEntity) is False:
                buff_id_list = self.data_center.skill_tree[conf.NORMAL_BURN_SKILL]['buff_id']
                for buff_id in buff_id_list:
                    CreateBuff(source.room_id, source.entity_id, monster.entity_id, keyType.Monster,
                               self.data_center.buff_info[buff_id])
                monster.dmg_target[1] += damage_value

                if monster.cd[0] <= 0:
                    if monster.element["water"] == 1:
                        monster.reduceHp(0, dmg_type=33, eid=source.entity_id)
                        CreateBuff(source.room_id, source.entity_id, monster.entity_id, keyType.Monster,
                                   self.data_center.buff_info[11])
                        monster.cd[0] = 3
                if monster.cd[1] <= 0:
                    if monster.element["light"] == 1:
                        repulse_distance = 3
                        angle = Collide.rayDir(source.transform.position, monster.transform.position)
                        monster.repelMonster(angle, repulse_distance)
                        CreateBuff(source.room_id, source.entity_id, monster.entity_id, keyType.Monster,
                                   self.data_center.buff_info[8])
                        monster.reduceHp(0, dmg_type=30, eid=source.entity_id)
                        source_list = self.data_center.getRoomEntity(keyType.Player, rid)
                        for source in source_list:
                            if source.setFlag(keyType.SITUATION_FLAG_MAP.BOOM):
                                source.writeAttr("flag", source.flag)
                                TimerManager.addTimer(0.02,
                                                      lambda x: source.removeFlag(keyType.SITUATION_FLAG_MAP.BOOM),
                                                      source)
                        monster.cd[1] = 3

            # Lighting skill
            if self.skillBeLit(source, conf.NORMAL_LIGHTNING_SKILL) and isinstance(monster, ChestEntity) is False:
                buff_id_list = self.data_center.skill_tree[conf.NORMAL_LIGHTNING_SKILL]['buff_id']
                for buff_id in buff_id_list:
                    CreateBuff(source.room_id, source.entity_id, monster.entity_id, keyType.Monster,
                               self.data_center.buff_info[buff_id])
                monster.dmg_target[2] += damage_value

                if monster.cd[1] <= 0:
                    if monster.element["burn"] == 1:
                        repulse_distance = 3
                        angle = Collide.rayDir(source.transform.position, monster.transform.position)
                        monster.repelMonster(angle, repulse_distance)
                        CreateBuff(source.room_id, source.entity_id, monster.entity_id, keyType.Monster,
                                   self.data_center.buff_info[8])
                        monster.reduceHp(0, dmg_type=30, eid=source.entity_id)
                        source_list = self.data_center.getRoomEntity(keyType.Player, rid)
                        for source in source_list:
                            if source.setFlag(keyType.SITUATION_FLAG_MAP.BOOM):
                                source.writeAttr("flag", source.flag)
                                TimerManager.addTimer(0.02,
                                                      lambda x: source.removeFlag(keyType.SITUATION_FLAG_MAP.BOOM),
                                                      source)
                        monster.cd[1] = 3
                if monster.cd[2] <= 0:
                    if monster.element["water"] == 1:
                        monster.reduceHp(0, dmg_type=35, eid=source.entity_id)
                        CreateBuff(source.room_id, source.entity_id, monster.entity_id, keyType.Monster,
                                   self.data_center.buff_info[6])
                        monster.cd[2] = 3

                if self.skillBeLit(source, conf.NORMAL_LIGHTNING_ALL_SKILL) and isinstance(monster,
                                                                                           ChestEntity) is False:
                    buff_id_list = self.data_center.skill_tree[conf.NORMAL_LIGHTNING_ALL_SKILL]['buff_id']
                    for buff_id in buff_id_list:
                        CreateBuff(source.room_id, source.entity_id, monster.entity_id, keyType.Monster,
                                   self.data_center.buff_info[buff_id])

            # Water Splash damage
            water_distance = self.data_center.skill_tree[conf.NORMAL_LIGHTNING_ALL_SKILL]['value'][0]
            if self.skillBeLit(source, conf.NORMAL_WATER_SKILL) and isinstance(monster, ChestEntity) is False:
                CreateBuff(source.room_id, source.entity_id, monster.entity_id, keyType.Monster,
                           self.data_center.buff_info[9])
                position = Vector3(monster.transform.position.x, monster.transform.position.y,
                                   monster.transform.position.z)
                self.waterSputteringSkillCreate(position, source, water_distance, monster)
                monster.dmg_target[3] += damage_value

                if monster.cd[0] <= 0:
                    if monster.element["burn"] == 1:
                        monster.reduceHp(0, dmg_type=33, eid=source.entity_id)
                        CreateBuff(source.room_id, source.entity_id, monster.entity_id, keyType.Monster,
                                   self.data_center.buff_info[11])
                        monster.cd[0] = 3
                if monster.cd[2] <= 0:
                    if monster.element["light"] == 1:
                        monster.reduceHp(0, dmg_type=35, eid=source.entity_id)
                        CreateBuff(source.room_id, source.entity_id, monster.entity_id, keyType.Monster,
                                   self.data_center.buff_info[6])
                        monster.cd[2] = 3

                if self.skillBeLit(source, conf.WATER_ADD_SKILL) and monster.dmg_target[3] >= 100 and \
                        isinstance(monster, ChestEntity) is False:
                    position = Vector3(monster.transform.position.x, monster.transform.position.y,
                                       monster.transform.position.z)
                    self.waterSkillCreate(position, source, monster)
                    monster.dmg_target[3] = 0

    def waterSputteringSkillCreate(self, position, source, distance, target):
        watersputteringskill = WaterSputteringSkillEntity(source.room_id)
        self.data_center.registerEntity(keyType.Skill, watersputteringskill)
        data = {
            keyType.Position: position,
            keyType.Source: source,
            keyType.Distance: distance,
            keyType.Target: target
        }
        watersputteringskill.initSkillData(data)
        room = self.data_center.getRoom(source.room_id)
        room.joinSkill(watersputteringskill.entity_id)

    def waterSkillCreate(self, position, source, target):
        waterskill = WaterSkillEntity(source.room_id)
        self.data_center.registerEntity(keyType.Skill, waterskill)
        data = {
            keyType.Position: position,
            keyType.Source: source,
            keyType.Target: target
        }
        waterskill.initSkillData(data)
        room = self.data_center.getRoom(source.room_id)
        room.joinSkill(waterskill.entity_id)

    def playerDamaged(self, msg):
        target_list = msg.target
        for player in target_list:
            player.reduceHp(10)

    def playerHelped(self, msg):
        target_list = msg.target
        for player in target_list:
            player.addHp(150)

    def flashSkillDeal(self, msg):
        source = msg.source
        target_list = msg.target
        dmg = self.data_center.skill_tree[conf.FLASH_PRODUCE_HURT]['value'][0]
        for monster_id in range(len(target_list)):
            monster = target_list[monster_id]
            if self.skillBeLit(source, conf.FLASH_PRODUCE_HURT):
                monster.reduceHp(dmg, eid=source.entity_id)

            # flash repulse monster
            if self.skillBeLit(source, conf.FLASH_REPULSED_ENEMY):
                repulse_distance = self.data_center.skill_tree[conf.FLASH_REPULSED_ENEMY]['value'][0]
                monster.repelMonster(msg.path_meet_target_angle_list[monster_id], repulse_distance)

            # flash let monster speed low
            if self.skillBeLit(source, conf.FLASH_LET_SPEED_lOW):
                buff_id_list = self.data_center.skill_tree[conf.FLASH_LET_SPEED_lOW]['buff_id']
                for buff_id in buff_id_list:
                    CreateBuff(source.room_id, source.entity_id, monster.entity_id, keyType.Monster,
                               self.data_center.buff_info[buff_id])

            # flash let monster easy get hurt
            if self.skillBeLit(source, conf.FLASH_LET_EASY_HURT):
                buff_id_list = self.data_center.skill_tree[conf.FLASH_LET_EASY_HURT]['buff_id']
                for buff_id in buff_id_list:
                    CreateBuff(source.room_id, source.entity_id, monster.entity_id, keyType.Monster,
                               self.data_center.buff_info[buff_id])

            # flash refresh skill cd
            if self.skillBeLit(source, conf.FLASH_REFRESH_SKILL) and monster.hp <= 0:
                source.cd[1] = 0
                source.writeAttr("cd", source.cd)
