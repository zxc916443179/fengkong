# coding=utf-8
from skillEntity import SkillEntity
from common.battle_queue_module import BattleMessage, BattleMsgQueue
from setting import keyType
from game.utils import Vector3
import logging

logger = logging.getLogger()


class HelpPlayerSkillEntity(SkillEntity):
    def __init__(self, rid):
        super(HelpPlayerSkillEntity, self).__init__(rid)
        self.entity_id = 0
        self.room_id = rid
        self.source = None
        self.aim = None
        self.cd = 0

    def initSkillData(self, data):
        logger.info("help skill added")
        self.source = data[keyType.Source]
        self.cd = data[keyType.Cd]
        player_entity_list = self.data_center.getRoomEntity(keyType.Player, self.room_id)
        can_be_help_distance = self.data_center.skill_data["Help_Distance"]
        for player_die in player_entity_list:
            if self.source != player_die:
                if Vector3.Distance(self.source.transform.position,
                                    player_die.transform.position) <= can_be_help_distance ** 2:
                    self.aim = player_die
        if self.aim is None:
            self.removeSkill()
        if self.source.setFlag(keyType.SITUATION_FLAG_MAP.SAVING_OTHER_PLAYER):
            # self.source.flag = keyType.SITUATION_FLAG_MAP.SAVING_OTHER_PLAYER
            self.source.writeAttr("flag", self.source.flag)

    def removeSkill(self):
        logger.info("help skill remove")
        room = self.data_center.getRoom(self.room_id)
        room.removeSkill(self.entity_id)

    def tick(self, tick_time=0.02):
        # 移除救人状态，死亡或者取消救援
        if self.source.flag & keyType.SITUATION_FLAG_MAP.SAVING_OTHER_PLAYER <= 0:
            self.removeSkill()
        self.cd -= tick_time
        target = [self.aim]
        if self.cd <= 0:
            self.battle_queue.push_msg(0, BattleMessage("playerHelped", self.source, target))
            # self.battle_queue.push_msg(0, BattleMessage(self.source, 2, target))
            # if self.aim.flag & keyType.SITUATION_FLAG_MAP.DEATH > 0:
            #     self.aim.flag ^= keyType.SITUATION_FLAG_MAP.DEATH
            if self.aim.removeFlag(keyType.SITUATION_FLAG_MAP.DEATH):
                self.aim.writeAttr("flag", self.aim.flag)
            if self.source.removeFlag(keyType.SITUATION_FLAG_MAP.SAVING_OTHER_PLAYER):
                # self.source.flag ^= keyType.SITUATION_FLAG_MAP.SAVING_OTHER_PLAYER
                self.source.writeAttr("flag", self.source.flag)
                self.removeSkill()
