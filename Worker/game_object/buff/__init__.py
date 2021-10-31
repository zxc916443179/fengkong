from buffBase import Buff
from numericBuff import NumericBuff
from hurtBuff import HurtBuff
from burnBuff import BurnBuff
from lightningBuff import LightningBuff
from stateBuff import StateBuff
from blankBuff import BlankBuff
from waterBuff import WaterBuff
from buffBase import Buff
from setting import keyType

import logging

logger = logging.getLogger()

buff_class_map = {
    1: NumericBuff,
    3: HurtBuff,
    4: BurnBuff,
    5: LightningBuff,
    6: StateBuff,
    7: BlankBuff,
    8: WaterBuff
}


def CreateBuff(room_id, source, target, target_entity_type, buff_data):
    # type: (int, int, int, str, dict) -> Buff or None
    for buff in Buff.data_center.getRoomEntity(keyType.Buff, room_id):
        if buff.target == target and buff.group == buff_data["group"] and buff.buff_type == buff_data["buff_type"]:
            if buff.prior > buff_data["prior"]:
                logger.info("already have higher prior buff, no effect")
                return None
            elif buff.prior == buff_data["prior"] and buff.same_priority_replace_rule == 1:
                buff.addPack()
                logger.info("add buff pack")
                return buff
            else:
                buff.time = buff_data["time"]
                return buff
    buff_instance = buff_class_map[buff_data["group"]](room_id, source, target, target_entity_type, buff_data)
    room = Buff.data_center.getRoom(room_id)
    Buff.data_center.registerEntity(keyType.Buff, buff_instance)
    room.addEntity(keyType.Buff, buff_instance.entity_id)
    return buff_instance
