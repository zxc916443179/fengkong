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
        self.mockData = {
        "ppit1": {
            "main":[
                ['a',111,17000,66,],
                ['b',122,18000,33,'good']
                ]
            ,
            "detail":[
                ['long','a',600171, 'shbl', 111, 17000,'66%',],
                ['short','b',600133, 'shbg', 111, 2300,'11%',]
                ] 
            },
        "ppit2": {
            "main":[
                ['c',111,17000,66,],
                ['d',122,18000,33,'good']]
            ,
            "detail":[
                ['long','c',600171, 'shbl', 111, 17000,'66%',],
                ['short','d',600133, 'shbg', 111, 2300,'11%',]
            ]
            }
        }

        self.res = None

        self.state = 0

        self.mian_list = None
        self.detail_list = None
        pass

    def statusControl(nowState, newState):
        if nowState == 0 and newState != 0:
            return newState
        elif nowState == 1 and newState != 0:
            return newState
        elif nowState == -1 and newState != 0:
            return newState
    
    def setState(self, state):
        self.state = state
    
    def getState(self, state):
        return self.state

    def setData(self, mockData, state, res, mian_list, detail_list):
        self.mockData = mockData
        self.res = res
        self.main_list = main_list
        self.detail_list = detail_list
    
    def getData(self):
        return self.mockData, self.res, self.main_list, self.detail_list
