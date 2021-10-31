import json

from common.common_library_module import Singleton
from setting import keyType
from common_server.timer import TimerManager
import logging
from typing import TYPE_CHECKING, List, Union, Dict
import numpy as np

if TYPE_CHECKING:
    from game_object.room.roomEntity import Room
    from game_object.entity import Entity
    from game_object.player.playerEntity import PlayerEntity
    from game_object.monster.monsterEntity import MonsterEntity
    from game_object.misc.itemEntity import ItemEntity
    from game_object.buff.buffBase import Buff

    from game_object.monster.chestEntity import ChestEntity
    from argparse import Namespace
logger = logging.getLogger()


@Singleton
class DataCenter(object):
    def __init__(self):
        self.config = None
        self.normal_skill = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 18]
        self.element_skill = [14, 16, 19]
        self.skill_data = {}
        self.id_idx = 0
        self.weapon_info = {}
        self.monsterGenerateInfo = {}
        self.monsterInfo = {}
        self.buff_info = {}
        self.mapInfoDict = {}
        self.gameStageInfo = GameStage()
        self.help_list = []
        self.skill_tree = []
        self.rooms = {}
        self.entities = {
            keyType.Player: {},  # type: Dict[int, PlayerEntity]
            keyType.Monster: {},
            keyType.Skill: {},
            keyType.Chest: {},
            keyType.Item: {},
            keyType.Buff: {},
        }
        self.initWeaponInfo("Weapon.json")
        self.initMonsterInfo("monstersInfo.json")
        self.initBuffInfo("buff.json")
        self.initSkillTreeInfo("talent.json")
        self.initSkillDate("skill.json")
        self.initMapInfo()

    def setConfig(self, config):
        # type: (Namespace) -> None
        self.config = config

    def registerEntity(self, entity_type, entity, entity_id=None):
        # type: (str, Entity, int) -> None
        if entity_id is None:
            entity.entity_id = self.generateEid()
        else:
            entity.entity_id = entity_id
        self.entities[entity_type][entity.entity_id] = entity
        logger.debug("register entity, type:%s, id:%d" % (entity_type, entity.entity_id))

    def getEntityByID(self, entity_type, eid):
        # type: (str, int) -> Union[MonsterEntity, PlayerEntity, ItemEntity]
        entity = self.entities[entity_type].get(eid, None)
        return entity

    def destroyEntity(self, entity_type, eid):
        entity = self.entities[entity_type].get(eid, None)
        if entity:
            entity.onDestroy()
            entity.deleted = True
            if entity.timer:
                TimerManager.cancel(entity.timer)
            self.entities[entity_type].pop(eid)
            logger.debug("%s destroyed, id: %d, type: %s" % (entity_type, eid, entity.__class__.__name__))

    def getPlayerByClientID(self, client_id):
        # type: (int) -> Union[PlayerEntity, None]
        for entity_id, entity in self.entities[keyType.Player].iteritems():
            if entity is None:
                continue
            if entity.client_id == client_id:
                return entity
        return None

    def getSkillByEid(self, eid):
        for _, entity in self.entities[keyType.Skill].iteritems():
            if entity is None:
                continue
            if entity.client_id == eid:
                return entity
        return None

    def getRoom(self, rid):
        # type: (int) -> Room
        return self.rooms.get(rid, None)

    def getRoomEntity(self, entity_type, rid):
        # type: (str, int) -> List[Union[PlayerEntity, MonsterEntity, ItemEntity, ChestEntity, Buff]]
        room = self.rooms.get(rid, None)
        res = []
        entity_list = getattr(room, entity_type.lower() + "_list", None)
        if entity_list is None:
            return []
        for eid in entity_list:
            entity = self.getEntityByID(entity_type, eid)
            res.append(entity)
        return res

    @property
    def allRooms(self):
        # type: () -> List[Room]
        return self.rooms.values()

    def updateRoom(self, room):
        # type: (Room) -> None
        self.rooms[room.id] = room

    def removeRoom(self, rid):
        # type: (int) -> None
        if self.rooms.__contains__(rid):
            self.clearRoom(rid)
            self.rooms.pop(rid)
            logger.debug("remove room: %d" % rid)

    def clearRoom(self, rid):
        # type: (int) -> None
        self.getRoom(rid).clearRoomBesidePlayer(keep_player=False)
        logger.info("room reset %d" % rid)

    def removePlayer(self, hid):
        """
            set player state to Deleted
        """
        player = self.getPlayerByClientID(hid)
        if player is None:
            return
        player.state = keyType.PLAYER_STATE_MAP.Deleted
        logger.debug("delete player, client_id: %d, id: %d, waiting remove" % (hid, player.entity_id))

    def removeInGamePlayer(self, eid):
        # type: (int) -> None
        """
            remove or delete player from room or whole game depends on state deleted or active
        """
        entity = self.getEntityByID(keyType.Player, eid)
        if entity is None:
            return
        room = self.getRoom(entity.room_id)
        if room is None:
            return
        if entity.entity_id in room.player_list:
            room.player_list.remove(entity.entity_id)
            if entity.state == keyType.PLAYER_STATE_MAP.Deleted:
                self.entities[keyType.Player].pop(entity.entity_id)
                logger.debug("delete player %d from game" % entity.entity_id)
            else:
                self.entities[keyType.Player][entity.entity_id].initialize(entity.entity_id, -1, entity.client_id)
                entity.state = keyType.PLAYER_STATE_MAP.Active

                logger.debug("remove player: %d" % entity.entity_id)

    '''
        init data from json files
    '''
    def initWeaponInfo(self, file_name):
        with open(file_name) as f:
            json_data = json.loads(f.read())
            for item in json_data:
                data = {}
                for key, value in item.items():
                    data[str(key)] = value
                self.weapon_info[data["_wid"]] = data

    def initMonsterInfo(self, file_name):
        with open(file_name) as f:
            json_data = json.loads(f.read())
            for item in json_data:
                data = {}
                for key, value in item.items():
                    data[str(key)] = value
                self.monsterInfo[data["monsterType"]] = data

    def getMapInfoWithStageID(self, sid):
        # type: (int) -> MapInfo
        return self.mapInfoDict.get(sid, None)

    def initMapInfo(self):
        fileName = ["./arena_navmesh_matrix.txt", "./normal_navmesh_matrix.txt", "./arena_navmesh_matrix.txt",
                    "./normal_navmesh_matrix.txt", "./arena_navmesh_matrix.txt", "./arena_navmesh_matrix.txt"]
        for idx in range(len(fileName)):
            mapInfoList = []
            with open(fileName[idx], 'r') as mapFile:
                top = self.getInfoWithLine(mapFile.readline())
                left = self.getInfoWithLine(mapFile.readline())
                line = mapFile.readline()
                while line:
                    mapInfoList = [[int(i) for i in line if "9" >= i >= "0"]] + mapInfoList
                    line = mapFile.readline()
            map_array = np.array(mapInfoList)
            self.mapInfoDict[idx + 1] = MapInfo(map_array.transpose(), top, left)

    @staticmethod
    def getInfoWithLine(line):
        begin = line.find('=')
        end = line.find('\n')
        line = line[begin + 1: end]
        return int(float(line))

    def initBuffInfo(self, file_name):
        with open(file_name) as f:
            json_data = json.loads(f.read())
            for buff_info in json_data:
                self.buff_info[buff_info["buff_id"][0]] = buff_info
                self.buff_info[buff_info["buff_id"][0]]["buff_id"] = buff_info["buff_id"][0]

    def initSkillDate(self, file_name):
        with open(file_name) as f:
            json_data = json.loads(f.read())
            for buff_info in json_data:
                self.skill_data = buff_info

    def initSkillTreeInfo(self, file_name):
        node = {
            'fa_id': [],
            'type': None,
            'level': 0,
            'high_level': 0,
            'value': [],
            'child': [],
            'buff_id': [],
            'name': None,
            'description': None
        }
        self.skill_tree.append(node)
        with open(file_name) as f:
            json_data = json.load(f)
            for skill in json_data:
                value = []
                value_count = 0
                for key in skill.keys():
                    if "value" in key:
                        value_count += 1
                for i in range(1, value_count + 1):
                    value.append(skill["value" + str(i)])
                if len(skill['child_nodes']) == 1 and skill['child_nodes'][0] == -1:
                    skill['child_nodes'] = []
                node = {
                    'fa_id': skill['father_nodes'],
                    'active': 0,
                    'type': skill['talent_type'],
                    'level': 0,
                    'high_level': 1,
                    'value': value,
                    'child': skill['child_nodes'],
                    'buff_id': skill['buff_id'],
                    'name': skill['talent_name'],
                    'description': skill['description']
                }
                self.createSkillTree(skill['id'], node)

    def createSkillTree(self, eid, node):
        while eid >= len(self.skill_tree):
            self.skill_tree.append({})
        self.skill_tree[eid] = node
        if self.skill_tree[eid]['fa_id'] and 0 in self.skill_tree[eid]['fa_id']:
            self.skill_tree[0]['child'].append(eid)

    def generateEid(self):
        # t = time.time()
        # t = str(int(t))[-9:-3] + str(self.id_idx)
        self.id_idx += 1
        return self.id_idx


class GameStage(object):
    def __init__(self):
        self.allStageInfo = {}  # stageID : info
        self.getInfoFromFile("gameStageInfo.json")

    def getInfoFromFile(self, file_name):
        with open(file_name) as f:
            json_data = json.loads(f.read())
            for info in json_data:
                info_data = {"stageID": info["stageID"], "stageThreat": float(info["stageThreat"]), "stageHP": float(info["stageHP"]),
                             "batchs": {}, "player_positions": info["player_positions"]}
                for batch in info["batchs"]:
                    batch_info = {"maxTime": float(batch["maxTime"]), "monsters": []}
                    for monster in batch["monsters"]:
                        monsterInfo = {"monsterType": int(monster["monsterType"]), "positions": []}
                        for pos in monster["positions"]:
                            monsterInfo["positions"].append([float(pos["x"]), float(pos["y"]), float(pos["z"])])
                        batch_info["monsters"].append(monsterInfo)
                    info_data["batchs"][int(batch["batchID"])] = batch_info
                self.allStageInfo[int(info["stageID"])] = info_data

    def getStageInfo(self, sid):
        return self.allStageInfo[sid]

    def __len__(self):
        return len(self.allStageInfo)


class MapInfo(object):
    def __init__(self, map_list, top, left):
        # type: (np.ndarray, int, int) -> None
        self.mapList = map_list
        self.top = top
        self.left = left

    def isCellEquals(self, x, y, value):
        # type: (float, float, int) -> bool
        return self.mapList[int(x) - self.left][int(y) + self.top] == value

    def setMapRange(self, range_x_start, range_x_end, range_y_start, range_y_end, value):
        # type: (int, int, int, int, int) -> None
        self.mapList[range_x_start: range_x_end, range_y_start: range_y_end] = value

    def mapArrayToImage(self):
        # type: () -> np.ndarray
        img_raw = self.mapList * 30
        return img_raw

