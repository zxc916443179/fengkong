# -*- coding: GBK -*-
from collections import deque, defaultdict
import random
import logging
from common_server.data_module import DataCenter

logger = logging.getLogger()


class SkillDict(object):
    def __init__(self):
        self.skill_can_be_light = [0, 0, 0]
        self.element = 0  # element
        self.flag = 0  # chose ele
        self.num = 0  # enhancement time
        self.ret = []
        # self.skill_dict = defaultdict(dict)
        self.skill_dict = {
            0: {
                "active": 1,
                "level": 1
            }
        }
        self.data_center = DataCenter()

    # search which is be buling
    def search(self):
        # type: (SkillDict) -> list
        skill_tree = self.data_center.skill_tree
        skill = []
        bfs_que = deque()
        bfs_que.append(0)
        while len(bfs_que) > 0:
            skillId = bfs_que.pop()
            if self.skill_dict.get(skillId) is not None and self.skill_dict[skillId]['active'] == 1:
                skill.append(skillId)
                for skill_child_id in skill_tree[skillId]['child']:
                    bfs_que.append(skill_child_id)
        return skill

    def OverSkillEnhancement(self):
        # type: (SkillDict) -> list
        self.ret = []
        skill_tree = self.data_center.skill_tree
        for skill_id in self.skill_can_be_light:
            skill_dict = {
                "Skill_name": skill_tree[skill_id]["name"],
                "Skill_id": skill_id,
                "Skill_description": skill_tree[skill_id]["description"],
                "Skill_type": skill_tree[skill_id]["type"]
            }
            self.ret.append(skill_dict)
        self.num += 1
        logger.info({"skill send": self.ret})
        return self.ret

    def add(self, eid):
        if eid not in self.skill_can_be_light:
            return 0
        skill_tree = self.data_center.skill_tree
        skill_fa_id = skill_tree[eid]['fa_id']
        if self.skill_dict.get(eid) is None or skill_tree[eid]['high_level'] > self.skill_dict[eid]['level']:
            for fa_id in skill_fa_id:
                if self.skill_dict.get(fa_id) is not None and self.skill_dict[fa_id]['active'] == 1:
                    if self.skill_dict.get(eid) is None:
                        self.skill_dict[eid] = {
                            "active": 0,
                            "level": 0
                        }
                    self.skill_dict[eid]['active'] = 1
                    self.skill_dict[eid]['level'] += 1
                    if eid in self.data_center.element_skill:
                        self.flag = eid
                    if self.flag != 0 and eid == self.flag + 1:
                        self.flag = eid
                    return 1
        return 0
