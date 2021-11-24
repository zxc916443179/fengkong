import configparser
from common.common_library_module import Singleton
import logging

from setting.keyType import WORKER_STATE

logger = logging.getLogger()

@Singleton
class DataCenter(object):
    def __init__(self):
        self.state = 0
        self.config = None
        self.allList = {}
        self.cf: configparser.ConfigParser = None
        self.is_main = 0 # 是否是主客户端
        self.contorller = None
    
    def regController(self, controller):
        self.contorller = controller

    def statusControl(self, nowState, newState):
        if WORKER_STATE.checkCanStateTransmit(nowState, newState):
            self.state = newState
            logger.info(f"state transmit to {newState} from {nowState}")
    
    def setState(self, state):
        self.statusControl(self.state, state)
    
    def getState(self):
        return self.state

    def setConfig(self, conf):
        self.config = conf
        self.readConfigFile()
        self.is_main = self.getCfgValue("client", "is_main")
    
    def getCfgValue(self, section: str, key: str, default: any = None):
        value = None
        try:
            value = self.cf.get(section, key)
        except:
            value = default
        if value is None:
            value = default
        if self.__is_float(value):
            return float(value)
        return value
    
    def readConfigFile(self):
        import codecs
        if self.config.config_file:
            logger.info("read config file from %s", self.config.config_file)
            self.cf = configparser.ConfigParser()
            with codecs.open(self.config.config_file, 'r', encoding="utf-8") as f:
                self.cf.readfp(f)


    def setData(self, allList):
        self.allList = allList

    def getData(self):
        return self.allList
    
    def getMainDataByKey(self, key):
        return self.allList[key]['main']

    def getDetailDataByKey(self, key):
        return self.allList[key]['detail']

    def __is_float(self, _s):
        try:
            float(str(_s))
            return True
        except:
            return False
