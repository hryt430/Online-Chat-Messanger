import socket
import json
import sys
import threading

# グローバル変数の宣言
server_address = "127.0.0.1"
server_tcp_port = 9001
server_udp_port = 9002
client_address = "0.0.0.0"
client_port = 9050

def handle_chatroom(server_address, server_port):
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
    room_name = input("ルーム名を入力してください : ")
    username = input("ユーザー名を入力してください : ")
    password = input("パスワードを決めてください (パスワードが不要の場合は空のままにしてください) : ")

    token = start_tcp_connection(server_address, server_port, room_name, operation, username, password)
    return token, room_name, username

# TCPで接続する
def start_tcp_connection(server_address, server_port, room_name, operation, username, password):
    client_tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("{} に接続しています".format(server_address))

    # サーバーと接続する
    try:
        client_tcp_sock.connect((server_address, server_tcp_port))

    except Exception as e:
        print(f"ERROR : {e}")
        sys.exit(1)

    try:
        # リクエストを送信する
        send_tcp_request(client_tcp_sock, room_name, operation, 0, username, password)

        # ヘッダーを受信
        header = client_tcp_sock.recv(32)
        room_name_size = int.from_bytes(header[:1], "big")
        operation = int.from_bytes(header[1:2], "big")
        state = int.from_bytes(header[2:3], "big")
        payload_size = int.from_bytes(header[3:32].lstrip(b'\x00'), "big")

        # ボディを受け取る
        body = client_tcp_sock.recv(room_name_size + payload_size)
        room_name = body[:room_name_size].decode()
        payload_json = body[room_name_size:].decode()
        payload = json.loads(payload_json)

        # 状態１の場合（エラー）
        if payload["status"] == "Error":
            if payload["message_id"] == 1:
                print("ルームが存在しません")
            elif payload["message_id"] == 2:
                print("ルームが既に存在します")
            elif payload["message_id"] == 3:
                print("パスワードが違います")

            print("\n操作をやり直します")
            handle_chatroom(server_address, server_port)
        
        # 状態２の場合（成功）
        if payload["status"] == "Success":
            if payload["message_id"] == 1:
                print("ルームに参加します！")
            elif payload["message_id"] == 2:
                print("ルームが作成されました！")
            
            token = payload["token"]

        return token
    
    except Exception as e:
        print(f"ERROR: {e}")

    finally:
        print("チャットルームに移動します。終了する場合は'/exit'入力してください")
        client_tcp_sock.close()

def send_tcp_request(sock, room_name, operation, state, username, password):
    payload = {"username": username, "password": password}
    # エンコード
    room_name_bytes = room_name.encode()
    payload_json = json.dumps(payload)
    payload_bytes = payload_json.encode()
    # バイトサイズ
    room_name_size = len(room_name_bytes)
    payload_size = len(payload_bytes)
    
    header = room_name_size.to_bytes(1, "big") + operation.to_bytes(1,"big") + state.to_bytes(1, "big") + payload_size.to_bytes(29, "big")
    sock.sendall(header + room_name_bytes + payload_bytes)

def udp_connection(client_udp_sock, room_name, token, username):
    # 初回にユーザーが参加したことを伝える
    join_message = f"{username}が{room_name}に参加しました！"
    send_udp_request(client_udp_sock, server_address, server_udp_port, room_name, token, join_message)

    try:
        while True:
            input_message = input(f"{username} : ")
            message = username + " : " + input_message
            if input_message == "/exit":
                send_udp_request(client_udp_sock, server_address, server_udp_port, room_name, token, input_message)
                break
            elif input_message == "":
                continue
            else:
                send_udp_request(client_udp_sock, server_address, server_udp_port, room_name, token, message)

    except Exception as e:
        print(f"ERROR: {e}")

def listen_response(sock):
    while True:
        try:
            data = sock.recv(4096)

            # ヘッダーを受け取る
            header = data[:2]
            room_name_size = int.from_bytes(header[:1], "big")
            token_size = int.from_bytes(header[1:2], "big")

            # ボディを受け取る
            body = data[2:]
            message = body[room_name_size + token_size:].lstrip(b"\x00").decode()

            if message in ["1", "2", "3", "4"]:
                if message == "1":
                    print("無効なユーザーです。退出します")
                elif message == "2":
                   print("ホストが退出したためチャットルームが閉じられました")    
                elif message == "3":
                    print(f"サーバーとの接続を切断しました")   
                elif message == "4":
                    print("タイムアウトのため退出します")
                break
            
            else:
                print(message)

        except Exception as e:
            print(f"ERROR: {e}")
        finally:
            sock.close()
            exit()

def send_udp_request(sock, server_address, server_port, room_name, token, message):
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

    sock.sendto(header + room_name_bytes + token_bytes + padding + message_bytes , (server_address, server_port))

def run_chat_client():
    try:
        token, room_name, username = handle_chatroom(server_address, server_tcp_port)

        client_udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_udp_sock.bind((client_address, client_port))

        udp_thread = threading.Thread(target=udp_connection, args=(client_udp_sock, room_name, token, username), daemon=True)
        udp_thread.start()

        listen_thread = threading.Thread(target=listen_response, args= (client_udp_sock,), daemon=True)
        listen_thread.start()

        udp_thread.join()
        listen_thread.join()

    except KeyboardInterrupt:
        print("接続を終了します...")

if __name__ == "__main__":
    run_chat_client()

