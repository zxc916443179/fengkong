from setting import keyType
from typing import TYPE_CHECKING
import logging

from .defaultWeapon import DefaultWeapon
from ..skill.raySkillEntity import RaySkillEntity
from game.utils import Vector3, Transform

if TYPE_CHECKING:
    from ..player.playerEntity import PlayerEntity
logger = logging.getLogger()


class LaserWeapon(DefaultWeapon):
    def __init__(self, rid, owner,  # type: PlayerEntity
                 _wid=None, _weapon_pow=None, _weapon_stable=None,
                 _weapon_range=None, _shock_screen=None, _move_speed=None, _fire_time=None, _fire_type=None):
        super(LaserWeapon, self).__init__(rid, owner, _wid=_wid, _weapon_pow=_weapon_pow, _weapon_stable=_weapon_stable,
                                            _weapon_range=_weapon_range, _shock_screen=_shock_screen, _move_speed=_move_speed, _fire_time=_fire_time,
                                            _fire_type=_fire_type)

    def initShootSkill(self):
        self.shoot_skill = RaySkillEntity(self.room_id, self.weapon_range, self.owner, self.weapon_pow, penetrated=True)
        self.data_center.registerEntity(keyType.Skill, self.shoot_skill)
        room = self.data_center.getRoom(self.room_id)
        room.joinSkill(self.shoot_skill.entity_id)

    def attackTick(self):
        if self.canAttack:
            self.shoot_skill.cast()
            self.owner.cd[0] = self.fire_time
