Monster = "Monster"
Player = "Player"
Skill = "Skill"
Chest = "Chest"
Item = "Item"
Buff = "Buff"

Value = "value"
#  DataBase
Name = "Name"
Level = "Level"
Coin = "Coin"
Password = "Password"

#  Entity
Client_id = "Client_id"
Entity_id = "Entity_id"
Room_id = "Room_id"
Position = "Position"
Rotation = "Rotation"
RoleType = "RoleType"
Hp = "Hp"
Maxhp = "Maxhp"
Speed = "Speed"
Distance = "Distance"
State = "State"
Shield = "Shield"
Maxshield = "Maxshield"
Weapon = "Weapon"
Money = "Money"
PlayerName = "Name"
Flag = "Flag"
Type = "Type"
Angle = "Angle"

MonsterType = "monsterType"
# weapon
Wid = "_wid"
Weapon_pow = "_weapon_pow"
Weapon_range = "_weapon_range"
Weapon_stable = "_weapon_stable"
Fire_time = "_fire_time"
Fire_type = "_fire_type"
Move_speed = "_move_speed"
Shock_screen = "_shock_screen"

Patrol_Speed = "Patrol_Speed"
Patrol_Range = "Patrol_Range"
Pow = "Pow"
Attack_Tick = "Attack_Tick"
Attack_Speed = "Attack_Speed"
Attack_Range = "Attack_Range"
Bullet_Speed = "Bullet_Speed"
Bullet_Range = "Bullet_Range"
Ready_Time = "Ready_Time"
Capsule_Radius = "Capsule_Radius"
RandSeed = "RandSeed"
Source = "Source"
Target = "Target"
Cd = "CD"
SkillType = "SkillType"
SkillRadius = "SkillRadius"
SkillTime = "SkillTime"
Damage = "Damage"


class ROOM_STATE_MAP(object):
    Max_Player_In_Game = 2
    Max_Rooms = 100
    Max_Fetch_Rooms = 5

    Start = 0
    SyncingProgress = 1
    SyncedProgress = 2
    CreatePlayer = 3
    InStory = 8
    CreateMonster = 4
    Ongoing = 5
    GameOver = 6
    Bonus = 7

    Tick_Time = 0.02

    STAGE_ID_MAP = {
        1: "GoToArenaBattle",
        2: "GoToNormalBattle",
        3: "GoToArenaBattle"
    }


class PLAYER_STATE_MAP(object):
    # activate state
    Deactive = 0
    Active = 1
    Not_Ready = 2
    Ready = 3
    In_Story = 6
    In_Animation = 10
    End_Story = 7
    In_Game = 4
    Die = 5
    Deleted = 8  # deleted from whole game
    Removed = 9  # removed from room

    # Aid
    Idle = 0
    NORMAL_ATTACK_BEGIN = 9
    NORMAL_ATTACK_DOWN = 1
    NORMAL_ATTACK_UP = 2
    BURST_ATTACK = 3
    GET_DAMAGE = 4
    DIZZY = 5
    FLASH = 6
    REPEL = 7
    DELETE_HELP_PLAYER = 8
    HELP_PLAYER = 10


class STAGE_STATE_MAP(object):
    Begin = 0
    Ongoing = 1
    End = 2


class MONSTER_STATE_MAP(object):
    Idle = 0
    Patrol = 1
    Follow = 2
    Attack = 3
    Die = 4
    Visible = 5
    Invisible = 6
    Invincible = 7
    Avoid = 8

    Start_Idle_Time = 1


class ITEM_TYPE_MAP(object):
    Nothing = 0
    Health = 1
    Weapon = 2


class SKILL_TYPE_MAP(object):
    RaySkill = 0
    BulletSkill = 1


class SITUATION_FLAG_MAP(object):
    NORMAL = 0
    CAN_SAVE_OTHER_PLAYER = 1 << 0
    RAY_SHOOT = 1 << 1
    BOOM = 1 << 2
    PERFORM_LOCAL_MASK = 1 << 16
    SAVING_OTHER_PLAYER = 1 << 17
    # 16->23 same pri
    # 24->31
    DIZZY = 1 << 24
    DEATH = 1 << 25
    CORRECT_MASK = 1 << 30


class EFFECT_TYPE_MAP(object):
    DELETE = -1
    FLASH_SWIRL = 1
    WATER = 2
    LIGHTNING = 3
    WATER_SPUTTERING = 4
    BURN = 5
