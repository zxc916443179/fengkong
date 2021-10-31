from game.utils import Random
from setting import keyType
from setting.keyType import PLAYER_STATE_MAP
from weaponBase import WeaponBase
from typing import TYPE_CHECKING
import logging
from ..skill.raySkillEntity import RaySkillEntity
from game.utils import Vector3, Transform

if TYPE_CHECKING:
    from ..player.playerEntity import PlayerEntity
logger = logging.getLogger()


class Sniper(WeaponBase):
    def __init__(self, rid, owner  # type: PlayerEntity
                 , _wid=None, _weapon_pow=None, _weapon_stable=None,
                 _weapon_range=None, _shock_screen=None, _move_speed=None, _fire_time=None, _fire_type=None):
        super(Sniper, self).__init__(rid, owner, _wid=_wid, _weapon_pow=_weapon_pow, _weapon_stable=_weapon_stable,
                                            _weapon_range=_weapon_range, _shock_screen=_shock_screen, _move_speed=_move_speed, _fire_time=_fire_time,
                                            _fire_type=_fire_type)
        self.max_charge_time = 2.0
        self.charge_time = 0.0

    def attackUp(self):
        super(Sniper, self).attackUp()
        self.owner.cd[0] = self.fire_time
        pow = self.weapon_pow + self.charge_time * 300
        ray_shoot_skill = RaySkillEntity(
            self.room_id, self.weapon_range, self.owner, pow,  penetrated=True
        )
        ray_shoot_skill.cast(0)
        logger.info("release charge, charge time is %f" % self.charge_time)
        self.charge_time = 0

    def attackTick(self, tick_time=0.02):
        if self.canAttack:
            if self.charge_time >= self.max_charge_time:
                return
            else:
                self.charge_time = min(self.max_charge_time, self.charge_time + tick_time)
