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
        self.config = None

        self.res = None
        self.res_status = None

        self.trader_list = None
        self.detail_list = None
        pass
    
    def setConfig(self, config):
        self.config = config
    
    def writeData(self, res, res_status, trader_list, detail_list):
        self.res = res
        self.res_status = res_status
        self.trader_list = trader_list
        self.detail_list = detail_list
    
    def getData(self):
        return self.res, self.res_status, self.trader_list, self.detail_list