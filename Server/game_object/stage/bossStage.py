import copy
from random import randint

from common.rpc_queue_module import RpcMessage
from common_server.timer import TimerManager
from game.utils import Vector3
from game_object.misc.entryEntity import EntryEntity
from setting import keyType
from setting.keyType import STAGE_STATE_MAP
from stage import StageInfo
from game_object.monster.bossMonsterEntity import BossMonsterEntity
from game_object.misc.bossCageEntryEntity import BossCageEntryEntity
from game_object.misc.itemEntity import ItemEntity
from typing import List
import logging

logger = logging.getLogger()


class BossStage(StageInfo):
    def __init__(self, rid, stage_info=None):
        super(BossStage, self).__init__(rid, stage_info)
        self.entries_list = [Vector3(15, 0, 15), Vector3(-15, 0, -15)]
        self.boss = None  # type: BossMonsterEntity or None
        self.recursive = False
        for key, stage_info in self.stage_info["batchs"].iteritems():
            if stage_info["maxTime"] == -1:
                self.recursive_index = int(key)
                break
        self.cage_positions = [Vector3(0, 0.2, -15.59), Vector3(15.59, 0.2, 0)]
        self.cages = []  # type: List[BossCageEntryEntity]

        self.entries_list = [Vector3(-14, 0, 14), Vector3(-14, 0, -14)]
        self.end_stage_timer = None

    def enterNextBatch(self):
        super(BossStage, self).enterNextBatch()
        if self.current_latest_time == -1 and not self.recursive:
            self.recursive_index = self.current_batch

        logger.info("recursive index is %d" % self.recursive_index)

    def tick(self, tick_time=0.02):
        if self.state == STAGE_STATE_MAP.End:
            return
        if self.boss and not self.boss.isAlive:
            if self.end_stage_timer is None:
                self.end_stage_timer = TimerManager.addTimer(3., self.endStage)
            return
        if self.current_batch == 0:
            self.enterNextBatch()
        if not self.isLastBatch:
            if self.isCurrentBatchDivider:
                if self.recursive:
                    self.current_batch = self.recursive_index
                    self.enterNextBatch()
            else:
                self.current_latest_time -= tick_time
                if self.current_latest_time <= 0.01 or len(self.room.monster_list) == 0:
                    self.enterNextBatch()
        if self.boss and self.boss.isAlive:
            if self.boss.isInvincible:
                if not self.recursive:  # boss become locked, recursively generate monster, generate entry item
                    logger.info("boss become locked, recursively generate monster, generate entry item")
                    self.generateCages()
                    self.recursive = True
                    self.enterNextBatch()
                self.handleCages()
            else:
                if self.recursive:
                    self.recursive = False
                    self.enterNextBatch()

    def handleCages(self):
        all_unlocked = True
        for cage in self.cages:
            if cage.isLocked:
                all_unlocked = False
                break
        if all_unlocked:  # all cages have been unlocked, release boss and clear cages
            logger.info("all cages have been unlocked, release boss")
            self.boss.removeInvincible()
            for cage in self.cages:
                self.room.removeEntity(keyType.Item, cage.entity_id)
            self.cages = []

    def generateCages(self):
        for position in self.cage_positions:
            entry_entity = BossCageEntryEntity(self.room_id, position, 13)
            self.data_center.registerEntity(keyType.Item, entry_entity)
            self.room.addEntity(keyType.Item, entry_entity.entity_id)
            self.cages.append(entry_entity)
            self.rpc_queue.push_msg(0, RpcMessage(
                "BattleHandler/GenerateDropItem", self.room.client_id_list, [],
                {"Item_type": 13, "Position": position.getDict(), "Entity_id": entry_entity.entity_id,
                 "Item": "Gun"}
            ))

    def generateMonster(self):
        create_list = []
        for item in self.getMonsters():
            monster_type = item["monsterType"]
            for pos in item["positions"]:
                data = {
                    keyType.Position: {"x": pos[0], "y": pos[1], "z": pos[2]},
                    keyType.Rotation: {"x": 0, "y": 0, "z": 0}
                }
                entity = StageInfo.monsterMap[monster_type](self.room.id)
                self.data_center.registerEntity(keyType.Monster, entity)
                entity.initMonsterData(data)
                monsterInfo = copy.deepcopy(self.data_center.monsterInfo[monster_type])
                monsterInfo["Hp"] *= self.stage_info["stageHP"]
                entity.initMonsterInfo(monsterInfo)
                self.room.addEntity(keyType.Monster, entity.entity_id)
                create_list.append(entity.entity_id)
                if monster_type == 6:
                    self.boss = entity
        ret = {"monsters": [self.data_center.getEntityByID(keyType.Monster, monster_eid).getMonsterInitData()
                            for monster_eid in create_list]}
        self.rpc_queue.push_msg(0, RpcMessage(
            "MonsterSyncHandler/GenerateMonster", self.room.client_id_list, [], ret
        )
                                )
        logger.debug("monsters generated")

    def endStage(self):
        self.state = keyType.STAGE_STATE_MAP.End
