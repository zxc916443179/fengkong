
import threading
from common import conf
from common.common_library_module import PriorityQueue, Singleton
from typing import Tuple, Dict, Any


"""
Class : MsgQueue
author: Tolki
@description:this is a message queue,which is multi-thread safety
@there will be only one msg queue instance in global environment
@:this class is designed as multi-producer and multi-consumer model
"""
# msg struct: [method: str, hid: int, args: [], kwargs: {}]


@Singleton
class MsgQueue(object):    
    def __init__(self):
        super(MsgQueue,self).__init__()
        self._queue = PriorityQueue()
        self._cond = threading.Condition(threading.Lock())
        self._count = 0

    # commonly,ret is (fd,data)
    def pop_msg(self):
        # type: () -> Message
        ret = None
        self._cond.acquire()
        
        if self._queue.size() <= 0:
            self._cond.wait(0.01)
        
        if self._queue.size() > 0:
            ret = self._queue.pop()
            self._count = self._count - 1

        self._cond.release()
        return ret

    def push_msg(self,priority,item):
        ret = 0
        self._cond.acquire()
        
        if self._count > conf.INPUT_QUEUE_MAX_COUNT:
            ret = -1
        else:
            self._queue.push(priority,item)
            self._count = self._count + 1

        self._cond.notify_all()
        self._cond.release()
        return ret


class Message(object):
    def __init__(self, method, client_id, args, kwargs, permission=""):
        # type: (str, int, Tuple[object,...], Dict[str, Any], str) -> None
        self.method = method
        self.client_id = client_id
        self.args = args
        self.kwargs = kwargs
        self.permission = permission
    
    def __eq__(self, o: object) -> bool:
        return self.client_id == o.client_id

    def __le__(self, o: object) -> bool:
        return self.client_id <= o.client_id
