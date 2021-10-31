import logging

from common.common_library_module import Singleton
from common.rpc_queue_module import RpcQueue
from common_server.data_module import DataCenter
from game.nav_module import NavAgent
from game_object.room.roomEntity import Room
from setting import keyType
from setting.keyType import ROOM_STATE_MAP

logger = logging.getLogger()


@Singleton
class AIModule(object):
    def __init__(self):
        self.nav_agent = NavAgent()
        self.rpc_queue = RpcQueue()
        self.target = []
        self.data_center = DataCenter()

    def fetchData(self):
        # fetch data from Data
        return self.data_center.rooms

    def updateState(self, room, tick_time=0.02):
        # type: (Room, float) -> None
        # update each monster state
        if room.state == ROOM_STATE_MAP.CreateMonster:
            logger.debug("have enough players, waiting generating monster and chests")
            room.state = ROOM_STATE_MAP.Ongoing

        if room.isOnGoing:
            for eid in room.getRoomMonster():
                monster_entity = self.data_center.getEntityByID(keyType.Monster, eid)
                monster_entity.tick(tick_time)
            for eid in room.item_list:
                item = self.data_center.getEntityByID(keyType.Item, eid)
                item.tick(tick_time)

    def tick(self, tick_time=0.02):
        rooms = self.fetchData()
        for room in rooms.values():
            self.updateState(room, tick_time)
