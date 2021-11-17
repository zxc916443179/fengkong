from threading import Thread

from common_server.data_module import DataCenter
from common.message_queue_module import MsgQueue, Message
from common.rpc_queue_module import RpcQueue, RpcMessage
from gameEntity import RPCError

import logging

from setting import keyType

logger = logging.getLogger()


def req(allow_permissions=None):
    def decorator(func):
        func.__exposed__ = True
        func.__allow_permissions__ = allow_permissions
        return func

    return decorator


class MsgHandler(Thread):
    def __init__(self):
        super(MsgHandler, self).__init__()
        self.state = 0
        self.msg_queue = MsgQueue()
        self.rpc_queue = RpcQueue()
        self.data_center = DataCenter()

    def run(self):
        while self.state == 0:
            msg = self.msg_queue.pop_msg()
            if msg is not None:
                self.handleMessage(msg)

    def handleMessage(self, msg):
        # type: (Message) -> None
        func = getattr(self, msg.method, None)
        if func is not None:
            if getattr(func, "__exposed__", False):
                allow_permissions = getattr(func, "__allow_permissions__", None)
                if allow_permissions is None or msg.permission in allow_permissions:
                    try:
                        func(msg)
                    except Exception as e:
                        if type(e) is RPCError:
                            ret = {"code": e.code, "msg": e.description}
                        else:
                            ret = {"code": 100}
                        self.rpc_queue.push_msg(0, RpcMessage("PlayerSyncHandler/Exception", [msg.client_id], [], ret))
                        logger.error("%s" % e.message, exc_info=True)
                else:
                    logger.error("invalid rpc call, permission denied: %s" % msg.method)
            else:
                logger.error("invalid rpc call, unreachable: %s" % msg.method)
        else:
            logger.error("not implement: %s" % msg.method)

    @req()
    def heartBeat(self, msg: Message) -> None:
        logger.debug("heart beat from client")
    
    @req()
    def closeClient(self, msg: Message) -> None:
        client = self.data_center.getClient(msg.client_id)
        client.setState(keyType.CLIENT_STATE.DEAD)