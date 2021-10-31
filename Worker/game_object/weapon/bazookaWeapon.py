import logging

from typing import TYPE_CHECKING
from setting import keyType
from weaponBase import WeaponBase
from ..skill.rocketEntity import RocketEntity

if TYPE_CHECKING:
    from ..player.playerEntity import PlayerEntity
logger = logging.getLogger()

RocketSpeed = 30


class BazookaWeapon(WeaponBase):
    def __init__(self, rid, owner,  # type: PlayerEntity
                 _wid=None, _weapon_pow=None, _weapon_stable=None,
                 _weapon_range=None, _shock_screen=None, _move_speed=None, _fire_time=None, _fire_type=None, _offset=None):
        super(BazookaWeapon, self).__init__(rid, owner, _wid=_wid, _weapon_pow=_weapon_pow, _weapon_stable=_weapon_stable,
                                            _weapon_range=_weapon_range, _shock_screen=_shock_screen, _move_speed=_move_speed, _fire_time=_fire_time,
                                            _fire_type=_fire_type)

    def attackUp(self):
        super(BazookaWeapon, self).attackUp()
        if self.canAttackForBazooka:
            rocket = RocketEntity(self.room_id, self.weapon_range, self.owner, self.weapon_pow, RocketSpeed)
            room = self.data_center.getRoom(self.room_id)
            self.data_center.registerEntity(keyType.Skill, rocket)
            room.joinSkill(rocket.entity_id)
            self.owner.cd[0] = self.fire_time

    def attackTick(self, tick_time=0.02):
        pass

