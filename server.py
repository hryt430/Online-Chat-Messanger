import socket
import time
import threading
import json

# グローバル変数の宣言
chat_rooms = {} #"roomid"{"hostip:", "password":},client:{ip_address:{}, }
server_address = "127.0.0.1"
server_tcp_port = 9001
server_udp_port = 9002

# TCP通信
def start_tcp_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((server_address, server_tcp_port))
    server_sock.listen(5)

    while True:
        client_sock, addr = server_sock.accept()
        client_address = addr[0]
        try:
            # ヘッダーを受け取る
            header = client_sock.recv(32)
            room_name_size = int.from_bytes(header[:1], "big")
            operation = int.from_bytes(header[1:2], "big")
            state = int.from_bytes(header[2:3], "big")
            payload_size = int.from_bytes(header[3:32].lstrip(b'\x00'), "big")

            # ボディを受け取る
            body = client_sock.recv(room_name_size + payload_size)
            room_name = body[:room_name_size].decode()
            payload_json = body[room_name_size:].decode()
            payload = json.loads(payload_json)

            # 操作によってチャットルームを作るか参加させる
            if operation == 1:
                room_creation(client_sock, client_address, room_name, payload)
            if operation == 2:
                room_join(client_sock, client_address, room_name, payload)
        
        except Exception as e:
            print(f"Error: {e}")

        finally:
            client_sock.close()

def room_creation(sock, sock_address, room_name, payload):
    # ルーム名に被りがないか確認
    if room_name in chat_rooms:
        response = {"status": "Error", "message_id": 2}
        send_tcp_response(sock, room_name, 1, 1, response)
        return

    username = payload["username"]
    password = payload["password"]

    # ルームを作成
    chat_rooms[room_name] = {
                            "host_ip": sock_address, 
                            "password": password,
                            "clients":{sock_address: [username, 0, None]}
                            }

    response = {"status": "Success", "message_id": 2, "token": sock_address}
    send_tcp_response(sock, room_name, 1, 2, response)
    print(f"チャットルーム{room_name}を作成されました！")

def room_join(sock_client, sock_address, room_name, payload):
    # ルーム名が間違ってないか確認
    if not room_name in chat_rooms:
        response = {"status": "Error", "message_id": 1}
        send_tcp_response(sock_client, room_name, 2, 1, response)
        return
    
    username = payload["username"]
    password = payload["password"]

    # パスワードがあっているか確認
    if chat_rooms[room_name]["password"] != password:
        response = {"status": "Error", "message_id": 3}
        send_tcp_response(sock_client, room_name, 2, 1, response)
        return
    
    # ユーザーを追加
    chat_rooms[room_name]["clients"][sock_address] = [username, 0, None]
    response = {"status": "Success", "message_id": 1, "token": sock_address}
    send_tcp_response(sock_client, room_name, 2, 2, response)
    print(f"{username}がチャットルーム{room_name}に参加します！")

def send_tcp_response(sock_client, room_name, operation, state, payload):
    # エンコード
    room_name_bytes = room_name.encode()
    payload_json = json.dumps(payload)
    payload_bytes = payload_json.encode()

    # バイトサイズ
    room_name_size = len(room_name_bytes)
    payload_size = len(payload_bytes)

    header = room_name_size.to_bytes(1, "big") + operation.to_bytes(1,"big") + state.to_bytes(1, "big") + payload_size.to_bytes(29, "big")
    sock_client.sendall(header + room_name_bytes + payload_bytes)

# UDPで接続
def start_udp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((server_address, server_udp_port))

    # タイムアウトを管理
    monitor_thread = threading.Thread(target=monitor_inactive_clients, args = (sock,), daemon=True)
    monitor_thread.start()

    while True:
        try:
            data, address = sock.recvfrom(4096)
            client_address = address[0]

            # ヘッダーを受け取る
            header = data[:2]
            room_name_size = int.from_bytes(header[:1], "big")
            token_size = int.from_bytes(header[1:2], "big")

            # ボディを受け取る
            body = data[2:]
            room_name = body[:room_name_size].decode()
            token = body[room_name_size:room_name_size + token_size].decode()
            message = body[room_name_size + token_size:].lstrip(b"\x00").decode()

            username = chat_rooms[room_name]["clients"][client_address][0]
            chat_rooms[room_name]["clients"][client_address][2] = address

            # ユーザー検証を行う
            if not validate_user(room_name, client_address, token):
                response_id = "1"
                send_udp_response(sock, address, room_name, token, response_id)
                continue
            
            if message == "/exit":        
                # ホストが切断した場合、ルームを閉じる
                if client_address == chat_rooms[room_name]["host_ip"]:
                    print(f"{username}が退出しました")
                    # 他のクライアントにルームが閉じられたことを通知
                    response_id = "2"
                    for addr, info in list(chat_rooms[room_name]["clients"].items()):
                        send_udp_response(sock, info[2], room_name, token, response_id)

                    # ルームを削除
                    del chat_rooms[room_name]
                    print(f"ホストが退出したため、チャットルーム{room_name}が閉じられました。")
                    continue

                else:
                    message = f"{username}が退出しました"
                    print(message)
                    response_id = "3"
                    send_udp_response(sock, address, room_name, token, response_id)
                    for addr, info in list(chat_rooms[room_name]["clients"].items()):
                        if client_address != addr:
                            send_udp_response(sock, info[2], room_name, token, message)
                    del chat_rooms[room_name]["clients"][client_address]

            else:
                print(message)
                # ユーザーの最新投稿時間を更新する
                chat_rooms[room_name]["clients"][client_address][1] = time.time()

                # 送り主以外の人にリレーする
                for addr, info in list(chat_rooms[room_name]["clients"].items()):
                    if addr != client_address:
                        send_udp_response(sock, address, room_name, token, message)

        except Exception as e:
            print(f"ERROR: {e}")

            # ホストが切断された場合にルームを閉じる処理を呼ぶ
            if client_address == chat_rooms[room_name]["host_ip"]:
                # ルームが閉じられたことを通知
                response_id = "2"
                for addr, info in list(chat_rooms[room_name]["clients"].items()):
                    send_udp_response(sock, addr, room_name, token, response_id)

                # ルームを削除
                del chat_rooms[room_name]
                print(f"チャットルーム{room_name}が閉じられました。")
                continue

            # 接続が切れた場合、クライアント情報を削除する
            message = f"{username}が退出しました"
            print(message)
            response_id = "3"
            send_udp_response(sock, address, room_name, token, response_id)
            for addr, info in list(chat_rooms[room_name]["clients"].items()):
                if client_address != addr:
                    send_udp_response(sock, info[2], room_name, token, message)

            del chat_rooms[room_name]["clients"][client_address]

def monitor_inactive_clients(sock):
    while True:
        for room_name, room_info in chat_rooms.items():
            for addr, info in list(room_info["clients"].items()):
                if time.time() - info[1] >= 180:  # 3分以上経過
                    response_id = "4"
                    send_udp_response(sock, info[2], room_name, addr, response_id)
                    del chat_rooms[room_name]["clients"][addr]
                    print(f"{info[0]}がタイムアウトで退出しました")
        time.sleep(10)  # 10秒ごとにチェック

# ユーザーがルームに入れるか検証
def validate_user(room_name, address, token):
    return token in chat_rooms[room_name]["clients"]

def send_udp_response(sock, address, room_name, token, message):
    # 最大4096バイトのメッセージを送れる
    MAX_BYTES = 4096

    # エンコード
    room_name_bytes = room_name.encode()
    token_bytes = token.encode()
    message_bytes = message.encode()

    # バイトサイズ
    room_name_size = len(room_name_bytes)
    token_size = len(token_bytes)
    message_size = len(message_bytes)

    header = room_name_size.to_bytes(1, "big") + token_size.to_bytes(1, "big")

    # 合計が4096バイトになるように調整
    total_size = len(header) + room_name_size + token_size + message_size

    if total_size < MAX_BYTES:
        padding_size = MAX_BYTES - total_size
        padding = b"\x00" * padding_size
    else:
        raise ValueError("メッセージのサイズが4096バイトを超えています")

    sock.sendto(header + room_name_bytes + token_bytes + padding + message_bytes , address)

# 並列処理の設定
def main():
    tcp_thread = threading.Thread(target=start_tcp_server)
    udp_thread = threading.Thread(target=start_udp_server)

    tcp_thread.daemon = True
    udp_thread.daemon = True

    tcp_thread.start()
    udp_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("サーバを終了します...")

if __name__ == "__main__":
    main()

  





        












