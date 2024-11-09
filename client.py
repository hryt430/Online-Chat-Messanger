import socket

def protcol_header(username_length, data_length):
    return username_length.to_bytes(1, "big") + data_length.to_bytes(3, "big")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# いらなくなりそう？チャットルームとの接続
server_adress = input("Type in the server's address to connect to: ")
server_port = 9001

adress = ""
port = 9050
# message = input("Type in the message you want to send to others ").encode()


sock.bind((adress, port))


try:
    username = input("Type in your name ")
    message = input("Type in the message you want to send to others ")
    header = protcol_header(len(username), len(message))

    data = header + username.encode() + message.encode()

    sent= sock.sendto(data, (server_adress, server_port))
    print("Send {} bytes".format(sent))

    # print("waitng to receive")
    # data, server = sock.recvfrom(4096)
    # print("received {!r}".format(data))

finally:
    print("closing socket")
    sock.close()
