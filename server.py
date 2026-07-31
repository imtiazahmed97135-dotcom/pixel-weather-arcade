import socket
import threading
import json
import random
import os

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 10000))

PLAYER_PALETTES = [
    (0, 240, 255),    # Cyan
    (255, 140, 0),    # Bright Orange
    (40, 230, 110),   # Neon Green
    (200, 80, 255),   # Purple
    (255, 220, 0),    # Yellow
    (255, 70, 130),   # Pink
    (0, 180, 255)     # Sky Blue
]

clients = {}
player_colors = {}
client_counter = 0

# Initial pool of 20 active coins across the world map
TOTAL_COINS = 20
coins = [
    {"id": i, "x": random.randint(300, 2900), "y": random.choice([920, 800, 680, 540])}
    for i in range(TOTAL_COINS)
]

def handle_client(conn, addr, player_id):
    global coins
    print(f"[NEW CONNECTION] Player {player_id} connected from {addr}.")
    
    color = PLAYER_PALETTES[player_id % len(PLAYER_PALETTES)]
    player_colors[player_id] = color
    
    conn.send(json.dumps({"id": player_id, "color": color}).encode())

    while True:
        try:
            data = conn.recv(2048).decode()
            if not data:
                break

            p_info = json.loads(data)
            p_info["color"] = color
            clients[player_id] = p_info

            # Check if player collected a specific coin ID
            collected_id = p_info.get("collected_coin_id")
            if collected_id is not None:
                # Respawn only the collected coin at a new position
                for c in coins:
                    if c["id"] == collected_id:
                        c["x"] = random.randint(300, 2900)
                        c["y"] = random.choice([920, 800, 680, 540])
                        break

            response = {
                "players": clients,
                "coins": coins
            }
            conn.send(json.dumps(response).encode())

        except Exception:
            break

    print(f"[DISCONNECTED] Player {player_id} left.")
    if player_id in clients:
        del clients[player_id]
    if player_id in player_colors:
        del player_colors[player_id]
    conn.close()


def start_server():
    global client_counter
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVER STARTED] Listening on {HOST}:{PORT}...")

    while True:
        conn, addr = server.accept()
        client_counter += 1
        thread = threading.Thread(target=handle_client, args=(conn, addr, client_counter))
        thread.start()

if __name__ == "__main__":
    start_server()