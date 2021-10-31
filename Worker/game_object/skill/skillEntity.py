
from common.battle_queue_module import BattleMsgQueue
from common.rpc_queue_module import RpcQueue
from common_server.data_module import DataCenter
from game_object.entity import Entity
from setting import keyType


class SkillEntity(Entity):
    data_center = DataCenter()

    def __init__(self, rid):
        super(SkillEntity, self).__init__(rid)
        self.entity_id = 0
        self.room_id = rid
        self.source = None
        self.timer = None
        self.rpc_queue = RpcQueue()
        self.battle_queue = BattleMsgQueue()
        self.data_center = DataCenter()
        self.roomEntity = None

    def initSkillData(self, data):
        self.source = data[keyType.Source]

    def tick(self, tick_time=0.02):
        pass

    def cast(self, *args):
        pass

