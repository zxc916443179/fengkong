from skillEntity import SkillEntity
from setting import keyType
from common.rpc_queue_module import RpcMessage
from game.utils import Transform, Collide, Vector3
import logging

logger = logging.getLogger()


class FlashSkillEntity(SkillEntity):
    def __init__(self, rid):
        super(FlashSkillEntity, self).__init__(rid)
        self.entity_id = 0
        self.room_id = rid
        self.position = None
        self.distance = 0
        self.speed = 0
        self.transform = None
        self.source = None
        self.cd = 0

    def initSkillData(self, data):
        self.distance = self.data_center.skill_data["Teleporting_Distance"]
        self.speed = self.data_center.skill_data["Teleporting_Speed"]
        self.source = data[keyType.Source]
        self.transform = Transform(data[keyType.Position], self.source.walk_rotation)

        # check player hit the wall
        room = self.data_center.getRoom(self.room_id)
        maps = room.currentMap.mapList
        top = room.currentMap.top
        lef = room.currentMap.left
        cross_list = Collide.cross(self.transform.position.x - lef, self.transform.position.z + top,
                                   self.transform.rotation.y, maps, self.distance)
        if len(cross_list) > 0:
            position = Vector3(cross_list[0] + lef, 0, cross_list[1] - top)
            source_to_war_distance = Vector3.Distance(position, self.transform.position) ** 0.5
            if source_to_war_distance < self.distance:
                self.distance = source_to_war_distance

        # player translate
        forward = self.transform.forward()
        forward.multiply(self.distance)
        self.source.transform.translate(forward)
        self.cd = self.distance / self.speed
        room = self.data_center.getRoom(self.room_id)
        if self.source.setFlag(keyType.SITUATION_FLAG_MAP.PERFORM_LOCAL_MASK):
            self.source.writeAttr("flag", self.source.flag)
        ActionArgs = self.source.transform.position.getDict()
        ActionArgs["Speed"] = self.speed
        ActionArgs["Flag"] = self.source.flag
        self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/PerformPlayer", room.client_id_list, [],
                                              {"Entity_id": self.source.entity_id, "aid": 6, "ActionArgs": ActionArgs
                                               }))

    def tick(self, tick_time=0.02):
        self.cd -= tick_time
        if self.cd <= 0:
            if self.source.removeFlag(keyType.SITUATION_FLAG_MAP.PERFORM_LOCAL_MASK):
                self.source.writeAttr("flag", self.source.flag)
                room = self.data_center.getRoom(self.room_id)
                room.removeSkill(self.entity_id)
