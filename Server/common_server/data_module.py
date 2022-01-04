import configparser
from common.common_library_module import Singleton
from common.rpc_queue_module import RpcMessage, RpcQueue
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
        self.pf: configparser.ConfigParser = None

        self.risk_mgrs: dict[str, RiskManager] = {}
        self.ticker = None
        self.rpc_queue = RpcQueue()

    def readConfigFile(self):
        import codecs
        if self.config.config_file:
            logger.info("read config file from %s", self.config.config_file)
            self.cf = configparser.ConfigParser()
            with codecs.open(self.config.config_file, 'r', encoding="utf-8") as f:
                self.cf.readfp(f)
        if self.config.pbrc_file:
            logger.info("read pbrc config file from %s", self.config.pbrc_file)
            self.pf = configparser.ConfigParser()
            with codecs.open(self.config.pbrc_file, 'r', encoding="utf-8") as f:
                self.pf.readfp(f)

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
        self.initPbrcsConfig()
        self.ticker = TimerManager.addRepeatTimer(self.getCfgValue("server", "tick_time", 1.0), self.tick)
        logger.info("初始化完毕，参数信息：")
        logger.info(f"[手续费]={self.getCfgValue('server', 'trader_tax_rate')}, [印花税]={self.getCfgValue('server', 'stamp_tax_rate')}")
        logger.info(f"[tick_time]={self.getCfgValue('server', 'tick_time')}")

    def initPbrcsConfig(self):
        pbrcs = self.pf.keys()
        for pbrc in pbrcs:
            if pbrc != "DEFAULT":
                self.risk_mgrs[pbrc] = RiskManager(
                    self.getCfgValue('reader', 'mid_dir'), self.pf[pbrc]['log_dir'], f'final_{pbrc}.csv',
                    f'mid_{pbrc}.csv', self.pf[pbrc]['name_to_account'], pbrc, self.getCfgValue("server", "trader_tax_rate", 0.0003),
                    self.getCfgValue("server", "stamp_tax_rate")
                )
                logger.info(f"添加解析数据文件:[{pbrc}]{self.pf[pbrc]['log_dir']}")

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

    def getData(self):
        data = {}
        for key in self.risk_mgrs:
            if self.risk_mgrs[key].status is None:
                data[key] = {}
                data[key]["main"] = []
                data[key]["detail"] = []
                continue
            tmp1 = self.risk_mgrs[key].status
            # tmp2, _ = self.risk_mgrs[key].get_current_status3()
            # for i, human in enumerate(tmp2):
            #     tmp1['main'][i][1] = human[1]
            data[key] = tmp1
        return {'data': data}

    def __is_float(self, _s):
        try:
            float(str(_s))
            return True
        except:
            return False

    def tick(self):
        for risk_mgr in self.risk_mgrs.values():
            risk_mgr.renew_status()
            risk_mgr.get_current_status2()

    def syncData(self):
        self.rpc_queue.push_msg(0, RpcMessage("syncData", self.getClientList(), [], self.getData()))