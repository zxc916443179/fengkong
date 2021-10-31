# -*- coding: GBK -*-

from network.netStream import NetStream, RpcProxy
from common import conf
from common.message_queue_module import MsgQueue, Message
import logging

logger = logging.getLogger()


def EXPOSED(func):
    func.__exposed__ = True
    return func


class RPCError(Exception):
    def __init__(self, code, description=None):
        super(RPCError, self).__init__()
        self.code = code
        self.description = description
        if self.description is None:
            self.description = conf.RET_CODE_MAP[code]

        self.message = self.description


class GameEntity(object):
    EXPOSED_FUNC = {}

    def __init__(self, netstream):
        # type: (NetStream) -> None
        self.netstream = netstream
        self.caller = RpcProxy(self, netstream)
        self.stat = 0
        self.msg_queue = MsgQueue()
        self.packet_no = 0
        self.permission = ""

    def destroy(self):
        self.caller = None
        self.netstream = None

    @EXPOSED
    def call(self, method, *args, **kwargs):
        # print "recv message from client: ", self.netstream.hid, "method: ", method
        if method == "closeClient":
            logger.debug("recv close client")
            self.stat = -1
        if method == "login":
            if kwargs.__contains__("username") and kwargs["username"] == "admin" and kwargs["password"] == "gm36_root":
                self.permission = "admin"
                return
        self.msg_queue.push_msg(0, Message(method, self.netstream.hid, args, kwargs, self.permission))

    @EXPOSED
    def closeClient(self):
        logger.debug("client closed")
        self.stat = -1
        self.netstream.close()
