import logging

from typing import TYPE_CHECKING

from common.rpc_queue_module import RpcMessage, RpcQueue
from common_server.data_module import DataCenter
from game.utils import Vector3
from game_object.buff import CreateBuff
from game_object.entity import Entity
from setting import keyType

if TYPE_CHECKING:
    from ..room.roomEntity import Room
logger = logging.getLogger()


class ItemEntity(Entity):
    def __init__(self, rid, position, item_type, weapon_info=None):
        # type: (int, Vector3, int, dict) -> None
        super(ItemEntity, self).__init__(rid)
        self.data_center = DataCenter()
        self.transform.position = position
        self.item_type = item_type
        self.rpc_queue = RpcQueue()
        self.weapon_info = weapon_info
        self.addHpValue = 0

    def handleTake(self, room):
        # type: (Room) -> None
        for player_eid in room.getRoomPlayer():
            player = self.data_center.getEntityByID(keyType.Player, player_eid)
            if player.isAlive and Vector3.Distance(player.transform.position, self.transform.position) < 1:
                logger.info("Item taken, id: %d" % self.entity_id)
                self.rpc_queue.push_msg(0, RpcMessage("BattleHandler/HandleTakeItem", room.client_id_list, [],
                                                      {"Entity_id": self.entity_id}))
                if self.item_type == keyType.ITEM_TYPE_MAP.Weapon and self.weapon_info is not None:
                    player.setWeapon(self.weapon_info["_wid"])
                    logger.info("player %d take new weapon %d" % (player_eid, self.weapon_info["_wid"]))
                elif self.item_type == keyType.ITEM_TYPE_MAP.Health:
                    player.addHp(100)
                    CreateBuff(self.room_id, -1, player_eid, keyType.Player, self.data_center.buff_info[1])
                room.removeEntity(keyType.Item, self.entity_id)

    def tick(self, tick_time=0.02):
        room = self.data_center.getRoom(self.room_id)
        if room.state == keyType.ROOM_STATE_MAP.Bonus:
            room.removeEntity(keyType.Item, self.entity_id)
            return
        self.handleTake(room)
