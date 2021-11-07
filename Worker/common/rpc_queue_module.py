import threading
from common import conf
from common.common_library_module import PriorityQueue, Singleton
from typing import List, Dict, Tuple

"""
Class : MsgQueue
author: Tolki
@description:this is a message queue,which is multi-thread safety
@there will be only one msg queue instance in global environment
@:this class is designed as multi-producer and multi-consumer model
"""


# rpc struct: [method: str, targets: [], args: [], kwargs: {}]


@Singleton
class RpcQueue(object):
    def __init__(self):
        super(RpcQueue, self).__init__()
        self._queue = PriorityQueue()
        self._cond = threading.Condition(threading.Lock())
        self._count = 0

    # commonly,ret is (fd,data)
    def pop_msg(self):
        # type: () -> RpcMessage
        ret = None
        self._cond.acquire()

        if self._queue.size() > 0:
            ret = self._queue.pop()
            self._count = self._count - 1

        self._cond.release()
        return ret

    def push_msg(self, priority, item):
        # type: (int, RpcMessage) -> int
        ret = 0
        self._cond.acquire()

        if self._count > conf.INPUT_QUEUE_MAX_COUNT:
            ret = -1
        else:
            self._queue.push(priority, item)
            self._count = self._count + 1

        self._cond.notify_all()
        self._cond.release()
        return ret

    def __len__(self):
        return self._count


class RpcMessage(object):
    def __init__(self, method, targets, args, kwargs):
        # type: (str, List[int], List[object], Dict) -> None
        self.method = method
        self.targets = targets
        self.args = args
        self.kwargs = kwargs

    def parseMsg(self):
        # type: () -> Tuple[str, List[int], List[object], Dict]
        return self.method, self.targets, self.args, self.kwargs

    def __eq__(self, o: object) -> bool:
        return len(self.targets) == len(o.targets)

    def __le__(self, o: object) -> bool:
        return len(self.targets) <= len(o.targets)
