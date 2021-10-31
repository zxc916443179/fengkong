from game.utils import Random
from weaponBase import WeaponBase
from typing import TYPE_CHECKING
import logging
from ..skill.raySkillEntity import RaySkillEntity

if TYPE_CHECKING:
    from ..player.playerEntity import PlayerEntity
logger = logging.getLogger()


class DefaultWeapon(WeaponBase):
    def __init__(self, rid, owner,  # type: PlayerEntity
                 _wid=None, _weapon_pow=None, _weapon_stable=None, _weapon_range=None, _shock_screen=None,
                 _move_speed=None, _fire_time=None, _fire_type=None):
        super(DefaultWeapon, self).__init__(rid, owner, _wid=_wid, _weapon_pow=_weapon_pow,
                                            _weapon_stable=_weapon_stable, _weapon_range=_weapon_range,
                                            _shock_screen=_shock_screen, _move_speed=_move_speed, _fire_time=_fire_time,
                                            _fire_type=_fire_type)
        self.initShootSkill()

    def initShootSkill(self):
        self.shoot_skill = RaySkillEntity(self.room_id, self.weapon_range, self.owner, self.weapon_pow)

    def attackTick(self):
        if self.canAttack:
            self.rand_seed = Random.rand(self.rand_seed)
            jitter_coff = (self.rand_seed % self.weapon_stable * 2 - self.weapon_stable) / 10.0
            self.shoot_skill.cast(jitter_coff)
            self.owner.cd[0] = self.fire_time