from threading import Thread

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
                        logger.error("", exc_info=True)
                else:
                    logger.error("invalid rpc call, permission denied: %s" % msg.method)
            else:
                logger.error("invalid rpc call, unreachable: %s" % msg.method)
        else:
            logger.error("not implement: %s" % msg.method)

    @req(["admin"])
    def testAdmin(self, msg):
        # type: (Message) -> None
        logger.debug("only admin allowed, client_id %d, permission: %s" % (msg.client_id, msg.permission))
        self.rpc_queue.push_msg(0, RpcMessage(msg.kwargs["callback"], [msg.client_id], [], {"data": "test return"}))

    @req()
    def heartBeat(self, msg):
        # type: (Message) -> None
        # self.rpc_queue.push_msg(0, RpcMessage("Test/test", [msg.client_id], [], {}))
        logger.debug("heart beat from client %d" % msg.client_id)
        pass

    # ***** Room Handler *****
    # ------------------------
    def createPlayer(self, player_info):
        # type: (dict) -> PlayerEntity
        player = self.data_center.getPlayerByClientID(player_info["Client_id"])
        if player is None:
            player = PlayerEntity(player_info["Entity_id"], -1, player_info["Client_id"])
            self.data_center.registerEntity(keyType.Player, player, entity_id=player_info["Entity_id"])

        logger.info("player created %s" % player.getPlayerBasicInfo())
        return player

    @req()
    def createRoom(self, msg):
        # type: (Message) -> None
        rooms = self.data_center.allRooms
        if len(rooms) >= ROOM_STATE_MAP.Max_Rooms:
            logger.debug("exceed max rooms limit, failed to create game")
            return
        player = self.data_center.getEntityByID(keyType.Player, msg.kwargs[keyType.Entity_id])
        if player is None:
            logger.debug("no player exists, creating")
            player = self.createPlayer(msg.kwargs["Player"])
        room = Room(host_eid=player.entity_id, host_name=player.name, title=msg.kwargs["Title"])
        room.joinPlayer(player)
        self.data_center.updateRoom(room)
        self.updateCurrentRoomInfo(room)
        self.rpc_queue.push_msg(0, RpcMessage("joinRoomCallback", [-1], [], {"Client_id": msg.kwargs["Client_id"]}))
        logger.debug(
            "create room by client: %d, room id is: %d, room title is: %s" % (player.client_id, room.id, room.title))

    @req()
    def joinRoom(self, msg):
        # type: (Message) -> None
        room = self.data_center.getRoom(msg.kwargs["Room_id"])
        if room is None:
            logger.debug("Room is not found %d" % msg.kwargs["Room_id"])
            raise RPCError(203)
        if room.state != ROOM_STATE_MAP.Start or len(room.player_list) >= ROOM_STATE_MAP.Max_Player_In_Game:
            logger.debug("cannot join room right now, room id %d" % room.id)
            raise RPCError(204)
        player = self.data_center.getEntityByID(keyType.Player, msg.kwargs[keyType.Entity_id])
        if player is None:
            logger.debug("player not found, creating")
            player = self.createPlayer(msg.kwargs["Player"])
        room.joinPlayer(player)
        self.updateCurrentRoomInfo(room)
        self.rpc_queue.push_msg(0, RpcMessage("joinRoomCallback", [-1], [], {"Client_id": msg.kwargs["Client_id"]}))
        logger.debug("player: %s join room %s" % (player.name, room.title))

    @req()
    def updateCurrentRoomInfo(self, room):
        # type: (Room) -> None
        # TODO: send to server
        ret = {
            "Room": {
                "Players": [player.getPlayerBasicInfo() for player in
                            self.data_center.getRoomEntity(keyType.Player, room.id)
                            if player.state != keyType.PLAYER_STATE_MAP.Active],
                "Room_id": room.id, "Title": room.title, "Host_id": room.host_eid, "Host_name": room.host_name,
                "State": room.state,
                "Player_id": [player.entity_id for player in
                              self.data_center.getRoomEntity(keyType.Player, room.id)
                              if player.state != keyType.PLAYER_STATE_MAP.Active]
            }
        }
        self.rpc_queue.push_msg(0, RpcMessage("updateRoom", [-1], [], {"Room_info": ret["Room"]}))
        self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/UpdateCurrentRoomInfo", room.client_id_list, [], ret))

    @req()
    def startGame(self, msg):
        # type: (Message) -> None
        player = self.data_center.getPlayerByClientID(msg.kwargs["Client_id"])
        room = self.data_center.getRoom(msg.kwargs["Room_id"])
        if not room.isHost(player.entity_id):
            return
        if room.isAllPlayersReady():
            room.enterStageWithNum(room.stage_number)
            self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/StartGame", room.client_id_list, [],
                                                  {"Stage_id": room.stage_number}))
            logger.info("stage id is %d" % room.stage_number)
            room.state = ROOM_STATE_MAP.SyncingProgress
            ret = {
                "Room_id": room.id, "Title": room.title, "Host_id": room.host_eid, "Host_name": room.host_name,
                "State": room.state
            }
            self.rpc_queue.push_msg(0, RpcMessage("updateRoom", [-1], [], {"Room_info": ret["Room"]}))
        else:
            logger.debug("not all player get ready")
            raise RPCError(202)

    @req()
    def setReady(self, msg):
        # type: (Message) -> None
        player = self.data_center.getPlayerByClientID(msg.kwargs["Client_id"])
        player.setReadyState()

    @req()
    def leaveRoom(self, msg):
        # type: (Message) -> None
        player = self.data_center.getPlayerByClientID(msg.kwargs["Client_id"])
        if player is None:
            logger.debug("player not found, %d" % msg.kwargs["Client_id"])
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
            self.rpc_queue.push_msg(0, RpcMessage("leaveRoomCallback", [-1], [], {"Client_id": msg.kwargs["Client_id"]}))

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
                self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/ChangeGameStage", [msg.kwargs["Client_id"]],
                                                      [], {"Stage_id": -3}))
            else:
                player.state = PLAYER_STATE_MAP.End_Story
                self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/ChangeGameStage", [msg.kwargs["Client_id"]],
                                                      [], {"Stage_id": -2}))
        else:
            self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/ChangeGameStage", [msg.kwargs["Client_id"]],
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
        entity = self.data_center.getPlayerByClientID(msg.kwargs["Client_id"])
        entity.updateProgress(msg.kwargs["Progress"])

    @req()
    def closeClient(self, msg):
        self.leaveRoom(msg)
        self.data_center.removePlayer(msg.kwargs["Client_id"])

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
