# -*- coding: GBK -*-

from common_server.msg_handler_module import MsgHandler

from common.message_queue_module import MsgQueue
import logging
logger = logging.getLogger()


class ThreadPool:
    def __init__(self):
        self.msg_queue = MsgQueue()
        self.thread_pool = [MsgHandler() for _ in xrange(10)]
        
    def tick(self, tick_time=0.02):
        pass

    def start(self):
        logger.debug("thread start")
        for thread in self.thread_pool:
            thread.start()

    def stop(self):
        for thread in self.thread_pool:
            thread.state = 1
