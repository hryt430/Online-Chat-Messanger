import socket
import time
import threading
import json
from struct import pack, unpack

chat_rooms = {} #"roomid"{"hostip:", "password":},client:{"username":, }

def start_udp_server():
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

def udp_message():


    return


# TCP通信でチャットを作るか参加させる（常時起動させる？）
def start_tcp_serer():
    # TCPで接続する
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = "0.0.0.0"
    server_port = 9002

    print('Starting up on {} port {}'.format(server_address, server_port))

    # 次に、サーバは bind()関数を使用して、ソケットをサーバのアドレスとポートに紐付けします。その後、listen()関数を呼び出すことで、サーバは着信接続の待ち受けを開始します。サーバは一度に最大1つの接続を受け入れることができます。
    sock.bind((server_address, server_port))

    sock.listen(1)

    while True:
        sock_client, sock_address = sock.accept()
        print("\nwaiting to receive response")

        try:
            # ヘッダーを受け取る
            header = sock_client.recv(32)
            room_name_size, operation, state, payload_size = unpack("!BBB29s", header)
            payload_size = int(payload_size.decode().strip("\x00"))

            # ボディを受け取る
            body = sock_client.recv(room_name_size + payload_size).decode()
            room_name = body[:room_name_size]
            payload = json.loads(body[room_name_size:])

            if operation == 1:
                room_creation(room_name, payload)
            if operation == 2:
                room_join(room_name, payload)
        
        except Exception as e:
            print(f"Error: {e}")

        finally:
            sock_client.close()

def room_creation(sock_client, sock_address, room_name, payload):
    # 名前に被りがないか確認
    if chat_rooms[room_name]:
        response = {"status": "Error", "message": "ルームがすでに存在しています"}
        send_tcp_reponse(sock_client, room_name, 1, 1, response)
        return

    username = payload["username"]
    password = payload["password"]

    # ルームを作成
    chat_rooms[room_name] = {
                            "host_ip": sock_address, 
                            "password": password,
                            "clients":{username: sock_address}
                            }

    response = {"status": "Ok", "message": "ルームが作成されました！", "token": sock_address}
    send_tcp_reponse(sock_client, room_name, 1, 2, response)
    print(f"チャットルーム{room_name}を作成しました！")

def room_join(sock_client, sock_address, room_name, payload):
    # ルーム名が間違ってないか確認
    if not chat_rooms[room_name]:
        response = {"status": "Error", "message": "ルームが存在しません"}
        send_tcp_reponse(sock_client, room_name, 2, 1, response)
        return
    
    username = payload["username"]
    passoword = payload["password"]

    # パスワードがあっているか確認
    if chat_rooms[room_name]["password"] != passoword:
        response = {"status": "Error", "message": "パスワードが違います"}
        send_tcp_reponse(sock_client, room_name, 2, 1, response)
        return
    
    # ユーザーを追加
    chat_rooms[room_name]["clients"][username] = sock_address
    response = {"status": "Success", "message": "ルームに参加します", "token": sock_address}
    send_tcp_reponse(sock_client, room_name, 2, 2, response)
    print(f"{username}がチャットルーム{room_name}に参加します！")

def send_tcp_reponse(sock_client, room_name, operation, state, payload):
    room_name_bytes = room_name.encode()
    payload_bytes = json.dumps(payload).encode()
    room_name_size = len(room_name_bytes)
    payload_size = len(payload_bytes)
    header = pack("!BBB29s", room_name_size, operation, state, payload_size)
    sock_client.sendall(header + room_name_bytes + payload_bytes)





        












