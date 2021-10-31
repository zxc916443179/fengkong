import math
from monsterEntity import MonsterEntity
from setting import keyType
from game.utils import Vector3, Random
from common_server.data_module import DataCenter
from common import conf

Accumulate_Time = 0.8


class BombMonsterEntity(MonsterEntity):
    def __init__(self, rid):
        super(BombMonsterEntity, self).__init__(rid)
        self.skillCD = 0
        self.hp = 0
        self.state = keyType.MONSTER_STATE_MAP.Idle          # 0: idle  3: attack  4: die
        self.monsterInfo = None
        self.accumulateTime = 0
        self.radius = 0

    def initMonsterInfo(self, info):
        # type: (dict) -> None
        super(BombMonsterEntity, self).initMonsterInfo(info)
        self.radius = info[keyType.Capsule_Radius]
        self.monsterInfo = info
        self.state = keyType.MONSTER_STATE_MAP.Idle
        self.updateState()

    def tick(self, tick_time=0.02):
        if self.accumulateTime == 0:
            super(BombMonsterEntity, self).tick(tick_time)
        if self.target:
            self.updateRotation(self.transform.position, self.target.transform.position)
        self.updateState()

    def recoverSkillCD(self):
        if self.skillCD > 0:
            self.skillCD -= conf.MODULE_MONSTER_TICK

    def attackHandle(self):
        self.accumulateTime += conf.MODULE_MONSTER_TICK
        if self.accumulateTime < Accumulate_Time:
            return
        for entity in self.data_center.getRoomEntity(keyType.Player, self.room_id):
            dis = Vector3.Distance(entity.transform.position, self.transform.position)
            if dis < self.monsterInfo[keyType.Attack_Range] ** 2:
                entity.reduceHp(self.monsterInfo[keyType.Pow])
        self.dieHandle()

    def reduceHp(self, dmg, dmg_type=0, eid=-1, is_critical=False, is_bullet=False):
        # type: (int, int, int, bool) -> None
        super(BombMonsterEntity, self).reduceHp(dmg, dmg_type=dmg_type, eid=eid, is_critical=is_critical, is_bullet=is_bullet)
        if is_bullet and self.beHitHidePos is None:
            self.beHitCountForBullet += 1
            if self.beHitCountForBullet == 3:
                self.beHitHidePos = self.getBeHitHidePos()

    def followHandle(self):
        if self.beHitHidePos:
            if Vector3.Distance(self.transform.position, self.beHitHidePos) >= 0.1:
                self.move(self.transform.position, self.beHitHidePos)
            else:
                self.beHitHidePos = None
                self.beHitCountForBullet = 0
            return
        if Vector3.Distance(self.transform.position, self.target.transform.position) < 4:
            self.move(self.transform.position, Random.randPosition(self.transform.position, self.target.transform.position, 1))
            return
        int_pos = Vector3(int(self.transform.position.x), int(self.transform.position.y), int(self.transform.position.z))
        path = self.nav_agent.SetDestination(int_pos, self.target.transform.position, self.room_id, step=3)
        if len(path) >= 2:
            dst = path[-2]
            dst = Vector3(dst.x + self.mapLeft, int_pos.y, dst.y - self.mapTop)
            self.move(int_pos, dst)

    def patrolHandle(self):
        if Vector3.Distance(self.transform.position, self.current_patrol_point) < 1:
            self.patrol_index = (self.patrol_index + 1) % len(self.patrol_list)
        diff = Vector3.Lerp(self.transform.position, self.current_patrol_point,
                            (conf.MODULE_MONSTER_TICK * self.speed) / math.sqrt(Vector3.Distance(self.transform.position, self.current_patrol_point))
        )
        self.transform.position = diff

    @property
    def current_patrol_point(self):
        return self.patrol_list[self.patrol_index]

    def updateState(self):
        if self.state == keyType.MONSTER_STATE_MAP.Idle:
            pass
        if self.state == keyType.MONSTER_STATE_MAP.Patrol:
            self.speed = self.monsterInfo[keyType.Patrol_Speed]
            self.patrolHandle()
        elif self.state == keyType.MONSTER_STATE_MAP.Follow:
            self.followHandle()
        elif self.state == keyType.MONSTER_STATE_MAP.Attack:
            self.attackHandle()
            self.sendStateToClient(keyType.MONSTER_STATE_MAP.Attack)
        elif self.state == keyType.MONSTER_STATE_MAP.Die:
            self.dieHandle()
