import logging

from common.rpc_queue_module import RpcMessage
from game.utils import Vector3
from entryEntity import EntryEntity
from typing import TYPE_CHECKING

from setting import keyType

if TYPE_CHECKING:
    from ..room.roomEntity import Room

logger = logging.getLogger()


class BossCageEntryEntity(EntryEntity):
    def __init__(self, rid, position, item_type):
        # type: (int, Vector3, int) -> None
        super(BossCageEntryEntity, self).__init__(rid, position, item_type)
        self.transform.position = position
        self.item_type = item_type
        self.locked = True
        self.lock_time = 10.0

    def handleEntry(self, room, tick_time=0.02):  # type: (Room, float) -> None
        if not self.locked:
            return
        for monster in self.data_center.getRoomEntity(keyType.Monster, room.id):
            if Vector3.Distance(self.transform.position, monster.transform.position) < 2.25:
                return
        for eid in room.getRoomPlayer():
            player = self.data_center.getEntityByID(keyType.Player, eid)
            if Vector3.Distance(player.transform.position, self.transform.position) < 2.25:
                if self.locked:
                    self.lock_time -= tick_time
                    logger.debug("entry %d time left %f" % (self.entity_id, self.lock_time))
                    if self.lock_time <= 0.1:
                        self.locked = False

                        self.rpc_queue.push_msg(0, RpcMessage("BattleHandler/HandleTakeItem", room.client_id_list, [],
                                                              {"Entity_id": self.entity_id}))
                    break

    @property
    def isLocked(self):
        return self.locked

    def tick(self, tick_time=0.02):
        room = self.data_center.getRoom(self.room_id)
        self.handleEntry(room, tick_time=tick_time)
