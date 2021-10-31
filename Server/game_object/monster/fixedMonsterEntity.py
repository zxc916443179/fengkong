import copy
from monsterEntity import MonsterEntity
from setting import keyType
from game.utils import Vector3, Transform
from common import conf

SkillSpeed = 10
SkillRadius = 2


class FixedMonsterEntity(MonsterEntity):
    def __init__(self, rid):
        super(FixedMonsterEntity, self).__init__(rid)
        self.skillCD = 0
        self.hp = 0
        self.state = keyType.MONSTER_STATE_MAP.Idle  # 0: idle  3: attack  4: die
        self.monsterInfo = None
        self.radius = 1
        self.skillEntityTransform = None
        self.attack = False
        self.skillDistance = -1

    def initMonsterInfo(self, info):
        # type: (dict) -> None
        super(FixedMonsterEntity, self).initMonsterInfo(info)
        self.radius = info[keyType.Capsule_Radius]
        self.monsterInfo = info
        self.skillDistance = 0
        self.updateState()

    def tick(self, tick_time=0.02):
        super(FixedMonsterEntity, self).tick(tick_time)
        if self.target:
            self.updateRotation(self.transform.position, self.target.transform.position)
        self.updateState()
        if self.attack:
            self.skillHandle()

    def recoverSkillCD(self):
        if self.skillCD > 0:
            self.skillCD -= conf.MODULE_MONSTER_TICK

    def attackHandle(self):
        if self.skillCD <= 0:
            self.skillCD = self.monsterInfo[keyType.Attack_Tick]
            self.attack = True
            self.skillEntityTransform = copy.deepcopy(self.transform)
            self.sendStateToClient(self.state)

    def skillHandle(self):
        if self.skillDistance > self.monsterInfo[keyType.Attack_Range]:
            self.skillEnd()
            return
        self.skillDistance += conf.MODULE_MONSTER_TICK * SkillSpeed
        if self.target:
            dis = Vector3.Distance(self.target.transform.position, self.skillEntityTransform.position)
            if dis < SkillRadius ** 2 and self.attack:
                self.skillEnd()
                self.target.reduceHp(self.monsterInfo[keyType.Pow])
                return
        forward = self.skillEntityTransform.forward()
        forward.multiply(conf.MODULE_MONSTER_TICK * SkillSpeed)
        self.skillEntityTransform.translate(forward)

    def skillEnd(self):
        self.skillEntityTransform = None
        self.skillDistance = 0
        self.attack = False

    def updateState(self):
        if self.state == keyType.MONSTER_STATE_MAP.Idle:
            pass
        if self.state == keyType.MONSTER_STATE_MAP.Patrol:
            self.speed = self.monsterInfo[keyType.Patrol_Speed]
        elif self.state == keyType.MONSTER_STATE_MAP.Follow:
            pass
        elif self.state == keyType.MONSTER_STATE_MAP.Attack:
            self.speed = self.monsterInfo[keyType.Attack_Speed]
            self.attackHandle()
        elif self.state == keyType.MONSTER_STATE_MAP.Die:
            self.dieHandle()

    def move(self, current, target):
        # type (Vector3) -> None
        self.updateRotation(self.transform.position, target)
        diff = Vector3.Lerp(current, target, conf.MODULE_MONSTER_TICK * self.speed)
        diff.subtract(current)
        self.transform.position.add(diff)
