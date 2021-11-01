from common.common_library_module import Singleton
from common.rpc_queue_module import RpcMessage
from setting import keyType
from common_server.timer import TimerManager
import logging
from typing import TYPE_CHECKING, List, Union, Dict, Tuple
import time
import numpy as np

if TYPE_CHECKING:
    from argparse import Namespace
logger = logging.getLogger()

class Client(object):
    idx = 0
    def __init__(self, hid) -> None:
        self.id = self.genId()
        self.hid = hid
        self.state = 0
    
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

    def setConfig(self, config):
        # type: (Namespace) -> None
        self.config = config

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
            self.clients.pop(client.hid)
            logger.info(f"remove dead client {client.hid}")
    
    def getClient(self, hid):
        return self.clients.get(hid)
    
    def getClientById(self, id: str) -> Client or None:
        clients = self.clients.values()
        for client in clients:
            if client.id == id:
                return client
        return None