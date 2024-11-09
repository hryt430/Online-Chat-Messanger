import socket
import time

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_address = "0.0.0.0"
server_port = 9001
print("starting up on {}".format(server_port))

sock.bind((server_address, server_port))
clients= {}

while True:
    sock_client, sock_address = sock.accept()
    print("\nwaiting to receive message")
    fulldata = sock_client.recv(4096)

    username_length = int.from_bytes(fulldata[:1], "big")
    message_length = int.from_bytes(fulldata[1:4], "big")

    print('Received header from client. Byte lengths: User length {}, Message length {}'.format(username_length, message_length))

    username = fulldata[4:4 + username_length].decode()
    message = fulldata[4 + username_length: 4 + username_length + message_length].decode()

    clients["username"] = [sock_client, sock_address, time.time()]

    print("Username: {}".format(username))
    print("Message: {}".format(message))

    

    for key, value in list(clients.items()):
        sock.sendto(message.encode(), value[1])

        if time.time() - value[2] >= 10:
            message = "disconnection "
            sock.send(message.encode(), value[1])
            value[0].close()
            del clients[key]












