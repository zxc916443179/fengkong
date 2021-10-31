import random
from game.utils import Vector3, Transform
from common.rpc_queue_module import RpcMessage, RpcQueue
from game_object.buff import CreateBuff
from setting import keyType
from common_server.data_module import DataCenter
from typing import TYPE_CHECKING
from setting.keyType import PLAYER_STATE_MAP
from common import conf
import logging

if TYPE_CHECKING:
    from game_object.skill.skillEntity import SkillEntity
logger = logging.getLogger()


class WeaponBase(object):
    def __init__(self, rid, owner, _wid=None, _weapon_pow=None, _weapon_stable=None,
                 _weapon_range=None, _shock_screen=None, _move_speed=None, _fire_time=None, _fire_type=None):
        self.room_id = rid
        self.owner = owner  # eid
        self.weaponInfo = None
        self.data_center = DataCenter()
        self.rpc_queue = RpcQueue()
        self.weapon_type = _wid
        self.weapon_pow = _weapon_pow
        self.weapon_stable = _weapon_stable
        self.weapon_range = _weapon_range
        self.shock_screen = _shock_screen
        self.move_speed = _move_speed
        self.fire_time = _fire_time
        self.fire_type = _fire_type
        self.shoot_skill = None  # type: SkillEntity or None
        self.rand_seed = random.randint(1, 100)
        self.weapon_buff = None
        self.weapon_stable *= 10

        logger.info("switch to weapon %d" % self.weapon_type)

    def attackDown(self):
        logger.info("begin shoot")
        if self.move_speed != 0.0:
            self.data_center.buff_info[7]["effects"][0]["speed"] = self.move_speed
            self.weapon_buff = CreateBuff(
                self.room_id, self.owner.entity_id, self.owner.entity_id, keyType.Player, self.data_center.buff_info[7])
        skill_type = self.owner.skill_dict.flag
        if skill_type in [15, 17, 20]:
            skill_type -= 1
        room = self.data_center.getRoom(self.room_id)
        ret = {"aid": self.owner.aid_flag, "Entity_id": self.owner.entity_id,
               "Rand_seed": self.rand_seed, "Skill_Type": skill_type
               }
        self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/PerformPlayer", room.client_id_list, [],
                                              ret))

    def attackUp(self):
        self.removeWeaponBuff()
        logger.info("end shoot")

    def removeWeaponBuff(self):
        if self.weapon_buff:
            self.weapon_buff.removeBuff()
            self.weapon_buff = None

    def attackTick(self):
        return NotImplementedError

    @property
    def canAttack(self):
        return self.owner.cd[0] <= 0 and (
                self.owner.aid_flag == PLAYER_STATE_MAP.NORMAL_ATTACK_BEGIN or
                self.owner.aid_flag == PLAYER_STATE_MAP.NORMAL_ATTACK_DOWN)

    @property
    def canAttackForBazooka(self):
        return self.owner.cd[0] <= 0

    def removeWeapon(self):
        if self.shoot_skill:
            self.shoot_skill = None
        self.removeWeaponBuff()
        logger.debug("player %d weapon removed: %d" % (self.owner.entity_id, self.weapon_type))
