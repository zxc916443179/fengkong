from raySkillEntity import RaySkillEntity
from flashSwirlSkillEntity import FlashSwirlSkillEntity
from flashSkillEntity import FlashSkillEntity
from flashMeetSkillEntity import FlashMeetSkillEntity

from helpPlayerSkillEntity import HelpPlayerSkillEntity
from setting import keyType
from skillEntity import SkillEntity

import logging

logger = logging.getLogger()

buff_class_map = {
    1: RaySkillEntity,
    3: FlashSwirlSkillEntity,
    4: FlashSkillEntity,
    5: FlashMeetSkillEntity,
    6: HelpPlayerSkillEntity
}


def CreateSkillEntity(skill_id, data, room_id):
    skill = buff_class_map[skill_id](room_id)
    SkillEntity.data_center.registerEntity(keyType.Skill, skill)
    skill.initSkillData(data)
    room = SkillEntity.data_center.getRoom(room_id)
    room.joinSkill(skill.entity_id)
