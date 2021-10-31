from threading import Thread

from common.battle_queue_module import BattleMsgQueue, BattleMessage
from common_server.data_module import DataCenter
from common.message_queue_module import MsgQueue, Message
from common.rpc_queue_module import RpcQueue, RpcMessage
from game.AI_module import AIModule
from gameEntity import RPCError

from game_object.room.roomEntity import Room
from game_object.player.playerEntity import PlayerEntity

from game.utils import Vector3, Random
from setting import keyType
from setting.keyType import ROOM_STATE_MAP, PLAYER_STATE_MAP
import logging

logger = logging.getLogger()


def req(allow_permissions=None):
    def decorator(func):
        func.__exposed__ = True
        func.__allow_permissions__ = allow_permissions
        return func

    return decorator


class MsgHandler(Thread):
    def __init__(self):
        super(MsgHandler, self).__init__()
        self.state = 0
        self.msg_queue = MsgQueue()
        self.rpc_queue = RpcQueue()
        self.battle_queue = BattleMsgQueue()
        self.ai_module = AIModule()
        self.data_center = DataCenter()
        self.playerInitData = [{
            "Position": {"x": 0., "y": 0., "z": 1.}, "Rotation": {"x": 0., "y": 0., "z": 0.}, "Name": "test1",
            "Money": 0, "Speed": 6.
        }, {
            "Position": {"x": 0., "y": 0., "z": -10.}, "Rotation": {"x": 0., "y": 0., "z": 0.}, "Name": "Test2",
            "Money": 0, "Speed": 6.
        }]

    def run(self):
        while self.state == 0:
            msg = self.msg_queue.pop_msg()
            if msg is not None:
                self.handleMessage(msg)

    def handleMessage(self, msg):
        # type: (Message) -> None
        func = getattr(self, msg.method, None)
        if func is not None:
            if getattr(func, "__exposed__", False):
                allow_permissions = getattr(func, "__allow_permissions__", None)
                if allow_permissions is None or msg.permission in allow_permissions:
                    try:
                        func(msg)
                    except Exception as e:
                        if type(e) is RPCError:
                            ret = {"code": e.code, "msg": e.description}
                        else:
                            ret = {"code": 100}
                        self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/Exception", [msg.client_id], [], ret))
                        logger.error("%s" % e.message, exc_info=True)
                else:
                    logger.error("invalid rpc call, permission denied: %s" % msg.method)
            else:
                logger.error("invalid rpc call, unreachable: %s" % msg.method)
        else:
            logger.error("not implement: %s" % msg.method)

    # ***** GM Handler *****
    # ------------------------
    @req(["admin"])
    def testAdmin(self, msg):
        # type: (Message) -> None
        logger.debug("only admin allowed, client_id %d, permission: %s" % (msg.client_id, msg.permission))
        self.rpc_queue.push_msg(0, RpcMessage(msg.kwargs["callback"], [msg.client_id], [], {"data": "test return"}))

    @req(["admin"])
    def setDamageRate(self, msg):
        # type: (Message) -> None
        players = self.data_center.getRoomEntity(keyType.Player, msg.kwargs["Room_id"])
        for player in players:
            self.data_center.setPlayerAttribute(player.entity_id, {"dmg_rate": msg.kwargs["dmg_rate"]})

    @req(["admin"])
    def clearAllMonster(self, msg):
        # type: (Message) -> None
        room = self.data_center.getRoom(msg.kwargs["Room_id"])
        room.clearRoomBesidePlayer()
        pass

    @req(["admin"])
    def getCurrentDoor(self, msg):
        # type: (Message) -> None
        pos = self.data_center.getDoorPosition(msg.kwargs["Room_id"])
        self.rpc_queue.push_msg(0, RpcMessage(msg.kwargs["callback"], [msg.client_id], [], {"data": pos}))
        pass

    @req(["admin"])
    def createMonster(self, msg):
        # type: (Message) -> None
        self.data_center.createMonster(msg.kwargs["Room_id"], msg.kwargs["Monster_type"],
                                       Vector3(from_dict=msg.kwargs["Position"]))
        pass

    @req(["admin"])
    def getPlayerPosition(self, msg):
        # type: (Message) -> None
        position = self.data_center.getEntityByID(keyType.Player, msg.kwargs["Entity_id"]).transform.position

        self.rpc_queue.push_msg(0, RpcMessage(msg.kwargs["callback"], [msg.client_id], [],
                                              {"data": (position.x, position.y, position.z)}))
        pass

    @req(["admin"])
    def setPlayerPosition(self, msg):
        # type: (Message) -> None
        player = self.data_center.getEntityByID(keyType.Player, msg.kwargs["Entity_id"])
        player.setPlayerPosition(Vector3(from_dict=msg.kwargs["Position"]))
        pass

    @req(["admin"])
    def setPlayerAttr(self, msg):
        # type: (Message) -> None
        entity_id = msg.kwargs["Entity_id"]
        if msg.kwargs.__contains__("callback"):
            msg.kwargs.pop("callback")
        msg.kwargs.pop("Entity_id")
        self.data_center.setPlayerAttribute(entity_id, msg.kwargs)
        pass

    @req(["admin"])
    def getPlayerAttr(self, msg):
        # type: (Message) -> None
        value = self.data_center.getPlayerAttribute(msg.kwargs["Entity_id"], msg.kwargs["Attr_name"])
        self.rpc_queue.push_msg(0, RpcMessage(msg.kwargs["callback"], [msg.client_id], [],
                                              {"data": value}))

    @req(["admin"])
    def getPlayerWeaponType(self, msg):
        # type: (Message) -> None
        value = self.data_center.getEntityByID(keyType.Player, msg.kwargs["Entity_id"]).weapon.weapon_type
        self.rpc_queue.push_msg(0, RpcMessage(msg.kwargs["callback"], [msg.client_id], [],
                                              {"data": value}))

    @req(["admin"])
    def setPlayerWeaponType(self, msg):
        # type: (Message) -> None
        self.data_center.getEntityByID(keyType.Player, msg.kwargs["Entity_id"]).setWeapon(msg.kwargs["Weapon_type"])

    @req(["admin"])
    def getPlayerTalents(self, msg):
        # type: (Message) -> None
        value = self.data_center.getPlayerTalents(msg.kwargs["Entity_id"])
        self.rpc_queue.push_msg(0, RpcMessage(msg.kwargs["callback"], [msg.client_id], [],
                                              {"data": value}))
        pass

    @req(["admin"])
    def clearPlayerTalents(self, msg):
        # type: (Message) -> None
        self.data_center.clearPlayerTalents(msg.kwargs["Entity_id"])
        pass

    @req(["admin"])
    def addPlayerTalent(self, msg):
        # type: (Message) -> None
        self.data_center.addPlayerTalent(msg.kwargs["Entity_id"], msg.kwargs["Talent_id"])
        pass

    @req(["admin"])
    def getPlayerBuffs(self, msg):
        # type: (Message) -> None
        value = self.data_center.getPlayerBuffs(msg.kwargs["Entity_id"])
        self.rpc_queue.push_msg(0, RpcMessage(msg.kwargs["callback"], [msg.client_id], [],
                                              {"data": value}))
        pass

    @req(["admin"])
    def clearPlayerBuffs(self, msg):
        # type: (Message) -> None
        self.data_center.clearPlayerBuffs(msg.kwargs["Entity_id"])
        pass

    @req(["admin"])
    def addPlayerBuff(self, msg):
        # type: (Message) -> None
        self.battle_queue.push_msg(0, BattleMessage("createBuff", -1, msg.kwargs["Entity_id"],
                                                    room_id=msg.kwargs["Room_id"],
                                                    target_entity_type=msg.kwargs["Entity_type"],
                                                    buff_id=msg.kwargs["Buff_id"]))
        pass

    @req(["admin"])
    def getSkillAttr(self, msg):
        # type: (Message) -> None
        ret = self.data_center.getSkillAttr()

        self.rpc_queue.push_msg(0, RpcMessage(msg.kwargs["callback"], [msg.client_id], [],
                                              {"data": ret}))
        pass

    @req(["admin"])
    def setSkillAttr(self, msg):
        # type: (Message) -> None
        self.data_center.setSkillAttr(msg.kwargs["Teleporting_Distance"], msg.kwargs["Teleporting_Speed"],
                                      msg.kwargs["Help_Cd"], msg.kwargs["Help_Distance"])
        pass

    @req(["admin"])
    def getTalentAttr(self, msg):
        # type: (Message) -> None
        ret = self.data_center.getTalentAttr(msg.kwargs["Talent_id"])

        self.rpc_queue.push_msg(0, RpcMessage(msg.kwargs["callback"], [msg.client_id], [],
                                              {"data": ret}))
        pass

    @req(["admin"])
    def setTalentAttr(self, msg):
        # type: (Message) -> None
        self.data_center.set_talent_attr(msg.kwargs["Talent_id"], msg.kwargs["Talent_type"],
                                         msg.kwargs["Buff_id"], msg.kwargs["Values"])
        pass

    @req(["admin"])
    def getBuffAttr(self, msg):
        # type: (Message) -> None
        ret = self.data_center.getBuffAttr(msg.kwargs["Buff_id"])

        self.rpc_queue.push_msg(0, RpcMessage(msg.kwargs["callback"], [msg.client_id], [],
                                              {"data": ret}))
        pass

    @req(["admin"])
    def setBuffAttr(self, msg):
        # type: (Message) -> None
        self.data_center.setBuffAttr(msg.kwargs["Buff_id"], msg.kwargs["Buff_time"], msg.kwargs["Effects"],
                                     msg.kwargs["Buff_tick"])
        pass

    @req(["admin"])
    def getWeaponAttr(self, msg):
        # type: (Message) -> None
        ret = self.data_center.getWeaponAttr(msg.kwargs["Weapon_type"])

        self.rpc_queue.push_msg(0, RpcMessage(msg.kwargs["callback"], [msg.client_id], [],
                                              {"data": ret}))
        pass

    @req(["admin"])
    def setWeaponAttr(self, msg):
        # type: (Message) -> None
        self.data_center.setWeaponAttr(msg.kwargs["_wid"], msg.kwargs)
        pass

    @req(["admin"])
    def getMonsterAttr(self, msg):
        # type: (Message) -> None
        ret = self.data_center.getMonsterInfo(msg.kwargs["Monster_type"])

        self.rpc_queue.push_msg(0, RpcMessage(msg.kwargs["callback"], [msg.client_id], [],
                                              {"data": ret}))
        pass

    @req(["admin"])
    def setMonsterAttr(self, msg):
        # type: (Message) -> None
        monster_type = msg.kwargs["Monster_type"]
        msg.kwargs.pop("Entity_id")
        if msg.kwargs.__contains__("callback"):
            msg.kwargs.pop("callback")
        self.data_center.setMonsterInfo(monster_type, msg.kwargs)

    @req(["admin"])
    def fetchAllRooms(self, msg):
        # type: (Message) -> None
        rooms = self.data_center.allRooms
        ret = [{
            "Room_id": room.id, "Player_id": room.player_list
        } for room in rooms]
        self.rpc_queue.push_msg(0, RpcMessage(msg.kwargs["callback"], [msg.client_id], [], {"data": ret}))

    @req()
    def heartBeat(self, msg):
        # type: (Message) -> None
        # self.rpc_queue.push_msg(0, RpcMessage("Test/test", [msg.client_id], [], {}))
        logger.debug("heart beat from client %d" % msg.client_id)
        pass

    # ***** Room Handler *****
    # ------------------------
    @req()
    def login(self, msg):
        # type: (Message) -> None
        logger.debug("login from client : " + str(msg.client_id))
        player = self.data_center.getPlayerByClientID(msg.client_id)
        if player is None:
            player = PlayerEntity(0, -1, msg.client_id)
            self.data_center.registerEntity(keyType.Player, player)
        logger.info(player.getPlayerBasicInfo())
        self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/CreatePlayerBeforeGame", [msg.client_id], [],
                                              player.getPlayerBasicInfo()))

    @req()
    def fetchRooms(self, msg):
        # type: (Message) -> None
        logger.debug("fetch rooms")
        ret = []
        rooms = self.data_center.allRooms
        if len(rooms) < ROOM_STATE_MAP.Max_Fetch_Rooms:
            ret = [{
                "Room_id": room.id, "Title": room.title, "Count": len(room.player_list),
                "Max": ROOM_STATE_MAP.Max_Player_In_Game, "Host_id": room.host_eid, "Host_name": room.host_name,
                "Player_id": room.player_list
            } for room in rooms if room.state == ROOM_STATE_MAP.Start]
        else:
            rand_indices = Random.randint(0, len(rooms), size=ROOM_STATE_MAP.Max_Fetch_Rooms)
            for i, room in enumerate(rooms):
                if room.state != ROOM_STATE_MAP.Start:
                    continue
                if i in rand_indices:
                    ret.append({
                        "Room_id": room.id, "Title": room.title, "Count": len(room.player_list),
                        "Max": ROOM_STATE_MAP.Max_Player_In_Game, "Host_id": room.host_eid, "Host_name": room.host_name,
                        "Player_id": room.player_list
                    })
        logger.debug(ret)
        self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/FetchRooms", [msg.client_id], [], {"Rooms": ret}))

    @req()
    def createRoom(self, msg):
        # type: (Message) -> None
        rooms = self.data_center.allRooms
        if len(rooms) >= ROOM_STATE_MAP.Max_Rooms:
            logger.debug("exceed max rooms limit, failed to create game")
            return
        player = self.data_center.getEntityByID(keyType.Player, msg.kwargs[keyType.Entity_id])
        room = Room(host_eid=player.entity_id, host_name=player.name, title=msg.kwargs["Title"])
        room.joinPlayer(player)
        self.data_center.updateRoom(room)
        self.updateCurrentRoomInfo(room)
        logger.debug(
            "create room by client: %d, room id is: %d, room title is: %s" % (msg.client_id, room.id, room.title))

    @req()
    def joinRoom(self, msg):
        # type: (Message) -> None
        room = self.data_center.getRoom(msg.kwargs["Room_id"])
        if room is None:
            logger.debug("Room is not found %d" % msg.kwargs["Room_id"])
            raise RPCError(203)
        if len(room.player_list) >= ROOM_STATE_MAP.Max_Player_In_Game:
            logger.debug("cannot join room right now, room id %d" % room.id)
            raise RPCError(204)
        if room.state != ROOM_STATE_MAP.Start:
            logger.debug("cannot join room right now, room id %d" % room.id)
            raise RPCError(205)

        player = self.data_center.getEntityByID(keyType.Player, msg.kwargs[keyType.Entity_id])
        if player is None:
            logger.debug("player not found, %d" % msg.kwargs[keyType.Entity_id])
            raise RPCError(100)

        room.joinPlayer(player)
        self.updateCurrentRoomInfo(room)
        logger.debug("player: %s join room %s" % (player.name, room.title))

    @req()
    def updateCurrentRoomInfo(self, room):
        # type: (Room) -> None
        ret = {
            "Room": {
                "Players": [player.getPlayerBasicInfo() for player in
                            self.data_center.getRoomEntity(keyType.Player, room.id)
                            if player.state != keyType.PLAYER_STATE_MAP.Active],
                "Room_id": room.id, "Title": room.title, "Host_id": room.host_eid, "Host_name": room.host_name
            }
        }
        self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/UpdateCurrentRoomInfo", room.client_id_list, [], ret))

    @req()
    def startGame(self, msg):
        # type: (Message) -> None
        player = self.data_center.getPlayerByClientID(msg.client_id)
        room = self.data_center.getRoom(msg.kwargs["Room_id"])
        if not room.isHost(player.entity_id):
            return
        if room.isAllPlayersReady():
            room.enterStageWithNum(room.stage_number)
            self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/StartGame", room.client_id_list, [],
                                                  {"Stage_id": room.stage_number}))
            logger.info("stage id is %d" % room.stage_number)
            room.state = ROOM_STATE_MAP.SyncingProgress
        else:
            logger.debug("not all player get ready")
            raise RPCError(202)

    @req()
    def setReady(self, msg):
        # type: (Message) -> None
        player = self.data_center.getPlayerByClientID(msg.client_id)
        player.setReadyState()

    @req()
    def leaveRoom(self, msg):
        # type: (Message) -> None
        player = self.data_center.getPlayerByClientID(msg.client_id)
        if player is None:
            logger.debug("player not found, %d" % msg.client_id)
            return
        if player.room_id != -1 or player.room_id is not None:
            room = self.data_center.getRoom(player.room_id)
            if room is None:
                logger.debug("Room is not found %d" % player.room_id)
                raise RPCError(203)
            player.state = PLAYER_STATE_MAP.Active
            logger.debug("set player state to Active, id: %d, state: %d" % (player.entity_id, player.state))
            room.updateNextHost(player.entity_id)
            self.updateCurrentRoomInfo(room)
            logger.debug("player %d leave game" % player.entity_id)

    @req()
    def finishStory(self, msg):
        # type: (Message) -> None
        room = self.data_center.getRoom(msg.kwargs["Room_id"])
        if room is None:
            logger.debug("Room is not found %d" % msg.kwargs["Room_id"])
            return
        player = self.data_center.getEntityByID(keyType.Player, msg.kwargs[keyType.Entity_id])
        if player is None:
            logger.debug("player not found, %d" % msg.kwargs[keyType.Entity_id])
            return
        if room.current_stage == 3:  # play animation
            room.delay_for_generate_monster = 2.0
            if player.state != PLAYER_STATE_MAP.In_Animation:
                player.state = PLAYER_STATE_MAP.In_Animation
                self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/ChangeGameStage", [msg.client_id],
                                                      [], {"Stage_id": -3}))
            else:
                player.state = PLAYER_STATE_MAP.End_Story
                self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/ChangeGameStage", [msg.client_id],
                                                      [], {"Stage_id": -2}))
        else:
            self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/ChangeGameStage", [msg.client_id],
                                                  [], {"Stage_id": -2}))
            player.state = PLAYER_STATE_MAP.End_Story
            logger.debug("player %d has finished story" % player.entity_id)

    @req()
    def updateSituation(self, msg):
        # type: (Message) -> None        
        room = self.data_center.getRoom(msg.kwargs["Room_id"])
        # print room.id
        if not room.isOnGoing:
            return
        # player = room.player_dict[msg.kwargs[keyType.Entity_id]]
        entity = self.data_center.getEntityByID(keyType.Player, msg.kwargs[keyType.Entity_id])
        # entity.updateWalkRotation(Vector3(dict=msg.kwargs["Position"]))
        if entity.flag & 0xFFFF0000 <= 0:
            entity.updateWalkRotation(Vector3(from_dict=msg.kwargs["Position"]))
            entity.updateTransform(Vector3(from_dict=msg.kwargs["Position"]), Vector3(from_dict=msg.kwargs["Rotation"]))
            entity.updateWeaponTransform(Vector3(from_dict=msg.kwargs["Weapon_position"]))

    @req()
    def syncProgress(self, msg):
        # type: (Message) -> None
        room = self.data_center.getRoom(msg.kwargs["Room_id"])
        print "sync progress, ", msg.kwargs["Progress"]
        if not room.state == ROOM_STATE_MAP.SyncingProgress:
            return
        entity = self.data_center.getPlayerByClientID(msg.client_id)
        entity.updateProgress(msg.kwargs["Progress"])

    @req()
    def closeClient(self, msg):
        self.leaveRoom(msg)
        self.data_center.removePlayer(msg.client_id)

    @req()
    def skillBegin(self, msg):
        player_eid = msg.kwargs["Entity_id"]
        playerEntity = self.data_center.getEntityByID(keyType.Player, player_eid)
        if playerEntity.flag & 0xFFFF0000 <= 0:
            playerEntity.attackHandle(msg.kwargs["skillType"])

    @req()
    def skillOver(self, msg):
        player_eid = msg.kwargs["Entity_id"]
        playerEntity = self.data_center.getEntityByID(keyType.Player, player_eid)
        room = self.data_center.getRoom(playerEntity.room_id)
        if playerEntity.flag & 0xFFFF0000 <= 0:
            aid = playerEntity.skillOver(msg.kwargs["skillType"])
            self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/PerformPlayer", room.client_id_list, [],
                                                  {"aid": aid, "Entity_id": player_eid}))

    @req()
    def addSkill(self, msg):
        player_eid = msg.kwargs["Entity_id"]
        playerEntity = self.data_center.getEntityByID(keyType.Player, player_eid)
        playerEntity.state = PLAYER_STATE_MAP.Ready
        if msg.kwargs["Skill_id"] != -1:
            playerEntity.addSkill(msg.kwargs["Skill_id"])
            playerEntity.search(msg.kwargs["Skill_id"])
        logger.info("player %d select skill %d" % (player_eid, msg.kwargs["Skill_id"]))
