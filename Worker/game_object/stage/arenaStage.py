from common.rpc_queue_module import RpcMessage
from stage import StageInfo

from game.utils import Vector3
from setting import keyType
from game_object.misc.entryEntity import EntryEntity
from random import randint
import logging
logger = logging.getLogger()


class ArenaStage(StageInfo):
    def __init__(self, rid, stage_info=None):
        super(ArenaStage, self).__init__(rid, stage_info)
        self.entries_list = [Vector3(-14, 0, 14), Vector3(-14, 0, -14)]
        self.survive_time = 6.0

    def tick(self, tick_time=0.02):
        super(ArenaStage, self).tick(tick_time)
        if self.survive_time >= 0:
            self.survive_time -= tick_time
        if self.state != keyType.STAGE_STATE_MAP.End and self.isLastBatch and len(self.room.monster_list) == 0:
            self.endStage()

        if self.survive_time <= 0 and self.state != keyType.STAGE_STATE_MAP.End:
            self.endStage()

    def endStage(self):
        entry_index = randint(0, 1)
        entity = EntryEntity(self.room_id, self.entries_list[entry_index], 1)
        self.data_center.registerEntity(keyType.Item, entity)
        self.room.addEntity(keyType.Item, entity.entity_id)
        self.rpc_queue.push_msg(0,
                                RpcMessage("BattleHandler/HandleArenaEntryShow", self.room.client_id_list, [],
                                           {"Entry_id": entry_index})
                                )
        self.state = keyType.STAGE_STATE_MAP.End
        logger.info("arena battle end, entry will show in position: %s" % self.entries_list[entry_index].getDict())
