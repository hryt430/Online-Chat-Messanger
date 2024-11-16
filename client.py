import socket
import json
import sys
from struct import pack, unpack

def protcol_UDP(username_length, data_length):
    return username_length.to_bytes(1, "big") + data_length.to_bytes(3, "big")

def protcol_TCP(roomname_length, operation_length, state_length, payload_length):
    return roomname_length.to_bytes(1, "big") + operation_length.to_bytes(1, "big") + state_length.to_bytes(1, "big") + payload_length.to_bytes(29, "big")

def start_udp_connection():
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
    header = protcol_UDP(len(username), len(message))

    data = header + username.encode() + message.encode()

    sent= sock.sendto(data, (server_adress, server_port))
    print("Send {} bytes".format(sent))

    # print("waitng to receive")
    # data, server = sock.recvfrom(4096)
    # print("received {!r}".format(data))

finally:
    print("closing socket")
    sock.close()

    
# TCPで接続する
def start_tcp_connection(server_address, server_port, room_name, operation, username, password):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("conecting {}".format(server_address, server_port))
    # サーバーと接続する
    try:
        sock.connect(server_address, server_port)

    except Exception as e:
        print(f"ERROR : {e}")
        sys.exit(1)

    try:
        # ヘッダーを送信する
        send_tcp_request(sock, room_name, operation, 0, username, password)

        # ヘッダーを受け取る
        header = sock.recv(32)
        room_name_size, operation, state, payload_size = unpack("!BBB29s", header)
        payload_size = int(payload_size.decode().strip("\x00"))

        # ボディーを受け取る
        body = sock.recv(room_name_size + payload_size).decode()
        room_name = body[:room_name_size]
        payload = body[room_name_size:]

        # 状態１の場合（エラー）
        if payload["status"] == "Error":
            print(payload["message"])
        # 状態２の場合（成功）
        if payload["status"] == "Success":
            token = payload["token"]
            print(payload["message"])

        return token
    
    finally:
        print("チャットルームに移動します")
        sock.close()

def handle_chatroom():
    # 操作を選ぶ
    while True:
        print("1: チャットルームを作成する")
        print("2: チャットルームに参加する")
        operation = int((input("操作を選択してください(1 または 2) :")))
        if operation == 1 or operation == 2:
            break
        else:
            print("無効な入力です。もう１度入力してください")

    # 名前とパスワードを入力
    username = input("ユーザー名を入力してください :")
    room_name = input("ルーム名を入力してください :")
    password = input("パスワードを決めてください (パスワードが不要の場合は空のままにしてください) :")

    token = start_tcp_connection(server_address, server_port, room_name, operation, username, password)
    print(f"トークンを受け取りました{token}")
    return token

def send_tcp_request(sock_client, room_name, operation, state, username, password):
    payload = {"username": username, "password": password}
    room_name_bytes = room_name.encode()
    payload_bytes = payload.encode()
    room_name_size = len(room_name_bytes)
    payload_size = len(payload_bytes)
    header = pack("!BBB29s", room_name_size, operation, state, payload_size)
    sock_client.sendall(header + room_name_bytes + payload_bytes)


