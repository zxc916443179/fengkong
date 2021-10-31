from arenaStage import ArenaStage
from escapeStage import EscapeStage
from bossStage import BossStage
from stage import StageInfo
import logging

logger = logging.getLogger()

Stage_ID_MAP = {1: ArenaStage, 2: EscapeStage, 3: ArenaStage, 4: EscapeStage, 5: ArenaStage, 6: BossStage}


def CreateStageInfo(rid, stage_info=None):
    # type: (int, dict) -> StageInfo
    return Stage_ID_MAP[stage_info["stageID"]](rid, stage_info)
