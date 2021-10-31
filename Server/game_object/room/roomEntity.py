import logging
import random
import time

from PIL import Image

from common.rpc_queue_module import RpcMessage, RpcQueue
from common_server.timer import TimerManager
from common_server.data_module import DataCenter
from game_object.player.playerEntity import PlayerEntity
from game_object.stage import CreateStageInfo
from setting import keyType
from setting.keyType import ROOM_STATE_MAP, PLAYER_STATE_MAP
from game.nav_module import NavAgent
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from common_server.data_module import MapInfo

logger = logging.getLogger()


class Room(object):
    room_idx = 0

    def __init__(self, host_eid=-1, host_name="", title=""):
        self.monster_list = []  # eid
        self.player_list = []  # eid
        self.id = Room.generateId()
        self.chest_list = []
        self.item_list = []
        self.skill_list = []
        self.buff_list = []
        self.element_list = []
        self.lightning_vis_dic = {}
        self.state = 0  # waiting 0, creating 1, ongoing 2
        self.map = None  # type: MapInfo or None
        self.current_stage = 1
        self.stageInfo = None
        self.data_center = DataCenter()
        self.host_eid = host_eid
        self.host_name = host_name
        self.title = title
        self.rpc_queue = RpcQueue()
        self.nav_agent = NavAgent()
        self.stage_number = 1
        self.show_map_timer = None
        self.delay_for_generate_monster = -1

    def isHost(self, eid):
        return self.host_eid == eid

    def isAllPlayersReady(self, except_host=True):
        if len(self.player_list) < 2:
            return False
        for eid in self.player_list:
            player = self.data_center.getEntityByID(keyType.Player, eid)
            if except_host:
                if player.entity_id == self.host_eid:
                    continue
            if player.state != PLAYER_STATE_MAP.Ready:
                return False
        return True

    @property
    def isOnGoing(self):
        # type: () -> bool
        return self.state == ROOM_STATE_MAP.Ongoing or self.state == ROOM_STATE_MAP.Bonus

    @property
    def currentMap(self):
        # type: () -> MapInfo
        return self.map

    @property
    def isStageEnd(self):
        return self.stageInfo.isStageEnd

    @property
    def client_id_list(self):
        res = []
        for eid in self.player_list:
            entity = self.data_center.getEntityByID(keyType.Player, eid)
            res.append(entity.client_id)
        return res

    def addEntity(self, entity_type, eid):
        # type: (str, int) -> None
        entity_list = getattr(self, entity_type.lower() + "_list")
        entity_list.append(eid)

    def removeEntity(self, entity_type, eid):
        # type: (str, int) -> None
        self.data_center.destroyEntity(entity_type, eid)
        entity_list = getattr(self, entity_type.lower() + "_list")
        if eid in entity_list:
            entity_list.remove(eid)
        if entity_type in [keyType.Monster, keyType.Player]:
            for buff_eid in self.buff_list:
                buff = self.data_center.getEntityByID(keyType.Buff, buff_eid)
                if buff.target == eid:
                    buff.removeBuff()

    def joinPlayer(self, player):
        # type: (PlayerEntity) -> None
        if player.entity_id not in self.player_list:
            player.room_id = self.id
            player.state = PLAYER_STATE_MAP.Not_Ready
            logger.debug("set player state to in game, id: %d, state: %d" % (player.entity_id, player.state))
            self.player_list.append(player.entity_id)
        else:
            logger.error("player already exists")

    def joinSkill(self, eid):
        self.skill_list.append(eid)

    def removeSkill(self, eid):
        self.data_center.destroyEntity(keyType.Skill, eid)
        if eid in self.skill_list:
            self.skill_list.remove(eid)

    @property
    def getAlivePlayerCount(self):
        # type: () -> int
        cnt = 0
        for eid in self.player_list:
            entity = self.data_center.getEntityByID(keyType.Player, eid)
            if entity.isAlive:
                cnt += 1
        return cnt

    def getPlayersPosition(self):
        # type: () -> List[dict]
        ret = []
        if self.state >= 1:
            for eid in self.player_list:
                entity = self.data_center.getEntityByID(keyType.Player, eid)
                ret.append(entity.getPlayerData())
        return ret

    @staticmethod
    def generateId():
        Room.room_idx += 1
        return Room.room_idx

    def getRoomPlayer(self):
        # type: () -> List[int]
        return self.player_list

    def getRoomMonster(self):
        # type: () -> List[int]
        return self.monster_list

    def enterStageWithNum(self, sid):
        logger.info("enter stage %d" % sid)
        info = self.data_center.gameStageInfo.getStageInfo(sid)
        self.map = self.data_center.getMapInfoWithStageID(sid)
        self.stageInfo = CreateStageInfo(self.id, info)
        if self.data_center.config.show_map:
            self.show_map_timer = TimerManager.addRepeatTimer(10, self.showMap)

    def updateNextHost(self, player_eid):
        if len(self.player_list) > 1:
            for i, eid in enumerate(self.player_list):
                if eid == player_eid:
                    self.host_eid = self.player_list[(i + 1) % len(self.player_list)]
                    logger.info("switch to next host")
                    break

    def startGame(self):
        self.clearRoomBesidePlayer()
        self.current_stage += 1
        if self.stage_number in [2, 4]:
            self.current_stage = 1
        if self.stage_number == 5:
            self.current_stage = 3
        self.stage_number += 1
        self.enterStageWithNum(self.stage_number)
        self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/" + ROOM_STATE_MAP.STAGE_ID_MAP[self.current_stage],
                                              self.client_id_list, [], {"Stage_id": self.stage_number}))
        self.state = ROOM_STATE_MAP.SyncingProgress
        logger.info("start game")

    def clearRoomBesidePlayer(self, keep_item=False, keep_player=True):
        while len(self.monster_list) > 0:
            self.removeEntity(keyType.Monster, self.monster_list[-1])

        if not keep_item:
            while len(self.item_list) > 0:
                self.removeEntity(keyType.Item, self.item_list[-1])

        while len(self.skill_list) > 0:
            self.removeEntity(keyType.Skill, self.skill_list[-1])
        while len(self.chest_list) > 0:
            self.removeEntity(keyType.Chest, self.chest_list[-1])

        while len(self.buff_list) > 0:
            self.removeEntity(keyType.Buff, self.buff_list[-1])
        if not keep_player:
            while len(self.player_list) > 0:
                self.removeEntity(keyType.Player, self.player_list[-1])
        if self.show_map_timer is not None:
            TimerManager.cancel(self.show_map_timer)
            self.show_map_timer = None
        logger.info("clear room beside player")

    def updateMap(self, x, z, move_away=False, value=2):
        # type: (int or List, int or List, bool, int) -> None
        if move_away:
            value = 0
        if type(x) is list and type(z) is list:
            x = [int(i) - self.map.left for i in x]
            z = [int(i) + self.map.top for i in z]
            self.map.setMapRange(*(x + z), value=value)
            return
        self.map.mapList[int(x) - self.map.left][int(z) + self.map.top] = value

    def showMap(self):
        img_raw = self.map.mapList * 30
        for player_eid in self.player_list:
            pos = self.data_center.getEntityByID(keyType.Player, player_eid).transform.position
            img_raw[int(pos.x) - self.map.left, int(pos.z) + self.map.top] = 240
        Image.fromarray(img_raw).resize((140 * 3, 120 * 3)).show()

    def overSkillEnhancement(self):
        element_list = []
        source_list = self.getRoomPlayer()
        for source_eid in source_list:
            source = self.data_center.getEntityByID(keyType.Player, source_eid)
            if source.skill_dict.flag != 0 and source.skill_dict.flag in self.data_center.element_skill:
                element_list.append(source.skill_dict.flag)
            elif source.skill_dict.flag != 0:
                element_list.append(source.skill_dict.flag - 1)
        for source_eid in source_list:
            source = self.data_center.getEntityByID(keyType.Player, source_eid)
            skill_can_be_light = []
            skill_tree = self.data_center.skill_tree
            for skill_id in range(len(skill_tree)):
                if skill_id in element_list:
                    continue
                info = source.skill_dict.skill_dict.get(skill_id)
                if info is None:
                    skill_fa_id = skill_tree[skill_id]['fa_id']
                    for fa_id in skill_fa_id:
                        if source.skill_dict.skill_dict.get(fa_id) is not None and source.skill_dict.skill_dict[fa_id]['active'] == 1:
                            skill_can_be_light.append(skill_id)
                            break
                elif info["level"] < skill_tree[skill_id]["high_level"] and info['active'] == 1:
                    skill_can_be_light.append(skill_id)
            random.shuffle(skill_can_be_light)
            normal_skill = []
            level1_skill = []
            for skill_id in skill_can_be_light:
                if skill_id in self.data_center.normal_skill:
                    normal_skill.append(skill_id)
                elif skill_id in self.data_center.element_skill:
                    level1_skill.append(skill_id)
            if source.skill_dict.num < 1:
                source.skill_dict.skill_can_be_light[0] = normal_skill[0]
                source.skill_dict.skill_can_be_light[2] = normal_skill[1]
                source.skill_dict.skill_can_be_light[1] = level1_skill[0]
                element_list.append(level1_skill[0])
            elif source.skill_dict.flag != 0:
                if source.skill_dict.flag in self.data_center.element_skill:
                    source.skill_dict.skill_can_be_light[0] = normal_skill[0]
                    source.skill_dict.skill_can_be_light[2] = normal_skill[1]
                    source.skill_dict.skill_can_be_light[1] = source.skill_dict.flag + 1
                else:
                    source.skill_dict.skill_can_be_light[0] = normal_skill[0]
                    source.skill_dict.skill_can_be_light[1] = normal_skill[1]
                    source.skill_dict.skill_can_be_light[2] = normal_skill[2]
            else:
                source.skill_dict.skill_can_be_light[0] = normal_skill[0]
                source.skill_dict.skill_can_be_light[2] = normal_skill[1]
                source.skill_dict.skill_can_be_light[1] = level1_skill[0]
                element_list.append(level1_skill[0])
        logger.info("hand room skill")
