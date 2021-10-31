from typing import TYPE_CHECKING
import logging
from game.utils import Vector3, Transform
from .defaultWeapon import DefaultWeapon

if TYPE_CHECKING:
    from ..player.playerEntity import PlayerEntity
logger = logging.getLogger()


class MachineGun(DefaultWeapon):
    def __init__(self, rid, owner  # type: PlayerEntity
                 , _wid=None, _weapon_pow=None, _weapon_stable=None,
                 _weapon_range=None, _shock_screen=None, _move_speed=None, _fire_time=None, _fire_type=None):
        super(MachineGun, self).__init__(rid, owner, _wid=_wid, _weapon_pow=_weapon_pow, _weapon_stable=_weapon_stable,
                                            _weapon_range=_weapon_range, _shock_screen=_shock_screen, _move_speed=_move_speed, _fire_time=_fire_time,
                                            _fire_type=_fire_type)
