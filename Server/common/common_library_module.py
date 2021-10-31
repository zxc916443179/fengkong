import heapq
import functools


class PriorityQueue:
    def __init__(self):
        self._queue = []

    def push(self, priority, item):
        heapq.heappush(self._queue, (priority, item))

    def pop(self):
        ret = heapq.heappop(self._queue)
        return ret[1]

    def size(self):
        return len(self._queue)


def Singleton(cls):
    _instance = {}
    cls._origin_new = cls.__new__
    cls._origin_init = cls.__init__

    @functools.wraps(cls.__new__)
    def _singleton_new(cls, *args, **kwargs):
        if cls not in _instance:
            sin_instance = cls._origin_new(cls, *args, **kwargs)
            sin_instance._origin_init(*args, **kwargs)
            _instance[cls] = sin_instance
        return _instance[cls]

    cls.__new__ = staticmethod(_singleton_new)
    cls.__init__ = lambda self, *args, **kwargs: None
    return cls
