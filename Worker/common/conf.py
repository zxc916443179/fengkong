# -*- coding: GBK -*-

MSG_CS_LOGIN = 0x1001
MSG_SC_CONFIRM = 0x2001

MSG_CS_MOVETO = 0x1002
MSG_SC_MOVETO = 0x2002

NET_STATE_STOP = 0  # state: init value
NET_STATE_CONNECTING = 1  # state: connecting
NET_STATE_ESTABLISHED = 2  # state: connected

NET_HEAD_LENGTH_SIZE = 4  # 4 bytes little endian (x86)
NET_HEAD_LENGTH_FORMAT = '<I'

NET_CONNECTION_NEW = 0  # new connection
NET_CONNECTION_LEAVE = 1  # lost connection
NET_CONNECTION_DATA = 2  # data coming

NET_HOST_DEFAULT_TIMEOUT = 70

MAX_HOST_CLIENTS_INDEX = 0xffff
MAX_HOST_CLIENTS_BYTES = 16
INPUT_QUEUE_MAX_COUNT = 100

STATE_CHECK_TIME = 0.01
MODULE_MONSTER_TICK = 0.05

MODULE_PLAYER_TICK = 0.02

RET_CODE_MAP = {
    0: "success",

    100: "unknown exception",
    # game controller
    # user info
    101: "username already exist",
    102: "username or password incorrect",
    103: "user already login",
    201: "exceed max home limit",
    202: "not all player ready",
    203: "game not found",
    204: "cannot join right now, exceed players limit or game is ongoing",
    205: "Game has started, cannot leave",
    403: "'invalid rpc call, NOT PERMITTED:', method",
    404: "'invalid rpc call, NOT EXIST:', method"
}

FLASH_SPEED_UPGRADE = 1
FLASH_REPULSED_ENEMY = 2
FLASH_PRODUCE_HURT = 3
FLASH_SWIRL_GET = 4
FLASH_LET_EASY_HURT = 5
FLASH_LET_SPEED_lOW = 6
FLASH_REFRESH_SKILL = 7
FLASH_BIG_TRICK = 8
NORMAL_BURN_SKILL = 14
BURN_TO_BOOM = 15
NORMAL_LIGHTNING_SKILL = 16
NORMAL_LIGHTNING_ALL_SKILL = 17
CRIT_SKILL = 18
NORMAL_WATER_SKILL = 19
WATER_ADD_SKILL = 20
