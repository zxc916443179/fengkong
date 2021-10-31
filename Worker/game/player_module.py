import logging

from common import conf
from common.common_library_module import Singleton
from common.rpc_queue_module import RpcQueue, RpcMessage
from common_server.data_module import DataCenter
from game_object.room.roomEntity import Room
from setting import keyType
from setting.keyType import ROOM_STATE_MAP, PLAYER_STATE_MAP
from typing import List

logger = logging.getLogger()


@Singleton
class PlayerModule(object):
    def __init__(self):
        self.rpc_queue = RpcQueue()
        self.data_center = DataCenter()
        self.player_start_index = 0
        self.playerInitData = [{
            "Position": {"x": 10., "y": 0, "z": 10.}, "Rotation": {"x": 0., "y": 0., "z": 0.}, "Name": "test1",
            "Money": 0, "Speed": 5.
        }, {
            "Position": {"x": -10., "y": 0, "z": -10.}, "Rotation": {"x": 0., "y": 0., "z": 0.}, "Name": "Test2",
            "Money": 0, "Speed": 5.
        }]

    def fetchData(self):
        # type: () -> List[Room]
        return self.data_center.allRooms

    def BroadCastPosition(self, room):
        # type: (Room) -> None
        pass

    def broadCastActivateState(self, room):
        ret = [self.data_center.getEntityByID(keyType.Player, eid).getPlayerBasicInfo() for eid in room.player_list]
        self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/UpdatePlayerActivateState", room.client_id_list, [],
                                              {"Players": ret}))

    def updateAndBroadCastSyncState(self, room):
        # type: (Room) -> None
        progress_meter = 0.0
        for eid in room.player_list:
            player = self.data_center.getEntityByID(keyType.Player, eid)
            progress_meter += player.progress
        progress_meter /= len(room.player_list)
        logger.debug("sync progress %f" % progress_meter)
        if progress_meter >= 0.99:
            for eid in room.player_list:
                player = self.data_center.getEntityByID(keyType.Player, eid)
                player.state = PLAYER_STATE_MAP.In_Game
                player.progress = 0.0  # reset progress to zero
                for i, data in enumerate(self.playerInitData):
                    data["Position"] = room.stageInfo.stage_info["player_positions"][i]
                player.initPlayerData(self.playerInitData[self.player_start_index % 2])
                self.player_start_index += 1
                logger.debug("set player state to in game, id: %d, state: %d" % (eid, player.state))
                logger.debug("Player skill is %s" % player.skill_dict.skill_dict)
            ret = {
                "Players": [self.data_center.getEntityByID(keyType.Player, eid).getPlayerStatInfo() for eid in
                            room.player_list]
            }
            self.rpc_queue.push_msg(0,
                                    RpcMessage("PlayerSyncHandler/AllPlayerHasLoadGame", room.client_id_list, [], ret))
            logger.debug("All player has loaded game, start game")
            room.state = ROOM_STATE_MAP.CreatePlayer

    def createPlayer(self, room):
        # type: (Room) -> None
        room.state = ROOM_STATE_MAP.InStory
        for eid in room.player_list:
            self.data_center.getEntityByID(keyType.Player, eid).state = PLAYER_STATE_MAP.In_Story

    def updateBuffs(self, room):
        # type: (Room) -> None
        for buff in self.data_center.getRoomEntity(keyType.Buff, room.id):
            if buff:
                buff.tick(conf.MODULE_PLAYER_TICK)

    def updateInStory(self, room):
        # type: (Room) -> None
        for eid in room.player_list:
            if self.data_center.getEntityByID(keyType.Player, eid).state != PLAYER_STATE_MAP.End_Story:
                return
        self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/ChangeGameStage", room.client_id_list, [],
                                              {"Stage_id": -1}))

        for eid in room.player_list:
            self.data_center.getEntityByID(keyType.Player, eid).state = PLAYER_STATE_MAP.In_Game
        logger.info("all player have finish story, get in game")
        logger.info("waiting monster generate")
        room.state = ROOM_STATE_MAP.CreateMonster

    def handleZombiePlayers(self, room):
        # type: (Room) -> None
        remove_list = []
        for _, eid in enumerate(room.player_list):
            player = self.data_center.getEntityByID(keyType.Player, eid)
            if player.state == PLAYER_STATE_MAP.Deleted or player.state == PLAYER_STATE_MAP.Active \
                    or player.state == PLAYER_STATE_MAP.Deactive:
                remove_list.append(eid)
        for eid in remove_list:
            self.data_center.removeInGamePlayer(eid)

    def tick(self, tick_time=0.02):
        rooms = self.fetchData()
        removed_room = []  # type: List[int]
        for room in rooms:
            self.handleZombiePlayers(room)
            if len(room.player_list) <= 0:
                removed_room.append(room.id)
                continue
            if room.state == ROOM_STATE_MAP.Start:
                # sync room info
                self.broadCastActivateState(room)
            if room.state == ROOM_STATE_MAP.SyncingProgress:
                # sync room progress
                self.updateAndBroadCastSyncState(room)

            elif room.state == ROOM_STATE_MAP.CreatePlayer:
                self.createPlayer(room)
            if room.state == ROOM_STATE_MAP.InStory:
                self.updateInStory(room)

            if room.state == ROOM_STATE_MAP.CreateMonster:
                # wait monster create
                continue

            if room.isOnGoing:
                self.updateBuffs(room)
                for eid in room.player_list:
                    entity = self.data_center.getEntityByID(keyType.Player, eid)
                    entity.recover(tick_time=tick_time)
                    # is player enter hole

                for _, skillEntity in enumerate(self.data_center.getRoomEntity(keyType.Skill, room.id)):
                    skillEntity.tick(tick_time=tick_time)

                if room.stageInfo:
                    if room.delay_for_generate_monster > 0:
                        room.delay_for_generate_monster -= tick_time
                    else:
                        room.stageInfo.tick(tick_time=tick_time)

            if room.state == ROOM_STATE_MAP.Ongoing:
                if room.getAlivePlayerCount == 0:
                    logger.debug("game over")
                    room.state = ROOM_STATE_MAP.GameOver

                    # game over, bonus here

                if room.isStageEnd:
                    # if self.stage_time <= 0:
                    #     self.stage_time = 10.
                    logger.debug("stage end")
                    room.state = ROOM_STATE_MAP.Bonus
                    if room.stage_number != 6:
                        room.overSkillEnhancement()
                        for eid in room.player_list:
                            entity = self.data_center.getEntityByID(keyType.Player, eid)
                            # entity.state = PLAYER_STATE_MAP.Not_Ready
                            dic = {"Skill_info": entity.skill_dict.OverSkillEnhancement()}
                            self.rpc_queue.push_msg(0,
                                                    RpcMessage("PlayerSyncHandler/EndCurrentBattle", [entity.client_id], [],
                                                               dic))
                    else:
                        self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/PlayerWinTheGame", room.client_id_list, [],
                                                              {"Stage_id": room.stage_number + 1}))
                    room.clearRoomBesidePlayer(keep_item=True)
            if room.state == ROOM_STATE_MAP.Bonus:
                if room.isAllPlayersReady(except_host=False):
                    logger.info("all player ready, go to next stage")
                    room.startGame()
            if room.state == ROOM_STATE_MAP.GameOver:
                self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/GameOver", room.client_id_list, [], {}))
                removed_room.append(room.id)
        for rid in removed_room:
            self.data_center.removeRoom(rid)
            self.rpc_queue.push_msg(0, RpcMessage("updateRoom", [-1], [], {"Room_info": {"State": -1, "Room_id": rid}}))
