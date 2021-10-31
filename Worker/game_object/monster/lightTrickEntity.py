from common.rpc_queue_module import RpcMessage
from game_object.monster.chestEntity import ChestEntity
from game.utils import Vector3
from typing import Union
import logging
from common_server.timer import TimerManager

logger = logging.getLogger()


class LightTrickEntity(ChestEntity):
    blue_in_map = [
        [[6, 11], [12, 17]], [[-5, 0], [-11, -6]], [[-5, 0], [0, 5]]
    ]
    red_in_map = [
        [[11, 17], [12, 17]], [[1, 6], [12, 17]], [[-5, 0], [-17, -11]],
        [[-5, 0], [-6, 0]]
    ]

    def __init__(self, rid, monster_type, position=None, rotation=None):
        # type: (int, int, Vector3, Vector3) -> None
        super(LightTrickEntity, self).__init__(rid, position, rotation)
        self.radius = 0.8
        self.hp = 9999
        self.monsterType = monster_type
        self.triggered = False

    def reduceHp(self, dmg, dmg_type=0, eid=0, is_critical=False, is_bullet=False):
        # type: (int, int, int, bool, bool) -> None
        if self.monsterType == 200:
            LightManager.handleLightHit(self, "blue")
        if self.monsterType == 201:
            LightManager.handleLightHit(self, "red")

    def updateInMap(self):
        range_in_map = None
        if self.monsterType == 200:
            range_in_map = self.blue_in_map
        elif self.monsterType == 201:
            range_in_map = self.red_in_map
        if range_in_map is None:
            return
        for x, y in range_in_map:
            self.roomEntity.updateMap(x, y, value=3, move_away=self.triggered)


class LightManager(object):
    room_blue_lights = {}
    room_red_lights = {}
    room_lights = {"blue": room_blue_lights, "red": room_red_lights}
    max_time_delay = 8.0

    @classmethod
    def registerLight(cls, rid, light_type, light):
        # type: (int, str, LightTrickEntity) -> None
        if not cls.room_lights[light_type].__contains__(rid):
            cls.room_lights[light_type][rid] = dict(timer=None, lights={})

        cls.room_lights[light_type][rid]["lights"][light.entity_id] = light

    @classmethod
    def handleLightHit(cls, light, light_type):
        # type: (Union[LightTrickEntity], str) -> None
        if not cls.room_lights[light_type].__contains__(light.room_id):
            return
        if not cls.room_lights[light_type].__contains__(light.room_id):
            return
        if not light.triggered:
            for _light in cls.room_lights[light_type][light.room_id]["lights"].itervalues():
                _light.triggered = True
            light.updateInMap()
            room = light.data_center.getRoom(light.room_id)
            light.rpc_queue.push_msg(0, RpcMessage("BattleHandler/HandleLightHit", room.client_id_list, [], {
                "Is_red": True if light_type == "red" else False, "Triggered": True
            }))
        timer = cls.room_lights[light_type][light.room_id]["timer"]
        if timer is not None:
            TimerManager.cancel(timer)
            logger.debug("cancel timer %s" % timer)
        timer = lambda: cls.setLightsNotTriggered(light.room_id, light_type, light)
        cls.room_lights[light_type][light.room_id]["timer"] = TimerManager.addTimer(cls.max_time_delay, timer)
        logger.info("set %s lights triggered" % light_type)

    @classmethod
    def setLightsNotTriggered(cls, rid, light_type, light):
        # type: (int, str, Union[LightTrickEntity]) -> None
        for _light in cls.room_lights[light_type][rid]["lights"].itervalues():
            _light.triggered = False
        light.updateInMap()
        room = light.data_center.getRoom(rid)
        light.rpc_queue.push_msg(0, RpcMessage("BattleHandler/HandleLightHit", room.client_id_list, [], {
            "Is_red": True if light_type == "red" else False, "Triggered": False
        }))
        logger.info("set %s lights not triggered" % light_type)

    @classmethod
    def clearRoomLights(cls, rid):
        # type: (int) -> None
        if cls.room_lights["blue"][rid]["timer"] is not None:
            TimerManager.cancel(cls.room_lights["blue"][rid]["timer"])
        if cls.room_lights["red"][rid]["timer"] is not None:
            TimerManager.cancel(cls.room_lights["red"][rid]["timer"])

        cls.room_lights["red"].pop(rid)
        cls.room_lights["blue"].pop(rid)
