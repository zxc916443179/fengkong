import copy
from common.rpc_queue_module import RpcMessage
from game.utils import Vector3
from game_object.misc.triggerLightEntity import TriggerLightEntity
from game_object.monster.lightTrickEntity import LightTrickEntity, LightManager
from stage import StageInfo
from setting import keyType
from game_object.monster.monsterEntity import MonsterEntity
from game_object.misc.entryEntity import EntryEntity
import logging

logger = logging.getLogger()


class EscapeStage(StageInfo):
    trigger_entity_map = {
        0: {"positions": [Vector3(-20.75, 0.7, 7.94), Vector3(-8.5, 0.7, 8.71)],
            "range_in_map": [[[-17, -12], [5, 11]]]
            },
        2: {"positions": [Vector3(26.05, 0.7, 40.65), Vector3(15.83, 0.7, 26.70)],
            "range_in_map": [[[11, 15], [25, 31]]]
            },
        1: {"positions": [Vector3(20.47, 0.7, -38.56), Vector3(-1, 0.7, -47)],
            "range_in_map": [[[6, 10], [-44, -39]]]
            }
    }

    check_points = [Vector3(28, 0, 33), Vector3(20, 0, 14), Vector3(-7, 0, 10), Vector3(0.5, 0, 27), Vector3(-1, 0, -21),
                    Vector3(-27.2, 0, -22.4)]
    checkpoints_active_distance = 7 ** 2

    entry_positions = [None, Vector3(-40, 0, -24.5), None, Vector3(-1.7, 0, 54.2)]

    blue_light_positions = [Vector3(15, 0, 22), Vector3(-7, 0, -20),
                            Vector3(-1, 0, 32), Vector3(-6.5, 0, 11)]

    red_light_positions = [Vector3(21, 0, 22), Vector3(-1, 0, 9),
                           Vector3(1, 0, 25.5), Vector3(-1.5, 0, -26)]

    def __init__(self, rid, stage_info=None):
        super(EscapeStage, self).__init__(rid, stage_info)
        self.door_boss = None  # type: MonsterEntity or None
        self.door_position = None  # type: Vector3 or None
        self.escape_index = 0
        self.entry_count = [2, 2, 2]
        self.entry_timer = [None, None, None]
        self.active_checkpoint = 0
        self.latest_checkpoint = 0

    def endStage(self):
        entity = EntryEntity(self.room_id, self.door_position, 1)
        self.data_center.registerEntity(keyType.Item, entity)
        self.room.addEntity(keyType.Item, entity.entity_id)
        self.rpc_queue.push_msg(0, RpcMessage(
            "BattleHandler/HandleNormalEntryShow", self.room.client_id_list, [],
            {"Entry_id": self.escape_index // 2}
        ))
        self.state = keyType.STAGE_STATE_MAP.End
        LightManager.clearRoomLights(self.room_id)

    def tick(self, tick_time=0.02):
        if self.current_batch == 0:
            self.enterNextBatch()
        if not self.isLastBatch:
            if self.isCurrentBatchDivider:
                if self.active_checkpoint < self.latest_checkpoint:
                    self.enterNextBatch()
                    self.active_checkpoint += 1
            else:
                self.current_latest_time -= 0.02
                if self.current_latest_time <= 0.01 or len(self.room.monster_list) == 0:
                    self.enterNextBatch()
        self.handlePlayerEnterCheckpoints()
        if self.door_boss and not self.door_boss.isAlive and self.state != keyType.STAGE_STATE_MAP.End:
            self.endStage()

    def handlePlayerEnterCheckpoints(self):
        for i, check_point in enumerate(self.check_points):
            for player in self.data_center.getRoomEntity(keyType.Player, self.room_id):
                if player.last_position == check_point:
                    continue
                if Vector3.Distance(check_point, player.transform.position) <= self.checkpoints_active_distance:
                    if i > self.latest_checkpoint:
                        self.latest_checkpoint = i
                    player.last_position = check_point

    def enterNextBatch(self):
        if self.current_batch < self.batch_number:
            self.current_batch += 1
            logger.debug("enter batch %d" % self.current_batch)
            self.updateCurrentBatchInfo()
            if self.current_batch == 1:
                self.generateChest()
                self.generateLight()
            self.generateMonster()
        return self.state

    def generateLight(self):
        blue_lights = []
        red_lights = []
        for position in EscapeStage.blue_light_positions:
            blue_light = LightTrickEntity(self.room_id, 200, position, Vector3(0, 0, 0))
            blue_lights.append(blue_light)
            self.data_center.registerEntity(keyType.Chest, blue_light)
            self.room.addEntity(keyType.Chest, blue_light.entity_id)
            LightManager.registerLight(self.room_id, "blue", blue_light)
        for position in EscapeStage.red_light_positions:
            red_light = LightTrickEntity(self.room_id, 201, position, Vector3(0, 0, 0))
            red_lights.append(red_light)
            self.data_center.registerEntity(keyType.Chest, red_light)
            self.room.addEntity(keyType.Chest, red_light.entity_id)
            LightManager.registerLight(self.room_id, "red", red_light)
        ret = {"monsters": [blue_light.getMonsterInitData() for blue_light in blue_lights] + [
            red_light.getMonsterInitData() for red_light in red_lights]
               }
        self.rpc_queue.push_msg(0, RpcMessage(
            "MonsterSyncHandler/GenerateMonster", self.room.client_id_list, [], ret
        )
                                )
        logger.info("generate blue and red light trick entity")
        LightManager.handleLightHit(blue_lights[0], "blue")
        LightManager.handleLightHit(red_lights[0], "red")
        for batch_no, batch in EscapeStage.trigger_entity_map.iteritems():
            if self.room.stage_number == 4:
                if batch_no == 2:  # skip last batch in second loop
                    continue
            positions = batch["positions"]
            for position in positions:
                trigger_entity = TriggerLightEntity(self.room_id, position, 10, batch_no,
                                                    ranges_in_map=batch["range_in_map"])
                self.data_center.registerEntity(keyType.Item, trigger_entity)
                self.room.addEntity(keyType.Item, trigger_entity.entity_id)
                self.rpc_queue.push_msg(0, RpcMessage(
                    "BattleHandler/GenerateDropItem", self.room.client_id_list, [],
                    {"Item_type": 10, "Position": trigger_entity.transform.position.getDict(),
                     "Entity_id": trigger_entity.entity_id, "Item": "Gun"}
                ))

    def generateMonster(self):
        create_list = []
        door_bosses = []
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
                if monster_type == 5:
                    door_bosses.append(entity)
        ret = {"monsters": [self.data_center.getEntityByID(keyType.Monster, monster_eid).getMonsterInitData() for
                            monster_eid in create_list]}
        self.rpc_queue.push_msg(0, RpcMessage(
            "MonsterSyncHandler/GenerateMonster", self.room.client_id_list, [], ret
        )
                                )
        # send_idx = 0
        # while send_idx <= len(ret["monsters"]) // 5:
        #     send = {"monsters": ret["monsters"][send_idx * 5: (send_idx + 1) * 5]}
        #     self.rpc_queue.push_msg(0, RpcMessage(
        #         "MonsterSyncHandler/GenerateMonster", self.room.client_id_list, [], send
        #     )
        #                             )
        #     send_idx += 1
        logger.debug("monsters generated")
        if not len(door_bosses) == 0:
            self.escape_index = 1 if self.room.stage_number == 2 else 3
            self.door_boss = door_bosses[self.escape_index]
            self.door_position = self.entry_positions[self.escape_index]
            logger.info("escape place in position %s" % self.entry_positions[self.escape_index].getDict())
