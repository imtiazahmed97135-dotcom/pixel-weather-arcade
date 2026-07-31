import json
import math
import random
import socket
import sys
import threading
import pygame

# Configuration
SCREEN_WIDTH = 1100
SCREEN_HEIGHT = 650
WORLD_WIDTH = 3200
WORLD_HEIGHT = 1200

# Colors
DARK_BG = (12, 15, 24)
CYAN = (0, 240, 255)
GOLD = (255, 215, 0)
GREEN = (40, 230, 110)
RED = (255, 60, 60)
WHITE = (255, 255, 255)
GREY = (140, 150, 170)


class NetworkClient:

  def __init__(self, host, port):
    self.host = host
    self.port = port
    self.socket = None
    self.connected = False
    self.player_id = None
    self.other_players = {}

  def connect(self):
    try:
      self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.socket.connect((self.host, self.port))
      self.connected = True

      # Start background thread to listen for server messages
      thread = threading.Thread(target=self.receive_data, daemon=True)
      thread.start()
      return True
    except Exception as e:
      print(f"[Network] Connection failed: {e}")
      self.connected = False
      return False

  def send(self, data):
    if self.connected and self.socket:
      try:
        msg = json.dumps(data) + "\n"
        self.socket.sendall(msg.encode("utf-8"))
      except Exception as e:
        print(f"[Network] Send error: {e}")
        self.connected = False

  def receive_data(self):
    buffer = ""
    while self.connected:
      try:
        chunk = self.socket.recv(4096).decode("utf-8")
        if not chunk:
          break
        buffer += chunk
        while "\n" in buffer:
          line, buffer = buffer.split("\n", 1)
          if line.strip():
            msg = json.loads(line)
            self.handle_message(msg)
      except Exception as e:
        print(f"[Network] Receive error: {e}")
        break
    self.connected = False

  def handle_message(self, msg):
    msg_type = msg.get("type")
    if msg_type == "welcome":
      self.player_id = msg.get("id")
    elif msg_type == "state_update":
      players = msg.get("players", [])
      self.other_players = {
          p["id"]: p for p in players if p["id"] != self.player_id
      }


def run_multiplayer_game(
    city_name, player_name, server_host, game_mode, api_key
):
  pygame.init()
  screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
  pygame.display.set_caption(f"WEATHER-PIXEL ARCADE - [{player_name}]")
  clock = pygame.time.Clock()

  # Network Setup
  # If server_host was passed as URL from dashboard, default to Railway proxy host
  host = "sakura.proxy.rlwy.net" if "rlwy" in server_host or "pixel" in server_host else server_host
  port = 44908

  net = NetworkClient(host, port)
  is_connected = net.connect()

  if is_connected:
    net.send({"type": "join", "name": player_name})

  # Player state
  player_pos = [400, 300]
  speed = 6
  font = pygame.font.SysFont("Consolas", 16, bold=True)

  running = True
  while running:
    clock.tick(60)

    # Event handling
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        running = False
      elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        running = False

    # Movement controls
    keys = pygame.key.get_pressed()
    moved = False
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
      player_pos[0] -= speed
      moved = True
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
      player_pos[0] += speed
      moved = True
    if keys[pygame.K_UP] or keys[pygame.K_w]:
      player_pos[1] -= speed
      moved = True
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
      player_pos[1] += speed
      moved = True

    # Keep player within screen bounds
    player_pos[0] = max(20, min(SCREEN_WIDTH - 20, player_pos[0]))
    player_pos[1] = max(20, min(SCREEN_HEIGHT - 20, player_pos[1]))

    # Send state to server
    if moved and net.connected:
      net.send({"type": "update", "x": player_pos[0], "y": player_pos[1]})

    # Drawing
    screen.fill(DARK_BG)

    # Render connection status HUD
    status_txt = (
        f"CONNECTED TO {host}:{port}" if net.connected else "OFFLINE MODE"
    )
    status_col = GREEN if net.connected else RED
    screen.blit(font.render(f"● {status_txt}", True, status_col), (20, 20))
    screen.blit(
        font.render(f"LOCATION: {city_name.upper()}", True, CYAN), (20, 45)
    )

    # Draw remote players (Other clients connected)
    for p_id, p_data in net.other_players.items():
      rx, ry = p_data.get("x", 0), p_data.get("y", 0)
      rname = p_data.get("name", "Player")
      pygame.draw.rect(screen, RED, (rx - 15, ry - 15, 30, 30), border_radius=4)
      label = font.render(rname, True, WHITE)
      screen.blit(
          label, (rx - label.get_width() // 2, ry - 32)
      )

    # Draw local player
    pygame.draw.rect(
        screen, GREEN, (player_pos[0] - 15, player_pos[1] - 15, 30, 30), border_radius=4
    )
    p_label = font.render(f"{player_name} (YOU)", True, GOLD)
    screen.blit(
        p_label, (player_pos[0] - p_label.get_width() // 2, player_pos[1] - 32)
    )

    pygame.display.flip()

  if net.socket:
    net.socket.close()


if __name__ == "__main__":
  run_multiplayer_game("Dhaka", "Soldier1", "sakura.proxy.rlwy.net", "SOLO_20", "")