import copy
from common_server.data_module import DataCenter
from common.rpc_queue_module import RpcQueue, RpcMessage
from game.utils import Vector3
from setting import keyType
from setting.keyType import STAGE_STATE_MAP
import logging

from game_object.monster.bombMonsterEntity import BombMonsterEntity
from game_object.monster.normalMonsterEntity import NormalMonsterEntity
from game_object.monster.fixedMonsterEntity import FixedMonsterEntity
from game_object.monster.turretMonsterEntity import TurretMonsterEntity
from game_object.monster.assassinationMonsterEntity import AssassinationMonsterEntity
from game_object.monster.bossMonsterEntity import BossMonsterEntity
from game_object.monster.chestEntity import ChestEntity
logger = logging.getLogger()


class StageInfo(object):
    monsterMap = {
        1: BombMonsterEntity,
        2: NormalMonsterEntity,
        3: FixedMonsterEntity,
        4: TurretMonsterEntity,
        5: AssassinationMonsterEntity,
        6: BossMonsterEntity
    }

    def __init__(self, rid, stage_info=None, map_info=None):
        # type: (int, dict, list) -> None
        self.room_id = rid
        self.data_center = DataCenter()
        self.rpc_queue = RpcQueue()
        self.room = self.data_center.getRoom(self.room_id)
        self.state = STAGE_STATE_MAP.Begin            # 0 begin, 1 ongoing, 2 end
        self.stage_info = stage_info
        self.current_batch = 0
        self.batch_number = 0
        self.current_batch_monster = []
        self.current_latest_time = 0
        self.initInfo(stage_info)
        
    def initInfo(self, stage_info):
        self.batch_number = len(stage_info["batchs"]) - 1
        self.state = STAGE_STATE_MAP.Ongoing

    def enterNextBatch(self):
        if self.current_batch < self.batch_number:
            self.current_batch += 1
            logger.debug("enter batch %d" % self.current_batch)
            self.updateCurrentBatchInfo()
            if self.current_batch == 1:
                self.generateChest()
            self.generateMonster()
        return self.state

    @property
    def isStageEnd(self):
        return self.state == STAGE_STATE_MAP.End

    @property
    def chestInfo(self):
        # type: () -> list[dict]
        if self.stage_info["batchs"].__contains__(0):
            return self.stage_info["batchs"][0]["monsters"]
        else:
            return []

    @property
    def isLastBatch(self):
        return self.current_batch >= self.batch_number

    def updateCurrentBatchInfo(self):
        self.current_latest_time = self.stage_info["batchs"][self.current_batch]["maxTime"]
        self.current_batch_monster = self.stage_info["batchs"][self.current_batch]["monsters"]

    def getMonsters(self):
        return self.current_batch_monster

    @property
    def isCurrentBatchDivider(self):
        return self.current_latest_time == -1

    def tick(self, tick_time=0.02):
        if self.state == STAGE_STATE_MAP.End:
            return
        if self.current_batch == 0:
            self.enterNextBatch()
        if not self.isLastBatch:
            self.current_latest_time -= 0.02
            if self.current_latest_time <= 0.01 or len(self.room.monster_list) == 0:
                self.enterNextBatch()

    def endStage(self):
        pass

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
        ret = {"monsters": [self.data_center.getEntityByID(keyType.Monster, monster_eid).getMonsterInitData() for
                            monster_eid in create_list]}
        send_idx = 0
        while send_idx <= len(ret["monsters"]) // 10:
            send = {"monsters": ret["monsters"][send_idx * 10: (send_idx + 1) * 10]}
            self.rpc_queue.push_msg(0, RpcMessage(
                    "MonsterSyncHandler/GenerateMonster", self.room.client_id_list, [], send
                )
            )
            send_idx += 1
        logger.debug("monsters generated")

    def createMonster(self, data, monster_type, room_id):
        room = self.data_center.getRoom(room_id)
        entity = StageInfo.monsterMap[monster_type](room_id)
        self.data_center.registerEntity(keyType.Monster, entity)
        entity.initMonsterData(data)
        entity.initMonsterInfo(self.data_center.monsterInfo[monster_type])
        room.addEntity(keyType.Monster, entity.entity_id)
        return entity

    def generateChest(self):
        create_list = []
        for item in self.chestInfo:
            chest_type = item["monsterType"]
            for pos in item["positions"]:
                data = {
                    keyType.Position: {"x": pos[0], "y": pos[1], "z": pos[2]},
                    keyType.Rotation: {"x": 0, "y": 0, "z": 0}
                }
                chest = ChestEntity(self.room.id, Vector3(from_dict=data[keyType.Position]), Vector3(
                    from_dict=data[keyType.Rotation]))
                chest.initMonsterInfo(self.data_center.monsterInfo[chest_type])
                self.data_center.registerEntity(keyType.Chest, chest)
                self.room.addEntity(keyType.Chest, chest.entity_id)
                create_list.append(chest)
        ret = {"monsters": [chest.getMonsterInitData() for chest in create_list]}
        self.rpc_queue.push_msg(0, RpcMessage(
                "MonsterSyncHandler/GenerateMonster", self.room.client_id_list, [], ret
            )
        )
        logger.debug("chest generated")
