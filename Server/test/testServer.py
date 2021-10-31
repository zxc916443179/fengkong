# -*- coding: GBK -*-
import unittest
import sys
import cPickle
import time


sys.path.append('.')
sys.path.append('./common')
sys.path.append('./network')
sys.path.append('./common_server')
from simpleServer import SimpleServer

from network.netStream import NetStream
import time
from common.message_queue_module import MsgQueue
from common import conf
import json
class TestServer():
    def __init__(self):
        self.server = SimpleServer()
    
    def test_Server(self):
        self.server.startup()

        sock = NetStream()
        sock.connect('127.0.0.1', 2000)
        sock.nodelay(1)
        stat = 0
        msg_queue = MsgQueue()

        while 1:
            time.sleep(0.1)
            sock.process()
            
            if stat == 1:
                break
            if stat == 0:
                if sock.status() == conf.NET_STATE_ESTABLISHED:
                    stat = 1
                    info = {
                        "method": "test", "args": [], "kwargs": {}
                    }
                    sock.send(json.dumps(info))
                    last = time.time()

            self.server.tick()
            time.sleep(0.01)
            self.server.tick()
            
        assert len(msg_queue) == 1

if __name__ == "__main__":
    TestServer().test_Server()
