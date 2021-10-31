import random
from monsterEntity import MonsterEntity
from setting import keyType
from common_server.data_module import DataCenter
from common.rpc_queue_module import RpcQueue, RpcMessage
from common import conf
from game.utils import Vector3

Accumulate_Time = 0.5
Boss_MaxHp = 8000
Boss_Radius = 2.5
Move_Speed = 2.5
Rush_Speed = 16
Aoe_Speed = 5
Aoe_Radius = 5
Aoe_Tick = 1
Aoe_Time = 3.2
Rush_Pow = 20
Rush_Distance = 15
Aoe_Pow = 20
Skill_CD = 2
InvincibleCount = 1  # 2

Aoe_State = 8
Rush_State = 9


class BossMonsterEntity(MonsterEntity):
    def __init__(self, rid):
        super(BossMonsterEntity, self).__init__(rid)
        self.skillCD = 0
        self.state = 0  # 0: idle  3: attack  4: die
        self.skillHandle = None
        self.skillTime = 0
        self.dmgCount = 1
        self.invincibleCount = InvincibleCount
        self.skillDistance = 0
        self.beginAni = True
        self.dmgDict = {}  # eid, hpValue
        self.radius = 0

    def initMonsterInfo(self, info):
        super(BossMonsterEntity, self).initMonsterInfo(info)
        self.monsterInfo = info
        self.hp = Boss_MaxHp
        self.speed = Move_Speed
        self.state = keyType.MONSTER_STATE_MAP.Invincible
        self.skillCD = 0
        self.radius = Boss_Radius
        self.skillEnd()

    def tick(self, tick_time=0.02):
        if self.target and self.skillHandle is None and self.state == keyType.MONSTER_STATE_MAP.Attack:
            self.updateRotation(self.transform.position, self.target.transform.position)
        self.updateState()
        if self.skillHandle:
            self.skillHandle()

    @property
    def isInvincible(self):
        return self.state == keyType.MONSTER_STATE_MAP.Invincible

    def getTarget(self):
        value = -0x3f3f3f3f
        resEntity = None
        player_list = self.data_center.getRoomEntity(keyType.Player, self.room_id)
        for entity in player_list:
            dis = Vector3.Distance(entity.transform.position, self.transform.position)
            v = self.dmgDict.get(entity.entity_id, 0) - (2 * dis) - (2 * entity.hp)
            if v > value and entity.isAlive:
                value = v
                resEntity = entity
        return resEntity

    def reduceHp(self, value, dmg_type=0, eid=-1, is_critical=False, is_bullet=False):
        # type: (int, int, int, bool, bool) -> None
        if dmg_type in [15, 17, 20]:
            dmg_type -= 1
            value = value * (1 + self.dmg_rate)
        if self.state == keyType.MONSTER_STATE_MAP.Attack:
            self.hp -= value
            self.rpc_queue.push_msg(0, RpcMessage("BattleHandler/HandleMonsterDamaged", self.roomEntity.client_id_list, [],
                                                  {"Entity_id": self.entity_id, "Hp": self.hp, "Type": dmg_type,
                                                   "Is_critical": is_critical}))
            if eid != -1:
                if self.dmgDict.get(eid) is None:
                    self.dmgDict[eid] = value
                else:
                    self.dmgDict[eid] += value
            if self.hp <= Boss_MaxHp / 2 and self.invincibleCount > 0:
                self.invincibleCount -= 1
                self.state = keyType.MONSTER_STATE_MAP.Invincible
            elif self.hp <= 0:
                self.state = keyType.MONSTER_STATE_MAP.Die
        else:
            return

    def recoverSkillCD(self):
        if self.skillCD > 0 and self.skillHandle is None:
            self.skillCD -= conf.MODULE_MONSTER_TICK

    def attackHandle(self):
        if self.skillCD <= 0 and self.skillHandle is None:
            self.target = self.getTarget()
            if random.randint(-1, 1) < 0:
                self.speed = Rush_Speed
                self.skillHandle = self.rushSkillHandle
                self.sendStateToClient(Rush_State)
            else:
                self.speed = Aoe_Speed
                self.skillHandle = self.aoeSkillHandle
                self.sendStateToClient(Aoe_State)
        elif self.skillCD > 0 and self.skillHandle is None and self.target:
            self.attackMove(self.target.transform.position)

    def rushSkillHandle(self):
        flag = self.roomEntity.currentMap.isCellEquals(self.transform.position.x, self.transform.position.z, 1)
        if self.skillDistance > Rush_Distance or flag:
            self.skillEnd()
            return
        self.skillTime += conf.MODULE_MONSTER_TICK
        if self.skillTime < 0:
            self.updateRotation(self.transform.position, self.target.transform.position)
            return
        self.skillDistance += conf.MODULE_MONSTER_TICK * Rush_Speed
        if self.target:
            dis = Vector3.Distance(self.target.transform.position, self.transform.position)
            if dis < self.radius ** 2 and self.dmgCount == 0:
                self.dmgCount += 1
                self.target.reduceHp(Rush_Pow)
        forward = self.transform.forward()
        forward.multiply(conf.MODULE_MONSTER_TICK * Rush_Speed)
        self.transform.translate(forward)

    def aoeSkillHandle(self):
        if self.skillTime > Aoe_Time:
            self.skillEnd()
            return
        self.skillTime += conf.MODULE_MONSTER_TICK
        self.attackMove(self.target.transform.position)
        if self.skillTime >= self.dmgCount:
            self.dmgCount += 1
            player_list = self.data_center.getRoomEntity(keyType.Player, self.room_id)
            for entity in player_list:
                dis = Vector3.Distance(entity.transform.position, self.transform.position)
                if dis < Aoe_Radius ** 2:
                    entity.reduceHp(Aoe_Pow)

    def invincibleHandle(self):
        if self.beginAni is False or self.skillHandle:
            return
        if abs(self.transform.position.x) <= 0.2 and abs(self.transform.position.z) <= 0.2:
            self.beginAni = False
            self.sendStateToClient(keyType.MONSTER_STATE_MAP.Invincible)
        else:
            self.attackMove(Vector3(0, 0, 0))

    def getBossState(self):
        return self.state

    def removeInvincible(self):
        self.sendStateToClient(keyType.MONSTER_STATE_MAP.Follow)
        self.state = keyType.MONSTER_STATE_MAP.Attack
        self.beginAni = True

    def skillEnd(self):
        self.speed = Move_Speed
        self.skillCD = Skill_CD
        self.sendStateToClient(keyType.MONSTER_STATE_MAP.Follow)
        self.dmgDict.clear()
        self.dmgCount = 0
        self.skillTime = -1.5
        self.skillDistance = 0
        self.skillHandle = None

    def updateState(self):
        if self.state == keyType.MONSTER_STATE_MAP.Idle:
            pass
        elif self.state == keyType.MONSTER_STATE_MAP.Patrol:
            pass
        elif self.state == keyType.MONSTER_STATE_MAP.Follow:
            pass
        elif self.state == keyType.MONSTER_STATE_MAP.Attack:
            self.attackHandle()
        elif self.state == keyType.MONSTER_STATE_MAP.Invincible:
            self.invincibleHandle()
        elif self.state == keyType.MONSTER_STATE_MAP.Die:
            self.dieHandle()

    def attackMove(self, position):
        if Vector3.Distance(self.transform.position, position) < 4:
            self.move(self.transform.position, position)
            return
        int_pos = Vector3(int(self.transform.position.x), int(self.transform.position.y),
                          int(self.transform.position.z))
        path = self.nav_agent.SetDestination(int_pos, position, self.room_id, step=3)
        if len(path) >= 2:
            dst = path[-2]
            dst = Vector3(dst.x + self.mapLeft, int_pos.y, dst.y - self.mapTop)
            self.move(int_pos, dst)
