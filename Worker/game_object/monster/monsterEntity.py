import math
from random import randint, uniform

from typing import TYPE_CHECKING, Tuple

from common import conf
from common.rpc_queue_module import RpcQueue, RpcMessage
from common_server.data_module import DataCenter
from common_server.timer import TimerManager
from game.nav_module import NavAgent
from game.utils import Vector3, Transform, Collide
from game_object.entity import Entity
from game_object.misc.itemEntity import ItemEntity
from setting import keyType

if TYPE_CHECKING:
    from game_object.room.roomEntity import Room

import logging

logger = logging.getLogger()


class MonsterEntity(Entity):
    def __init__(self, rid):
        super(MonsterEntity, self).__init__(rid)
        self.rpc_queue = RpcQueue()
        self.entity_id = -1
        self.room_id = rid
        self.dmg_target = [0, 0, 0, 0]  # get different damaged,0 normal,1 burn,2 lighting,3 water
        self.dmg_rate = 0
        self.hp = 0
        self.state = -1
        self.shield = 0
        self.speed = 0
        self.skillCD = 0
        self.cd = [0.0, 0.0, 0.0]  # 3 element CD
        self.hate_time = 10
        self.target = None
        self.patrol_list = []
        self.patrol_index = 0
        self.monsterType = 0
        self.knock_hp_rate = 0
        self.knock_gun_rate = 0
        self.buff = []
        self.element = {
            "water": 0,
            "light": 0,
            "burn": 0
        }
        self.roomEntity = self.data_center.getRoom(self.room_id)
        self.mapTop = self.roomEntity.currentMap.top
        self.mapLeft = self.roomEntity.currentMap.left
        self.mapList = self.roomEntity.currentMap.mapList
        self.flag = keyType.SITUATION_FLAG_MAP.NORMAL

        self.timer = None
        self.radius = 0

        self.data_center = DataCenter()
        self.monsterInfo = None
        self.nav_agent = NavAgent()
        self.beHitHidePos = None
        self.beHitCountForBullet = 0

        self.sync_rpc_url = "MonsterSyncHandler/UpdateMonsterAttribute"
        self.cold_data_list = ["hp", "shield", "entity_id", "buff"]

        self.start_idle_time = keyType.MONSTER_STATE_MAP.Start_Idle_Time

    @property
    def isAlive(self):
        # type: () -> bool
        return self.state != keyType.MONSTER_STATE_MAP.Die

    def initMonsterData(self, data):
        self.transform.position = Vector3(data[keyType.Position]["x"], data[keyType.Position]["y"],
                                          data[keyType.Position]["z"])
        self.transform.rotation = Vector3(data[keyType.Rotation]["x"], data[keyType.Rotation]["y"],
                                          data[keyType.Rotation]["z"])
        self.patrol_list = [Vector3(from_dict=data[keyType.Position]), Vector3(10, 0, -10)]

    def initMonsterInfo(self, info):
        # type: (dict) -> None
        self.knock_gun_rate = info["Guns_Knock_Rating"]
        self.knock_hp_rate = info["HP_Knock_Rating"]
        self.radius = info[keyType.Capsule_Radius]
        self.monsterType = info[keyType.MonsterType]
        self.hp = info[keyType.Hp]
        self.state = keyType.MONSTER_STATE_MAP.Idle
        self.timer = TimerManager.addRepeatTimer(conf.MODULE_MONSTER_TICK, self.recoverSkillCD)

    def getMonsterPositionData(self):
        return {
            keyType.Entity_id: self.entity_id,
            keyType.Position: self.transform.position.getDict(),
            keyType.Rotation: self.transform.rotation.getDict(),
        }

    def getMonsterInitData(self):
        return {
            keyType.Entity_id: self.entity_id,
            keyType.MonsterType: self.monsterType,
            keyType.Hp: self.hp,
            keyType.Shield: self.shield,
            keyType.State: self.state,
            keyType.Position: self.transform.position.getDict(),
            keyType.Rotation: self.transform.rotation.getDict(),
        }

    def getNearestTarget(self, Distance):
        nearest_player = None
        distance = Distance
        for eid in self.roomEntity.getRoomPlayer():
            player_entity = self.data_center.getEntityByID(keyType.Player, eid)
            if player_entity.hp <= 0:
                continue
            d = Vector3.Distance(player_entity.transform.position, self.transform.position)
            dis = math.sqrt(d)
            if dis < distance:
                distance = dis
                nearest_player = player_entity
        return nearest_player

    def getMostHateTarget(self):
        target_hate = 0
        target = None
        patrol_range = self.monsterInfo[keyType.Patrol_Range] ** 2
        for eid in self.roomEntity.getRoomPlayer():
            hate = 0
            player_entity = self.data_center.getEntityByID(keyType.Player, eid)
            if not player_entity.isAlive:
                continue
            d = Vector3.Distance(player_entity.transform.position, self.transform.position)
            if d < patrol_range:
                if d == 0:
                    hate += 100
                else:
                    hate += 1 / d
            if hate > target_hate:
                target_hate = hate
                target = player_entity
            # TODO: more hate
        if target_hate > 0:
            self.setTarget(target)

    def setTarget(self, target):
        # type: (Entity or None) -> None
        if target is not None:
            if self.target is None or self.target.entity_id != target.entity_id:
                self.target = target
                logger.debug("%d get new target, id: %d" % (target.entity_id, self.entity_id))
            self.hate_time = 10.
            self.state = keyType.MONSTER_STATE_MAP.Follow
        else:
            if self.target is not None:
                logger.debug("%d lose target" % self.entity_id)
                self.target = None
            self.state = keyType.MONSTER_STATE_MAP.Patrol

    def tick(self, tick_time=0.02):
        for i in range(len(self.cd)):
            if self.cd[i] > 0:
                self.cd[i] = max(0., self.cd[i] - tick_time)

        if self.flag & keyType.SITUATION_FLAG_MAP.DIZZY:
            self.state = keyType.MONSTER_STATE_MAP.Idle
            return
        if self.start_idle_time >= 0.1:
            self.start_idle_time -= conf.MODULE_MONSTER_TICK
            if self.start_idle_time < 0.1:
                self.state = keyType.MONSTER_STATE_MAP.Patrol
            return
        if self.hate_time <= 0 or self.target is None:
            self.getMostHateTarget()
        if self.target is not None:
            if not self.target.isAlive:
                self.setTarget(None)
                return
            self.hate_time -= conf.MODULE_MONSTER_TICK
            dis = Vector3.Distance(self.target.transform.position, self.transform.position)
            if dis < self.monsterInfo[keyType.Attack_Range] ** 2:
                self.state = keyType.MONSTER_STATE_MAP.Attack
            elif dis < self.monsterInfo[keyType.Patrol_Range] ** 2:
                self.state = keyType.MONSTER_STATE_MAP.Follow
            else:
                self.setTarget(None)
        self.handleFallDown()

    def handleFallDown(self):
        if self.isAlive:
            if self.roomEntity.currentMap.isCellEquals(self.transform.position.x, self.transform.position.z, 3):
                logger.info("monster %d fall down" % self.entity_id)
                self.state = keyType.MONSTER_STATE_MAP.Die

    def updateRotation(self, oldVector3, newVector3):
        # type: (Vector3, Vector3) -> None
        if oldVector3.x == newVector3.x and oldVector3.z == newVector3.z:
            return
        x = newVector3.x - oldVector3.x
        z = newVector3.z - oldVector3.z
        cos_angle = z / math.sqrt(z * z + x * x)
        angle = math.acos(cos_angle) / math.pi * 180
        if x < 0:
            angle = -angle
        self.transform.rotation.y = round(angle, 3)

    def sendStateToClient(self, state):
        self.rpc_queue.push_msg(0, RpcMessage(
            "MonsterSyncHandler/SyncMonsterState", self.roomEntity.client_id_list, [],
            {"monsters": [{keyType.State: state, keyType.Entity_id: self.entity_id}]}
        ))

    def reduceHp(self, dmg, dmg_type=0, eid=-1, is_critical=False, is_bullet=False):
        # type: (int, int, int, bool, bool) -> None
        if dmg_type in [15, 17, 20]:
            dmg_type -= 1
        dmg *= 1 + self.dmg_rate
        self.hp = max(0, self.hp - dmg)
        self.sendHpToClient(dmg_type, is_critical, eid)
        if self.hp <= 0:
            self.state = keyType.MONSTER_STATE_MAP.Die
            self.updateState()

    def sendHpToClient(self, dmg_type, is_critical, eid):
        self.rpc_queue.push_msg(0, RpcMessage("BattleHandler/HandleMonsterDamaged", self.roomEntity.client_id_list, [],
                                              {"Entity_id": self.entity_id, "Source": eid, "Hp": self.hp, "Type": dmg_type,
                                               "Is_critical": is_critical}))

    def dieHandle(self):
        self.sendStateToClient(keyType.MONSTER_STATE_MAP.Die)
        self.tryDropItem(self.roomEntity)
        self.roomEntity.removeEntity(keyType.Monster, self.entity_id)
        self.roomEntity.updateMap(self.transform.position.x, self.transform.position.z, move_away=True)

    def updateState(self):
        pass

    def tryDropItem(self, room):
        # type: (Room) -> None
        drop_item, item_type = self.dropItem()
        if drop_item != keyType.ITEM_TYPE_MAP.Nothing:
            logger.debug("drop item!")
            self.transform.position.y = 0.0
            logger.debug({"Item_type": drop_item, "Position": self.transform.position})
            item = ItemEntity(self.room_id, self.transform.position, drop_item,
                              None if drop_item == keyType.ITEM_TYPE_MAP.Health else self.data_center.weapon_info[
                                  item_type]
                              )
            self.data_center.registerEntity(keyType.Item, item)
            room.addEntity(keyType.Item, item.entity_id)
            self.rpc_queue.push_msg(0, RpcMessage(
                "BattleHandler/GenerateDropItem", room.client_id_list, [],
                {"Item_type": item_type, "Position": self.transform.position.getDict(), "Entity_id": item.entity_id,
                 "Item": "Health" if drop_item == keyType.ITEM_TYPE_MAP.Health else "Gun"
                 }
            ))

    def dropItem(self):
        # type: () -> Tuple[int, int or None]
        rate = randint(0, 10) / 10.
        if rate < self.knock_hp_rate:
            return keyType.ITEM_TYPE_MAP.Health, randint(0, 1)
        elif rate < self.knock_hp_rate + self.knock_gun_rate:
            keys = self.data_center.weapon_info.keys()
            key_index = randint(1, len(keys) - 1)
            if key_index == 4:
                # don't use sniper
                key_index = 5
            return keyType.ITEM_TYPE_MAP.Weapon, keys[key_index]
        else:
            logger.info("drop nothing")
            return keyType.ITEM_TYPE_MAP.Nothing, None

    def recoverSkillCD(self):
        pass

    def move(self, current, target):
        self.roomEntity.updateMap(self.transform.position.x, self.transform.position.z, move_away=True)
        self.updateRotation(self.transform.position, target)
        diff = Vector3.Lerp(current, target, conf.MODULE_MONSTER_TICK * self.speed)
        diff.subtract(current)
        self.transform.position.add(diff)
        self.roomEntity.updateMap(self.transform.position.x, self.transform.position.z)

    def repelMonster(self, angle, dis):
        # type: (Vector3, float) -> None
        tran = Transform(self.transform.position, Vector3(0, angle, 0))
        cross_list = Collide.cross(self.transform.position.x - self.mapLeft, self.transform.position.z + self.mapTop,
                                   angle, self.mapList, dis)
        if len(cross_list) > 0:
            position = Vector3(cross_list[0] + self.mapLeft, 0, cross_list[1] - self.mapTop)
            source_to_war_distance = Vector3.Distance(position, self.transform.position) ** 0.5
            if source_to_war_distance < dis:
                dis = source_to_war_distance
        forward = tran.forward()
        forward.multiply(dis)
        self.transform.translate(forward)

    def setDizzy(self):
        self.flag |= keyType.SITUATION_FLAG_MAP.DIZZY

    def removeDizzy(self):
        self.flag ^= keyType.SITUATION_FLAG_MAP.DIZZY
        logger.info(self.entity_id, "dizzy remove")

    def getBeHitHidePos(self):
        res = self.randomPos(3, self)
        return Vector3(res[0], 0, res[1])

    def randomPos(self, length, target):
        x = uniform(-length + 1, length - 1)
        z = math.sqrt((length - 1) ** 2 - x ** 2)
        if randint(-1, 1) < 0:
            z = -z
        return [target.transform.position.x + x, target.transform.position.z + z]