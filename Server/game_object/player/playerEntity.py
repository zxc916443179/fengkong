import copy
import logging
from common import conf
from common.rpc_queue_module import RpcMessage
from game.skill_dict import SkillDict
from game.utils import Vector3, Transform, Collide, Random
from game_object.buff import CreateBuff
from game_object.entity import Entity
from game_object.skill.flashMeetSkillEntity import FlashMeetSkillEntity
from game_object.skill.flashSkillEntity import FlashSkillEntity
from game_object.skill.flashSwirlSkillEntity import FlashSwirlSkillEntity
from game_object.skill.helpPlayerSkillEntity import HelpPlayerSkillEntity
from game_object.weapon.bazookaWeapon import BazookaWeapon
from game_object.weapon.defaultWeapon import DefaultWeapon
from game_object.weapon.laserWeapon import LaserWeapon
from game_object.weapon.machineGun import MachineGun
from game_object.weapon.shotGunWeapon import ShotGun
from game_object.weapon.sniperWeapon import Sniper
from game_object.weapon.weaponBase import WeaponBase
from common_server.timer import TimerManager
from setting import keyType
from setting.keyType import PLAYER_STATE_MAP

logger = logging.getLogger()
Weapon_Type_Map = {
    0: DefaultWeapon,
    1: LaserWeapon,
    2: MachineGun,
    3: ShotGun,
    4: Sniper,
    5: BazookaWeapon
}


class PlayerEntity(Entity):
    id_idx = 1

    def __init__(self, eid, rid, hid):
        super(PlayerEntity, self).__init__(rid)
        self.transform = None
        self.initialize(eid, rid, hid)
        self.last_position = None
        self.timer = None

    @property
    def isAlive(self):
        return (not self.flag & keyType.SITUATION_FLAG_MAP.DEATH) and self.state == PLAYER_STATE_MAP.In_Game

    def initPlayerData(self, data):
        self.skill_tree = self.data_center.skill_tree
        self.transform = Transform(Vector3(from_dict=data[keyType.Position]), Vector3(from_dict=data[keyType.Rotation]))
        self.default_weapon = None
        self.weapon = None
        self.setWeapon(0)
        self.default_weapon = self.weapon
        self.speed = data[keyType.Speed]

    def getPlayerData(self):
        return {
            keyType.Entity_id: self.entity_id,
            keyType.Room_id: self.room_id,
            # keyType.Speed: self.speed,
            keyType.State: self.state,
            keyType.Position: self.transform.position.getDict() if self.transform else "",
            keyType.Rotation: self.transform.rotation.getDict() if self.transform else "",
            # keyType.Flag: self.flag,
        }

    def getPlayerBasicInfo(self):
        return {
            keyType.State: self.state,
            keyType.Entity_id: self.entity_id,
            keyType.Room_id: self.room_id,
            keyType.Name: self.name,
        }

    def getPlayerStatInfo(self):
        return {
            keyType.Entity_id: self.entity_id,
            keyType.Room_id: self.room_id,
            keyType.Hp: float(self.hp * 1.0),
            keyType.Maxhp: float(self.maxhp * 1.0),
            keyType.Shield: float(self.shield * 1.0),
            keyType.Maxshield: float(self.maxshield * 1.0),
            keyType.Speed: float(self.speed * 1.0),
            keyType.Weapon: self.weapon.weapon_type if self.weapon else 0,
            keyType.Flag: self.flag,
            keyType.State: self.state,
            keyType.Cd: [round(cd, 1) for cd in self.cd],
            keyType.Position: self.transform.position.getDict() if self.transform else "",
            keyType.Rotation: self.transform.rotation.getDict() if self.transform else "",
        }

    def updateWalkRotation(self, position):
        position1 = Vector3(self.transform.position.x, 0, self.transform.position.z)
        position2 = Vector3(position.x, 0, position.z)
        if Vector3.Distance(position1, position2) > 0.01:
            angle = Collide.rayDir(position1, position2)
            self.walk_rotation = Vector3(0, angle, 0)

    def updateTransform(self, position, rotation):
        # type: (Vector3, Vector3) -> None
        self.transform.position = position
        self.transform.rotation = rotation

    def updateWeaponTransform(self, position):
        self.weapon_position =position

    def recover(self, tick_time=0.02):
        #  CD
        for i in range(len(self.cd)):
            if self.cd[i] > 0:
                self.cd[i] = max(0., self.cd[i] - tick_time)
                if self.cd[i] <= 0:
                    self.writeAttr("cd", self.cd)

        if self.weapon and self.weapon.weapon_type != 0:
            self.weapon_time = max(0, self.weapon_time - tick_time)
            if self.weapon_time <= 0:
                self.setWeapon(0)

        # can do low 16 things
        if self.flag & 0xFFFF0000 <= 0:
            self.canHelp()
            if self.weapon:
                self.weapon.attackTick()
        self.handleFallDown()

    def handleFallDown(self, tick_time=0.02):
        room = self.data_center.getRoom(self.room_id)
        if room.currentMap.isCellEquals(self.transform.position.x, self.transform.position.z, 3):
            if self.setFlag(keyType.SITUATION_FLAG_MAP.PERFORM_LOCAL_MASK):
                self.writeAttr("flag", self.flag)
                ActionArgs = Vector3(self.transform.position.x, -15, self.transform.position.z).getDict()
                ActionArgs["Speed"] = 9.8
                ActionArgs["Flag"] = self.flag
                self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/PerformPlayer", room.client_id_list, [],
                                                      {"Entity_id": self.entity_id, "aid": 6,
                                                       "ActionArgs": ActionArgs
                                                       }))
            self.transform.position.y -= 9.8 * tick_time
            logger.debug("fallen down, position is %s" % self.transform.position.getDict())
            if self.transform.position.y < -15:
                self.transform.position = self.last_position
                logger.info("fallen into deepest, reset position %s" % self.transform.position.getDict())
                if self.setFlag(keyType.SITUATION_FLAG_MAP.CORRECT_MASK):
                    self.writeAttrs(["hp", "flag"], [self.hp - 30, self.flag])
                    unset_flag = keyType.SITUATION_FLAG_MAP.CORRECT_MASK
                    self.timer = TimerManager.addTimer(1.0, lambda: self.writeAttr("flag", self.flag ^ unset_flag))

    def setPlayerPosition(self, position):
        # type: (Vector3) -> None
        if self.setFlag(keyType.SITUATION_FLAG_MAP.CORRECT_MASK):
            self.writeAttr("flag", self.flag)
            self.transform.position = position
            TimerManager.addTimer(0.5, lambda: self.removeFlag(keyType.SITUATION_FLAG_MAP.CORRECT_MASK))

    def canHelp(self):
        player_entity_list = self.data_center.getRoomEntity(keyType.Player, self.room_id)
        can_be_help_distance = self.data_center.skill_data["Help_Distance"]
        for player in player_entity_list:
            if player.entity_id != self.entity_id and player.hp <= 0:
                d = Vector3.Distance(player.transform.position, self.transform.position)
                if d <= can_be_help_distance ** 2:
                    if self.setFlag(keyType.SITUATION_FLAG_MAP.CAN_SAVE_OTHER_PLAYER):
                        self.writeAttr("flag", self.flag)
                        logger.info("get die in range flag %d" % self.flag)
                    # if not self.flag & keyType.SITUATION_FLAG_MAP.CAN_SAVE_OTHER_PLAYER:
                    #     self.flag |= keyType.SITUATION_FLAG_MAP.CAN_SAVE_OTHER_PLAYER
                    #     self.writeAttr("flag", self.flag)
                    #     logger.info("get die in range flag %d" % self.flag)
                    return
        if self.removeFlag(keyType.SITUATION_FLAG_MAP.CAN_SAVE_OTHER_PLAYER):
            self.writeAttr("flag", self.flag)
            logger.info("lose die in range, set flag %d" % self.flag)
        # if self.flag & keyType.SITUATION_FLAG_MAP.CAN_SAVE_OTHER_PLAYER:
        #     self.flag ^= keyType.SITUATION_FLAG_MAP.CAN_SAVE_OTHER_PLAYER
        #     self.writeAttr("flag", self.flag)
        #     logger.info("lose die in range, set flag %d" % self.flag)

    def setWeapon(self, weapon_type):
        # type: (int) -> None
        if self.weapon and self.weapon.weapon_type != 0:
            self.weapon.removeWeapon()
        if self.weapon and weapon_type == 0:
            self.weapon = self.default_weapon
        else:
            weapon_info = self.data_center.weapon_info[weapon_type]
            logger.info(weapon_info)
            self.weapon = Weapon_Type_Map[weapon_type](self.room_id, self, **weapon_info)
            self.weapon_time = 20.
        if self.default_weapon is not None:  # don't send to client while initialize
            self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/SetPlayerWeaponType",
                                                  self.data_center.getRoom(self.room_id).client_id_list, [],
                                                  {"Entity_id": self.entity_id, "_wid": self.weapon.weapon_type}))
        if self.removeFlag(keyType.SITUATION_FLAG_MAP.RAY_SHOOT):
            self.aid_flag = PLAYER_STATE_MAP.NORMAL_ATTACK_UP
            room = self.data_center.getRoom(self.room_id)
            self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/PerformPlayer", room.client_id_list, [],
                                                  {"aid": self.aid_flag, "Entity_id": self.entity_id}))

    def addHp(self, hp):
        self.hp += hp
        if self.hp > self.maxhp:
            self.shield = min(self.shield + self.hp - self.maxhp, self.maxshield)
            self.hp = self.maxhp
        self.writeAttrs(["hp", "shield"], [self.hp, self.shield])
        room = self.data_center.getRoom(self.room_id)
        self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/PerformPlayer", room.client_id_list, [],
                                              {"Entity_id": self.entity_id, "aid": 11
                                               }))

    def reduceHp(self, dmg):
        dmg *= (1 + self.dmg_rate)
        self.shield -= dmg
        if self.shield <= 0:
            self.hp = max(0, self.hp + self.shield)
            self.shield = 0
        if self.hp <= 0:
            self.aid_flag = keyType.PLAYER_STATE_MAP.Die
            self.setFlag(keyType.SITUATION_FLAG_MAP.DEATH)
            self.writeAttrs(["hp", "shield", "flag"], [self.hp, self.shield, self.flag])  # keyType
            # .SITUATION_FLAG_MAP.DEATH])
            logger.info("player die %d" % self.entity_id)
        else:
            self.writeAttrs(["hp", "shield"], [self.hp, self.shield])
            room = self.data_center.getRoom(self.room_id)
            self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/PerformPlayer", room.client_id_list, [],
                                                  {"Entity_id": self.entity_id, "aid": 12
                                                   }))

    def updateProgress(self, progress):
        self.progress = progress
        logger.debug("update player[%d], progress is %f" % (self.entity_id, self.progress))

    def setReadyState(self):
        self.state = PLAYER_STATE_MAP.Ready if self.state == PLAYER_STATE_MAP.Not_Ready else PLAYER_STATE_MAP.Not_Ready
        logger.debug("set ready state: %d" % self.state)

    def flashSkillDeal(self):
        self.cd[1] = self.data_center.skill_data["Flash_Cd"]
        self.writeAttr("cd", self.cd)
        if self.skill_dict.skill_dict.get(conf.FLASH_SWIRL_GET) is not None and self.skill_dict.skill_dict[conf.FLASH_SWIRL_GET]["active"]:
            self.flashStarSwirl()
        if self.skill_dict.skill_dict.get(conf.FLASH_SPEED_UPGRADE) is not None and self.skill_dict.skill_dict[conf.FLASH_SPEED_UPGRADE]["active"]:
            buff_id_list = self.data_center.skill_tree[conf.FLASH_SPEED_UPGRADE]['buff_id']
            for buff_id in buff_id_list:
                CreateBuff(self.room_id, -1, self.entity_id, keyType.Player, self.data_center.buff_info[buff_id])
        self.flashMeetMonster()
        self.flashSkill()

    def flashSkill(self):
        flash_skill = FlashSkillEntity(self.room_id)
        self.data_center.registerEntity(keyType.Skill, flash_skill)
        data = {
            keyType.Position: self.transform.position,
            keyType.Source: self
        }
        flash_skill.initSkillData(data)
        room = self.data_center.getRoom(self.room_id)
        room.joinSkill(flash_skill.entity_id)

    def flashStarSwirl(self):
        flash_swirl = FlashSwirlSkillEntity(self.room_id)
        self.data_center.registerEntity(keyType.Skill, flash_swirl)
        data = {
            keyType.Position: copy.copy(self.transform.position),
            keyType.Source: self,
            keyType.Cd: self.skill_tree[conf.FLASH_SWIRL_GET][keyType.Value][1]
        }
        flash_swirl.initSkillData(data)
        room = self.data_center.getRoom(self.room_id)
        room.joinSkill(flash_swirl.entity_id)

    def flashMeetMonster(self):
        flash = FlashMeetSkillEntity(self.room_id, self.transform.position)
        self.data_center.registerEntity(keyType.Skill, flash)
        data = {
            keyType.Position: copy.copy(self.transform.position),
            keyType.Source: self
        }
        flash.initSkillData(data)
        room = self.data_center.getRoom(self.room_id)
        room.joinSkill(flash.entity_id)

    def helpPlayer(self):
        rescue = HelpPlayerSkillEntity(self.room_id)
        self.data_center.registerEntity(keyType.Skill, rescue)
        data = {
            keyType.Source: self,
            keyType.Cd: self.data_center.skill_data["Help_Cd"]
        }
        rescue.initSkillData(data)
        room = self.data_center.getRoom(self.room_id)
        room.joinSkill(rescue.entity_id)
        logger.info(self.flag)

    def deleteHelpPlayer(self):
        self.removeFlag(keyType.SITUATION_FLAG_MAP.SAVING_OTHER_PLAYER)
        # if self.flag & keyType.SITUATION_FLAG_MAP.SAVING_OTHER_PLAYER > 0:
        #     self.flag ^= keyType.SITUATION_FLAG_MAP.SAVING_OTHER_PLAYER
        #     self.writeAttr("flag", self.flag)

    def setFlag(self, aim):
        if aim & self.flag > 0:
            return 0
        if aim >= (1 << 16):
            # aim is high 23
            if aim > (1 << 23):
                self.flag = aim
                return 1
            # aim is low 23
            else:
                # flag 16 -> 32 aim 16 -> 23
                if self.flag >= (1 << 16):
                    return 0
                # flag 0 -> 16 aim 16 -> 23
                else:
                    self.flag = aim
                    return 1
        else:
            # flag 16 -> 32 aim 0 -> 16
            if self.flag >= (1 << 16):
                return 0
            # flag 0 -> 16 aim 0 -> 16
            else:
                self.flag |= aim
                return 1

    def removeFlag(self, aim):
        if self.flag & aim > 0:
            self.flag ^= aim
            self.writeAttr("flag", self.flag)
            return 1
        return 0

    def attackHandle(self, skill_type):
        # type: (int) -> int
        if skill_type == 0:
            logger.info("player attack")
            self.aid_flag = PLAYER_STATE_MAP.NORMAL_ATTACK_DOWN
            if self.setFlag(keyType.SITUATION_FLAG_MAP.RAY_SHOOT):
                # self.flag |= keyType.SITUATION_FLAG_MAP.RAY_SHOOT
                self.writeAttr("flag", self.flag)
                self.weapon.attackDown()
        elif skill_type == 1:
            logger.info("player flash")
            if self.cd[1] <= 0:
                self.aid_flag = PLAYER_STATE_MAP.FLASH
                self.flashSkillDeal()
        elif skill_type == 2:
            logger.info("rescue player")
            self.aid_flag = PLAYER_STATE_MAP.HELP_PLAYER
            self.helpPlayer()

        return self.aid_flag

    def skillOver(self, skill_type):
        if skill_type == 0:
            self.aid_flag = PLAYER_STATE_MAP.NORMAL_ATTACK_UP
            if self.removeFlag(keyType.SITUATION_FLAG_MAP.RAY_SHOOT):
                # self.flag ^= keyType.SITUATION_FLAG_MAP.RAY_SHOOT
                self.writeAttr("flag", self.flag)
                self.weapon.attackUp()

        elif skill_type == 2:
            self.aid_flag = PLAYER_STATE_MAP.DELETE_HELP_PLAYER
            self.deleteHelpPlayer()
        return self.aid_flag

    def addSkill(self, skill_id):
        self.skill_dict.add(skill_id)

    def search(self, skill_added_id):
        if skill_added_id == 8:
            pass  # sent to client
        if skill_added_id == 9:
            value = self.skill_tree[skill_added_id][keyType.Value]
            self.maxhp = self.maxhp + value[0]
            self.writeAttr("maxhp", self.maxhp)
        if skill_added_id == 10:
            value = self.skill_tree[skill_added_id][keyType.Value]
            self.maxhp = self.maxhp + value[0]
            self.writeAttr("maxhp", self.maxhp)
        if skill_added_id == 11:
            value = self.skill_tree[skill_added_id][keyType.Value]
            self.maxshield = self.maxshield + value[0]
            self.writeAttr("maxshield", self.maxshield)
        if skill_added_id == 12:
            value = self.skill_tree[skill_added_id][keyType.Value]
            self.maxshield = self.maxshield + value[0]
            self.writeAttr("maxshield", self.maxshield)
        if skill_added_id == 13:
            if self.flag & keyType.SITUATION_FLAG_MAP.DEATH:
                self.flag ^= keyType.SITUATION_FLAG_MAP.DEATH
                self.writeAttr("flag", self.flag)
            self.hp = self.maxhp
            self.writeAttr("hp", self.hp)
        if skill_added_id == 10:
            self.prd_c = Random.prdC(0.1)
            self.magnification = 2
        self.shield = self.maxshield

    def initialize(self, eid, rid, hid):
        self.entity_id = eid
        self.room_id = rid
        self.client_id = hid
        self.radius = 1
        self.rand_seed = 0
        self.magnification = 0
        self.name = "test1"
        self.dmg_rate = 0
        self.walk_rotation = Vector3(0, 0, 0)
        self.hp = 1000000
        self.maxhp = 1000000
        self.shield = 50
        self.maxshield = 50
        self.speed = 0
        self.flag = keyType.SITUATION_FLAG_MAP.NORMAL  # in game situation state
        self.cd = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.skill_tree = None
        self.timer = None
        self.weapon = None  # type: WeaponBase or None
        self.weapon_position = Vector3(0, 0, 0)
        self.default_weapon = None
        self.weapon_time = 0
        self.progress = 0.
        self.prd_c = 0
        self.n = 0
        self.help_entity = None
        self.aid_flag = PLAYER_STATE_MAP.Idle
        self.state = PLAYER_STATE_MAP.Active  # mainly use for before game state
        self.sync_rpc_url = "PlayerSyncHandler/UpdatePlayerAttribute"
        self.cold_data_list += ["shield", "flag", "maxhp", "maxshield", "cd"]
        self.skill_dict = SkillDict()
