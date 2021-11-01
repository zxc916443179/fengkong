import json

from common.common_library_module import Singleton
from setting import keyType
from common_server.timer import TimerManager
import logging
from typing import TYPE_CHECKING, List, Union, Dict
import numpy as np

if TYPE_CHECKING:
    from argparse import Namespace
logger = logging.getLogger()


@Singleton
class DataCenter(object):
    def __init__(self):
        pass
    
    def setConfig(self, config):
        pass