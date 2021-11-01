# =========================================================================
#
# NOTE: We use 4 bytes little endian (x86) by default.
# If you choose a different endian, you may have to modify header length.
#
# =========================================================================

from common import conf
import errno
import socket
import struct
import json
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from gameEntity import GameEntity
logger = logging.getLogger()


class RpcProxy(object):
    def __init__(self, owner, netstream):
        # type: (GameEntity, NetStream) -> None
        self.owner = owner
        self.netstream = netstream

    def close(self):
        self.owner = None
        self.netstream = None

    def __getitem__(self, name):
        def call(_self, *args, **kwargs):
            # not support key-value pairs
            _self.owner.packet_no += 1
            kwargs["Packet_Number"] = _self.owner.packet_no
            if not kwargs.__contains__("code"):
                kwargs["code"] = 0
            if not kwargs.__contains__("msg"):
                kwargs["msg"] = conf.RET_CODE_MAP[kwargs["code"]]
            info = {
                'method': name,
                'args': args,
                'kwargs': kwargs,
                'code': 0
            }
            # logger.info("_packet_no %d" % _self.owner.packet_no, "info %s" % info)
            _self.netstream and _self.netstream.send(json.dumps(info))

        setattr(RpcProxy, name, call)
        return getattr(self, name)

    def parse_rpc(self, data):
        info = json.loads(data)
        method = info.get('method', None)

        if method is None:
            return
        func = getattr(self.owner, "call", None)
        if func:
            if getattr(func, '__exposed__', False):
                func(method, *info['args'], **info['kwargs'])
            else:
                print('invalid rpc call, NOT PERMITTED:', method)
        else:
            print('invalid rpc call, NOT EXIST:', method)


class NetStream(object):
    def __init__(self):
        super(NetStream, self).__init__()

        self.sock = None  # socket object
        self.send_buf = b''  # send buffer
        self.recv_buf = b''  # recv buffer

        self.state = conf.NET_STATE_STOP
        self.errd = (errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK)
        self.conn = (errno.EISCONN, 10057, 10053)
        self.errc = 0
        self.hid = 0

        return

    def status(self):
        return self.state

    # connect the remote server
    def connect(self, address, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.sock.connect_ex((address, port))
        self.state = conf.NET_STATE_CONNECTING
        self.send_buf = b''
        self.recv_buf = b''
        self.errc = 0

        return 0

    # close connection
    def close(self):
        self.state = conf.NET_STATE_STOP

        if not self.sock:
            return 0
        try:
            self.sock.close()
        except:
            pass  # should logging here

        self.sock = None

        return 0

    # assign a socket to netstream
    def assign(self, sock):
        self.close()
        self.sock = sock
        self.sock.setblocking(0)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.state = conf.NET_STATE_ESTABLISHED
        self.nodelay(1)

        self.send_buf = b''
        self.recv_buf = b''

        return 0

    # set tcp nodelay flag
    def nodelay(self, nodelay=0):
        if 'TCP_NODELAY' not in socket.__dict__:
            return -1
        if self.state != 2:
            return -2
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, nodelay)

        return 0

    # update
    def process(self):
        if self.state == conf.NET_STATE_STOP:
            return 0
        if self.state == conf.NET_STATE_CONNECTING:
            self.__tryConnect()
        if self.state == conf.NET_STATE_ESTABLISHED:
            self.__tryRecv()
        if self.state == conf.NET_STATE_ESTABLISHED:
            self.__trySend()

        return 0

    def __tryConnect(self):
        if self.state == conf.NET_STATE_ESTABLISHED:
            return 1
        if self.state != conf.NET_STATE_CONNECTING:
            return -1
        try:
            self.sock.recv(0)
        except socket.error as error:
            code, _ = error.errno, error.strerror
            if code in self.conn:
                return 0
            if code in self.errd:
                self.state = conf.NET_STATE_ESTABLISHED
                self.recv_buf = b''
                logger.info("success connect to gate server")
                return 1

            self.close()
            return -1

        self.state = conf.NET_STATE_ESTABLISHED
        logger.info("success connect to gate server")
        return 1

    # append data into send_buf with a size header
    def send(self, data):
        size = len(data) + conf.NET_HEAD_LENGTH_SIZE
        wsize = struct.pack(conf.NET_HEAD_LENGTH_FORMAT, size)
        self.__sendRaw(wsize + str.encode(data))

        return 0

    # append data to send_buf then try to send it out (__try_send)
    def __sendRaw(self, data):
        self.send_buf = self.send_buf + data
        self.process()

        return 0

    # send data from send_buf until block (reached system buffer limit)
    def __trySend(self):
        wsize = 0
        if len(self.send_buf) == 0:
            return 0

        try:
            # print "self.send_buf",self.send_buf
            wsize = self.sock.send(self.send_buf)
        
        except socket.error as error:
            code, _ = error.errno, error.strerror
            if code not in self.errd:
                self.errc = code
                self.close()

                return -1

        self.send_buf = self.send_buf[wsize:]
        return wsize

    # recv an entire message from recv_buf
    def recv(self):
        rsize = self.__peekRaw(conf.NET_HEAD_LENGTH_SIZE)
        if len(rsize) < conf.NET_HEAD_LENGTH_SIZE:
            return ''

        size = struct.unpack(conf.NET_HEAD_LENGTH_FORMAT, rsize)[0]
        if len(self.recv_buf) < size:
            return ''

        self.__recvRaw(conf.NET_HEAD_LENGTH_SIZE)

        return self.__recvRaw(size - conf.NET_HEAD_LENGTH_SIZE)

    # try to receive all the data into recv_buf
    def __tryRecv(self):
        rdata = b''
        while 1:
            text = b''
            try:
                text = self.sock.recv(1024)
                if not text:
                    self.errc = 10000
                    self.close()

                    return -1
            
            except socket.error as error:
                code, _ = error.errno, error.strerror
                if code not in self.errd:
                    self.errc = code
                    self.close()
                    return -1
            if text == b'':
                break

            rdata = rdata + text

        self.recv_buf = self.recv_buf + rdata
        return len(rdata)

    # peek data from recv_buf (read without delete it)
    def __peekRaw(self, size):
        self.process()
        if len(self.recv_buf) == 0:
            return b''

        if size > len(self.recv_buf):
            size = len(self.recv_buf)
        rdata = self.recv_buf[0:size]

        return rdata

    # read data from recv_buf (read and delete it from recv_buf)
    def __recvRaw(self, size):
        rdata = self.__peekRaw(size)
        size = len(rdata)
        self.recv_buf = self.recv_buf[size:]

        return rdata.decode()
