import copy
import math
from math import sqrt
from monsterEntity import MonsterEntity
from game_object.skill.bulletEntity import BulletEntity
from setting import keyType
from game.utils import Vector3, Transform
from common import conf

BulletSpeed = 7
BulletRadius = 1
BulletLifeTime = 2
BulletTimeGap = 0.2
BulletCount = 3

Length = 60
Point = Vector3(-9.2, 0, 0)


class TurretMonsterEntity(MonsterEntity):
    def __init__(self, rid):
        super(TurretMonsterEntity, self).__init__(rid)
        self.skillCD = 0
        self.hp = 0
        self.state = keyType.MONSTER_STATE_MAP.Idle  # 0: idle  3: attack  4: die
        self.monsterInfo = None
        self.headRotateSpeed = 0
        self.headCurrentRotation = 0
        self.radius = 0
        self.skillEntityTransform = None
        self.attack = False
        self.bulletTimeGap = 0
        self.bulletCount = -1

        self.angle = 90
        self.isPatrol = False

    def initMonsterInfo(self, info):
        super(TurretMonsterEntity, self).initMonsterInfo(info)
        self.radius = info[keyType.Capsule_Radius]
        self.monsterInfo = info
        self.updateState()
        self.patrol_list = []
        self.headCurrentRotation = self.transform.rotation.y
        self.headRotateSpeed = info[keyType.Attack_Speed]

    def tick(self, tick_time=0.02):
        super(TurretMonsterEntity, self).tick(tick_time)
        self.updateState()
        self.headCurrentRotation += self.headRotateSpeed
        if self.headCurrentRotation >= 360:
            self.headCurrentRotation -= 360
        if self.attack:
            self.skillHandle()

    def getMonsterPositionData(self):
        return {
            keyType.Entity_id: self.entity_id,
            keyType.Position: self.transform.position.getDict(),
            keyType.Rotation: {"x": self.headCurrentRotation, "y": 0, "z": 0},
        }

    def recoverSkillCD(self):
        if self.skillCD > 0:
            self.skillCD -= conf.MODULE_MONSTER_TICK

    def attackHandle(self):
        if self.skillCD <= 0:
            self.skillCD = self.monsterInfo[keyType.Attack_Tick]
            self.attack = True

    def skillHandle(self):
        self.bulletTimeGap += conf.MODULE_MONSTER_TICK
        if self.bulletCount >= BulletCount:
            self.skillEnd()
            return
        if self.bulletTimeGap < BulletTimeGap:
            return
        self.bulletTimeGap = 0
        self.bulletCount += 1
        skill = BulletEntity(self.room_id)
        data = {
            keyType.Source: self,
            keyType.SkillRadius: BulletRadius,
            keyType.Position: copy.deepcopy(self.transform.position),
            keyType.Rotation: Vector3(0, self.headCurrentRotation, 0),
            keyType.Speed: BulletSpeed,
            "maxLifeTime": BulletLifeTime,
        }
        skill.initSkillInfo(data)
        self.data_center.registerEntity(keyType.Skill, skill)
        self.roomEntity.joinSkill(skill.entity_id)
        self.sendStateToClient(self.state)

    def skillEnd(self):
        self.bulletTimeGap = 0
        self.bulletCount = 0
        self.attack = False

    def patrolHandle(self):
        if Vector3.Distance(Point, self.transform.position) <= 0.01 and self.isPatrol is False:
            self.isPatrol = True
        if self.isPatrol:
            self.getNextPatrolPos()
        else:
            diff = Vector3.Lerp(self.transform.position, Point,
                                (conf.MODULE_MONSTER_TICK * self.speed) / sqrt(
                                Vector3.Distance(self.transform.position, Point)))
            self.transform.position = diff

    def getNextPatrolPos(self):
        r = Length / (2 * math.pi) / 50
        h = r * math.sin(self.angle / 180 * math.pi)
        d = r * math.cos(self.angle / 180 * math.pi)
        self.transform.position.x -= d
        self.transform.position.z -= h
        self.angle += 360 / (Length / self.monsterInfo[keyType.Attack_Speed] / conf.MODULE_MONSTER_TICK)

    def updateState(self):
        if self.state == keyType.MONSTER_STATE_MAP.Idle:
            pass
        if self.state == keyType.MONSTER_STATE_MAP.Patrol:
            self.speed = self.monsterInfo[keyType.Patrol_Speed]
            self.patrolHandle()
        elif self.state == keyType.MONSTER_STATE_MAP.Follow:
            self.patrolHandle()
        elif self.state == keyType.MONSTER_STATE_MAP.Attack:
            self.speed = self.monsterInfo[keyType.Attack_Speed]
            self.attackHandle()
            self.patrolHandle()
        elif self.state == keyType.MONSTER_STATE_MAP.Die:
            self.dieHandle()
