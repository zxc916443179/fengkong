from monsterEntity import MonsterEntity
from setting import keyType
from game.utils import Vector3
from common.rpc_queue_module import RpcMessage
from common import conf

Distance = 2
MaxFlash = 3


class AssassinationMonsterEntity(MonsterEntity):
    def __init__(self, rid):
        super(AssassinationMonsterEntity, self).__init__(rid)
        self.skillCD = 0
        self.hp = 0
        self.state = keyType.MONSTER_STATE_MAP.Idle  # 0: idle  3: attack  4: die
        self.attackState = 0
        self.monsterInfo = None
        self.processTime = 0
        self.flashCount = 0
        self.radius = 1
        self.randomPosFlag = False
        self.lateTime = 0                            # Flash animation time
        self.canWalkList = [0, 1, 2, 3]

    def initMonsterInfo(self, info):
        # type: (dict) -> None
        super(AssassinationMonsterEntity, self).initMonsterInfo(info)
        self.radius = info[keyType.Capsule_Radius]
        self.monsterInfo = info
        self.attackState = keyType.MONSTER_STATE_MAP.Invisible
        self.updateState()

    def tick(self, tick_time=0.02):
        self.lateTime += conf.MODULE_MONSTER_TICK
        if self.flag & keyType.SITUATION_FLAG_MAP.DIZZY:
            self.state = keyType.MONSTER_STATE_MAP.Idle
            return
        if self.start_idle_time >= 0.1:
            self.start_idle_time -= conf.MODULE_MONSTER_TICK
            if self.start_idle_time < 0.1:
                self.state = keyType.MONSTER_STATE_MAP.Patrol
            return
        self.handleFallDown()

        if self.target:
            print "self: ", self.transform, "target: ", self.target.transform
            self.updateRotation(self.transform.position, self.target.transform.position)
            if self.target.hp <= 0:
                self.target = None
                self.state = keyType.MONSTER_STATE_MAP.Patrol
        else:
            self.target = self.getNearestTarget(Distance)
            if self.target:
                self.state = keyType.MONSTER_STATE_MAP.Follow
                self.sendStateToClient(keyType.MONSTER_STATE_MAP.Patrol)
                self.flashCount = 0
                self.processTime = 0
            else:
                self.state = keyType.MONSTER_STATE_MAP.Patrol
        self.processTime += conf.MODULE_MONSTER_TICK
        self.updateState()
        if self.randomPosFlag and self.lateTime >= 0.3:
            self.flashPos()

    def recoverSkillCD(self):
        if self.skillCD > 0:
            self.skillCD -= conf.MODULE_MONSTER_TICK

    def flashHandle(self):
        if self.attackState == keyType.MONSTER_STATE_MAP.Invisible and self.processTime >= 0.5:
            self.attackState = keyType.MONSTER_STATE_MAP.Visible
            self.processTime = 0
            self.sendStateToClient(self.attackState)
        if self.attackState == keyType.MONSTER_STATE_MAP.Visible and self.processTime >= 2:
            self.attackState = keyType.MONSTER_STATE_MAP.Invisible
            self.processTime = 0
            self.flashCount += 1
            self.randomPosFlag = True
            self.lateTime = 0
            if self.flashCount == MaxFlash:
                self.attackState = keyType.MONSTER_STATE_MAP.Visible
            self.sendStateToClient(self.attackState)

    def attackHandle(self):
        if self.skillCD <= 0 and self.flashCount == MaxFlash:
            self.skillCD = self.monsterInfo[keyType.Attack_Tick]
            self.target.reduceHp(self.monsterInfo[keyType.Pow])
            if self.target.setFlag(keyType.SITUATION_FLAG_MAP.DIZZY):
                self.target.writeAttr("flag", self.target.flag)
                ActionArgs = self.transform.rotation.getDict()
                self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/PerformPlayer", self.roomEntity.client_id_list, [],
                                                      {"Entity_id": self.target.entity_id, "aid": 13,
                                                       "ActionArgs": ActionArgs
                                                       }))

    def updateState(self):
        if self.state == keyType.MONSTER_STATE_MAP.Idle:
            pass
        if self.state == keyType.MONSTER_STATE_MAP.Patrol:
            self.attackState = keyType.MONSTER_STATE_MAP.Invisible
            self.sendStateToClient(self.attackState)
        elif self.state == keyType.MONSTER_STATE_MAP.Follow:
            self.speed = self.monsterInfo[keyType.Attack_Speed]
            if self.flashCount < MaxFlash:
                self.flashHandle()
            elif self.lateTime >= 0.3:
                self.sendStateToClient(keyType.MONSTER_STATE_MAP.Follow)
                self.followHandle()
        elif self.state == keyType.MONSTER_STATE_MAP.Attack:
            self.sendStateToClient(keyType.MONSTER_STATE_MAP.Attack)
            self.attackHandle()
        elif self.state == keyType.MONSTER_STATE_MAP.Die:
            self.dieHandle()

    def flashPos(self):
        res = self.randomPos(self.monsterInfo[keyType.Patrol_Range], self.target)
        mapList = self.roomEntity.currentMap.mapList
        if mapList[int(res[0]) - self.mapLeft][int(res[1]) + self.mapTop] == 0:
            self.transform.position.x = res[0]
            self.transform.position.z = res[1]
            self.randomPosFlag = False

    def followHandle(self):
        dis = Vector3.Distance(self.transform.position, self.target.transform.position)
        if dis < 1:
            self.state = keyType.MONSTER_STATE_MAP.Attack
        elif dis < 4:
            self.move(self.transform.position, self.target.transform.position)
        else:
            int_pos = Vector3(int(self.transform.position.x), int(self.transform.position.y),
                              int(self.transform.position.z))
            path = self.nav_agent.SetDestination(int_pos, self.target.transform.position, self.room_id, step=3,
                                                 walkList=self.canWalkList)
            if len(path) >= 2:
                dst = Vector3(path[-2].x + self.mapLeft, int_pos.y, path[-2].y - self.mapTop)
                self.move(int_pos, dst)

    def dieHandle(self):
        if self.target is not None and self.target.removeFlag(keyType.SITUATION_FLAG_MAP.DIZZY):
            self.target.writeAttr("flag", self.target.flag)
        super(AssassinationMonsterEntity, self).dieHandle()

    def repelMonster(self, angle, dis):  # type: (Vector3, float) -> None
        if self.state == keyType.MONSTER_STATE_MAP.Attack:
            return
        super(AssassinationMonsterEntity, self).repelMonster(angle, dis)

    def reduceHp(self, dmg, dmg_type=0, eid=-1, is_critical=False, is_bullet=False):
        if self.attackState == keyType.MONSTER_STATE_MAP.Invisible:
            return
        super(AssassinationMonsterEntity, self).reduceHp(dmg, dmg_type=0, eid=-1, is_critical=False, is_bullet=False)