import configparser
from common.common_library_module import Singleton
from common.rpc_queue_module import RpcMessage
from risk_manager.risk_manager import RiskManager
from setting import keyType
from common_server.timer import TimerManager
import logging
from typing import TYPE_CHECKING, List, Union, Dict, Tuple
import time

if TYPE_CHECKING:
    from argparse import Namespace
logger = logging.getLogger()

class Client(object):
    idx = 0
    def __init__(self, hid) -> None:
        self.id = self.genId()
        self.hid = hid
        self.state = keyType.CLIENT_STATE.NORMAL
    
    def genId(self):
        self.id = str(int(time.time() * 1000))[3:] + str(Client.idx)
        Client.idx += 1
        return self.id

    def setState(self, state):
        self.state = state


@Singleton
class DataCenter(object):
    def __init__(self):
        self.config = None
        self.clients: Dict[int, Client] = {}
        self.checkTimer = TimerManager.addRepeatTimer(0.2, self.checkZombieClient)
        self.cf: configparser.ConfigParser = None

        self.risk_mgrs = {}

        self.res = None
        self.res_status = None

        self.trader_list = None
        self.detail_list = None
    
    def readConfigFile(self):
        if self.config.config_file:
            logger.info("read config file from %s", self.config.config_file)
            import configparser, codecs
            self.cf = configparser.ConfigParser()
            with codecs.open(self.config.config_file, 'r', encoding="utf-8") as f:
                self.cf.readfp(f)
            pass
        pass

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

    def setConfig(self, config):
        # type: (Namespace) -> None
        self.config = config
        self.readConfigFile()

    def initPbrcsConfig(self):
        pass

    def regClient(self, client_id):
        if client_id not in self.clients:
            self.clients[client_id] = Client(client_id)
            logger.info(f"register client {client_id}, id is {self.clients[client_id].id}")
        else:
            logger.info("already exist")
    
    def checkZombieClient(self):
        clients = self.clients.values()
        remove_list = []
        for client in clients:
            if client.state == keyType.CLIENT_STATE.DEAD:
                remove_list.append(client.hid)
        for hid in remove_list:
            self.clients.pop(hid)
            logger.info(f"remove dead client {hid}")
    
    def getClient(self, hid):
        return self.clients.get(hid)
    
    def getClientById(self, id: str) -> Client or None:
        clients = self.clients.values()
        for client in clients:
            if client.id == id:
                return client
        return None
    
    def getClientList(self) -> List[int]:
        return self.clients.keys()
    
    def isClientAlive(self, hid: int) -> bool:
        return hid in self.clients and self.clients[hid].state == keyType.CLIENT_STATE.NORMAL
    
    def writeData(self, res, res_status, trader_list, detail_list):
        self.res = res
        self.res_status = res_status
        self.trader_list = trader_list
        self.detail_list = detail_list
    
    def getData(self):
        return self.res, self.res_status, self.trader_list, self.detail_list
    
    def __is_float(self, _s):
        try:
            float(str(_s))
            return True
        except:
            return False