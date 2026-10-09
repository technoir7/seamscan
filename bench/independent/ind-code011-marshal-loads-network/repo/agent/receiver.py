import marshal
import socket


def receive(conn: socket.socket):
    data = conn.recv(65536)
    return marshal.loads(data)
