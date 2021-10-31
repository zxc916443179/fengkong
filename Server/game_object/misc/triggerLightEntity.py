import logging

from typing import TYPE_CHECKING

from common.rpc_queue_module import RpcMessage
from common_server.timer import TimerManager
from game.utils import Vector3
from game_object.entity import Entity
from setting import keyType

if TYPE_CHECKING:
    from ..room.roomEntity import Room
logger = logging.getLogger()


class TriggerLightEntity(Entity):
    def __init__(self, rid, position, item_type, trigger_id, ranges_in_map=None):
        # type: (int, Vector3, int, int, list) -> None
        super(TriggerLightEntity, self).__init__(rid)
        self.transform.position = position
        self.item_type = item_type
        self.trigger_id = trigger_id
        self.trigger_time = 1.5
        self.triggered = True
        self.ranges_in_map = ranges_in_map
        self.setTrigger(False)

    def handleEntry(self, room, tick_time=0.02):
        # type: (Room, float) -> None
        for player_eid in room.getRoomPlayer():
            player = self.data_center.getEntityByID(keyType.Player, player_eid)
            if Vector3.Distance(player.transform.position, self.transform.position) < 2.25:
                self.setTrigger(True)
                return
        if self.triggered:
            self.trigger_time = 1.5
            self.setTrigger(False)

    def setTrigger(self, triggered):
        # type: (bool) -> None
        room = self.data_center.getRoom(self.room_id)
        if self.triggered != triggered:
            self.triggered = triggered
            if triggered:
                room.stageInfo.entry_count[self.trigger_id] += 1
                if room.stageInfo.entry_timer[self.trigger_id] is None:
                    room.stageInfo.entry_timer[self.trigger_id] = \
                        TimerManager.addTimer(self.trigger_time,
                                              lambda: [
                                                  room.updateMap(range_in_map[0], range_in_map[1], move_away=self.triggered,
                                                                 value=1) for range_in_map in self.ranges_in_map])
            else:
                room.stageInfo.entry_count[self.trigger_id] -= 1
                if room.stageInfo.entry_count[self.trigger_id] == 0:
                    for range_in_map in self.ranges_in_map:
                        room.updateMap(range_in_map[0], range_in_map[1], move_away=self.triggered,
                                       value=1)
                    if room.stageInfo.entry_timer[self.trigger_id] is not None:
                        TimerManager.cancel(room.stageInfo.entry_timer[self.trigger_id])
                        logger.debug("entry timer canceled")
                        room.stageInfo.entry_timer[self.trigger_id] = None
            if self.triggered and room.stageInfo.entry_count[self.trigger_id] == 1 or \
                    not self.triggered and room.stageInfo.entry_count[self.trigger_id] == 0:
                '''
                change triggered state when triggered is true and count set to 1 
                or triggered is false and count set to 0
                '''
                self.rpc_queue.push_msg(0, RpcMessage("BattleHandler/HandleLightTriggered", room.client_id_list, [],
                                                      {"Triggered": not self.triggered, "Trigger_id": self.trigger_id}))
                logger.info("trigger blocks %s" % self.triggered)

    def tick(self, tick_time=0.02):
        room = self.data_center.getRoom(self.room_id)
        self.handleEntry(room, tick_time=tick_time)
