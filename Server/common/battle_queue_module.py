
import threading
from common import conf
from common.common_library_module import PriorityQueue, Singleton


@Singleton
class BattleMsgQueue(object):    
    def __init__(self):
        super(BattleMsgQueue, self).__init__()
        self._queue = PriorityQueue()
        self._cond = threading.Condition(threading.Lock())
        self._count = 0

    # commonly,ret is (fd,data)
    def pop_msg(self):
        # type: () -> BattleMessage
        ret = None
        self._cond.acquire()
        
        if self._queue.size() <= 0:
            self._cond.wait(0.01)
        
        if self._queue.size() > 0:
            ret = self._queue.pop()
            self._count = self._count - 1

        self._cond.release()
        return ret

    def push_msg(self, priority, item):
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

    @property
    def count(self):
        return self._count


class BattleMessage(object):
    def __init__(self, method, source, target, **kwargs):
        # entity type {}
        self.method = method
        self.source = source
        self.target = target
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    def __getattr__(self, item):
        return None
