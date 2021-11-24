
class WORKER_STATE(object):
    INIT = 0
    CONNECTING = 1
    RUNNING = 2
    DISCONNECTED = -1

    state_map = {
        INIT: [CONNECTING], CONNECTING: [RUNNING, DISCONNECTED], RUNNING: [CONNECTING, DISCONNECTED],
        DISCONNECTED: []
    }

    @classmethod
    def checkCanStateTransmit(cls, now_state: int, new_state: int) -> bool:
        return new_state in cls.state_map[now_state]
