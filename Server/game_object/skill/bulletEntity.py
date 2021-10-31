import logging
from skillEntity import SkillEntity
from common.battle_queue_module import BattleMessage
from setting import keyType
from game.utils import Collide, Transform

logger = logging.getLogger()


class BulletEntity(SkillEntity):
    def __init__(self, rid):
        super(BulletEntity, self).__init__(rid)
        self.room_id = rid
        self.transform = None
        self.radius = 0
        self.maxTime = 0
        self.speed = 0
        self.lifeTime = 0

    def initSkillInfo(self, data):
        self.source = data[keyType.Source]
        self.radius = data[keyType.SkillRadius]
        self.transform = Transform(data[keyType.Position], data[keyType.Rotation])
        self.lifeTime = data["maxLifeTime"]
        self.speed = data[keyType.Speed]
        self.roomEntity = self.data_center.getRoom(self.room_id)

    def tick(self, tick_time=0.02):
        forward = self.transform.forward()
        forward.multiply(self.speed * tick_time)
        self.transform.translate(forward)
        self.lifeTime -= tick_time
        if self.lifeTime <= 0:
            self.roomEntity.removeSkill(self.entity_id)
            return
        for target in self.data_center.getRoomEntity(keyType.Player, self.room_id):
            r = self.radius + target.radius
            if Collide.trigger(self.transform.position, target.transform.position, r):
                self.battle_queue.push_msg(0, BattleMessage("playerDamaged", self.source, [target]))
                self.roomEntity.removeSkill(self.entity_id)
                return
