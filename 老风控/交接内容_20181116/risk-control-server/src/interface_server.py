import socket
import socketserver


HOST, PORT = '0.0.0.0', 19190


class InterfaceHandler(socketserver.BaseRequestHandler):

    def handle(self):
        self.data = self.request.recv(1024).strip()
        print("{} write: {}".format(self.client_address[0], self.data))
        self.request.sendall(self.data.upper())


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(1)

    while True:
        conn, addr = s.accept()
        print("Connected with {}".format(addr))
        while True:
            data = conn.recv(1024)
            if not data:
                break
            print("received [{}]".format(repr(data)))
            reply = repr(data)
            conn.sendall(reply.encode('utf-8'))


if __name__ == '__main__':
    #server = socketserver.TCPServer((HOST, PORT), InterfaceHandler)
    #server.serve_forever()
    main()

