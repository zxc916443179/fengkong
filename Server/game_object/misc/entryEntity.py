import logging

from typing import TYPE_CHECKING

from common.rpc_queue_module import RpcMessage
from game.utils import Vector3
from game_object.entity import Entity
from setting import keyType


if TYPE_CHECKING:
    from ..room.roomEntity import Room
logger = logging.getLogger()


class EntryEntity(Entity):
    def __init__(self, rid, position, item_type):
        # type: (int, Vector3, int) -> None
        super(EntryEntity, self).__init__(rid)
        self.transform.position = position
        self.item_type = item_type

    def handleEntry(self, room):
        # type: (Room) -> None
        for player_eid in room.getRoomPlayer():
            player = self.data_center.getEntityByID(keyType.Player, player_eid)
            if player.state != keyType.PLAYER_STATE_MAP.In_Game:
                continue
            if Vector3.Distance(player.transform.position, self.transform.position) < 2.25:
                self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/PlayerGoToEnhanceMent", room.client_id_list, []
                                                      , {"Entity_id": player_eid}))
                player.state = keyType.PLAYER_STATE_MAP.Not_Ready
                logger.info("player %d enter doors" % player_eid)

    def tick(self, tick_time=0.02):
        room = self.data_center.getRoom(self.room_id)
        if room.state != keyType.ROOM_STATE_MAP.Bonus:
            return
        self.handleEntry(room)
