import json
import math
import random
import socket
import sys
import threading
import pygame

import weather

# Screen Window Dimensions
SCREEN_WIDTH = 1100
SCREEN_HEIGHT = 650

# Map World Dimensions (Camera scrolls within this larger world)
WORLD_WIDTH = 2400
WORLD_HEIGHT = 1400

# Base UI Colors
CYAN = (0, 240, 255)
GOLD = (255, 215, 0)
GREEN = (40, 230, 110)
RED = (255, 60, 60)
WHITE = (255, 255, 255)
GREY = (140, 150, 170)
DARK_PANEL = (15, 20, 32)

# --- CITY THEME COLOR PALETTES ---
CITY_THEMES = {
    "SYLHET": {
        "sky_day": (30, 80, 60),
        "sky_night": (10, 30, 25),
        "ground": (34, 110, 56),
        "building": (40, 65, 50),
        "roof": (60, 100, 75),
        "window": (255, 220, 120),
    },
    "DHAKA": {
        "sky_day": (40, 85, 70),
        "sky_night": (12, 32, 28),
        "ground": (45, 120, 65),
        "building": (50, 70, 60),
        "roof": (75, 110, 85),
        "window": (255, 230, 130),
    },
    "TOKYO": {
        "sky_day": (25, 25, 55),
        "sky_night": (12, 10, 30),
        "ground": (40, 30, 70),
        "building": (25, 20, 45),
        "roof": (255, 0, 128),
        "window": (0, 240, 255),
    },
    "DUBAI": {
        "sky_day": (120, 85, 45),
        "sky_night": (35, 20, 15),
        "ground": (190, 140, 70),
        "building": (75, 55, 35),
        "roof": (210, 170, 90),
        "window": (255, 240, 180),
    },
    "LONDON": {
        "sky_day": (70, 80, 90),
        "sky_night": (20, 25, 32),
        "ground": (50, 65, 60),
        "building": (55, 60, 68),
        "roof": (85, 95, 105),
        "window": (240, 210, 130),
    },
    "MOSCOW": {
        "sky_day": (60, 75, 95),
        "sky_night": (18, 24, 38),
        "ground": (180, 200, 215),
        "building": (45, 55, 75),
        "roof": (120, 145, 175),
        "window": (170, 220, 255),
    },
    "NEW YORK": {
        "sky_day": (85, 60, 95),
        "sky_night": (18, 15, 32),
        "ground": (60, 60, 70),
        "building": (50, 45, 60),
        "roof": (130, 80, 120),
        "window": (255, 200, 100),
    },
}

DEFAULT_THEME = {
    "sky_day": (35, 50, 75),
    "sky_night": (12, 18, 30),
    "ground": (45, 70, 50),
    "building": (45, 52, 70),
    "roof": (70, 80, 105),
    "window": (255, 230, 120),
}


def get_city_theme(city_name):
  return CITY_THEMES.get(city_name.upper().strip(), DEFAULT_THEME)


class Camera:
  """Mini Militia style camera tracking player across large world."""

  def __init__(self, width, height):
    self.camera = pygame.Rect(0, 0, width, height)
    self.width = width
    self.height = height

  def apply(self, rect):
    return rect.move(self.camera.topleft)

  def apply_pos(self, x, y):
    return x + self.camera.x, y + self.camera.y

  def update(self, target_rect):
    x = -target_rect.centerx + int(SCREEN_WIDTH / 2)
    y = -target_rect.centery + int(SCREEN_HEIGHT / 2)

    x = min(0, max(-(self.width - SCREEN_WIDTH), x))
    y = min(0, max(-(self.height - SCREEN_HEIGHT), y))
    self.camera = pygame.Rect(x, y, self.width, self.height)


class Building:

  def __init__(self, x, y, width, height, is_ground=False):
    self.rect = pygame.Rect(x, y, width, height)
    self.is_ground = is_ground

  def draw(self, screen, camera, theme):
    cam_rect = camera.apply(self.rect)
    b_color = theme["ground"] if self.is_ground else theme["building"]
    r_color = theme["roof"]

    pygame.draw.rect(screen, b_color, cam_rect)
    pygame.draw.rect(screen, r_color, cam_rect, width=3)

    if not self.is_ground:
      for wx in range(self.rect.x + 12, self.rect.right - 12, 25):
        for wy in range(self.rect.y + 15, self.rect.bottom - 15, 30):
          win_rect = camera.apply(pygame.Rect(wx, wy, 12, 16))
          pygame.draw.rect(screen, theme["window"], win_rect)


class Coin:

  def __init__(self, x, y):
    self.x = x
    self.y = y
    self.radius = 8
    self.pulse = random.uniform(0, 6)

  def draw(self, screen, camera):
    self.pulse += 0.1
    r = self.radius + int(math.sin(self.pulse) * 2)
    cx, cy = camera.apply_pos(self.x, self.y)
    pygame.draw.circle(screen, GOLD, (cx, cy), r)
    pygame.draw.circle(screen, (255, 255, 180), (cx, cy), max(2, r - 3))

  def get_rect(self):
    return pygame.Rect(
        self.x - self.radius,
        self.y - self.radius,
        self.radius * 2,
        self.radius * 2,
    )


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
      self.socket.settimeout(3.0)
      self.socket.connect((self.host, self.port))
      self.socket.settimeout(None)
      self.connected = True
      threading.Thread(target=self.receive_data, daemon=True).start()
      return True
    except Exception:
      self.connected = False
      return False

  def send(self, data):
    if self.connected and self.socket:
      try:
        msg = json.dumps(data) + "\n"
        self.socket.sendall(msg.encode("utf-8"))
      except Exception:
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
            if msg.get("type") == "welcome":
              self.player_id = msg.get("id")
            elif msg.get("type") == "state_update":
              players = msg.get("players", [])
              self.other_players = {
                  p["id"]: p for p in players if p["id"] != self.player_id
              }
      except Exception:
        break
    self.connected = False


class WeatherParticleSystem:

  def __init__(self):
    self.particles = []

  def update_and_draw(self, screen, weather_condition):
    cond = str(weather_condition).lower()

    if "rain" in cond or "drizzle" in cond or "thunderstorm" in cond:
      if len(self.particles) < 120:
        self.particles.append([
            random.randint(0, SCREEN_WIDTH),
            random.randint(-20, 0),
            random.randint(8, 14),
        ])
      for p in self.particles:
        p[1] += p[2]
        pygame.draw.line(
            screen, (150, 200, 255), (p[0], p[1]), (p[0] - 2, p[1] + 10), 2
        )
        if p[1] > SCREEN_HEIGHT:
          p[1] = random.randint(-20, 0)
          p[0] = random.randint(0, SCREEN_WIDTH)

    elif "snow" in cond:
      if len(self.particles) < 80:
        self.particles.append([
            random.randint(0, SCREEN_WIDTH),
            random.randint(-20, 0),
            random.randint(2, 5),
            random.randint(2, 4),
        ])
      for p in self.particles:
        p[1] += p[2]
        p[0] += math.sin(p[1] * 0.05)
        pygame.draw.circle(screen, (255, 255, 255), (int(p[0]), int(p[1])), p[3])
        if p[1] > SCREEN_HEIGHT:
          p[1] = random.randint(-20, 0)
          p[0] = random.randint(0, SCREEN_WIDTH)


def generate_map():
  """Generates ground floor and scattered sky buildings."""
  buildings = [
      Building(0, WORLD_HEIGHT - 60, WORLD_WIDTH, 60, is_ground=True),
      Building(200, WORLD_HEIGHT - 350, 180, 290),
      Building(500, WORLD_HEIGHT - 550, 220, 490),
      Building(850, WORLD_HEIGHT - 400, 200, 340),
      Building(1200, WORLD_HEIGHT - 600, 250, 540),
      Building(1600, WORLD_HEIGHT - 380, 220, 320),
      Building(1900, WORLD_HEIGHT - 500, 180, 440),
  ]

  coins = []
  while len(coins) < 30:
    cx = random.randint(100, WORLD_WIDTH - 100)
    cy = random.randint(100, WORLD_HEIGHT - 120)
    c_rect = pygame.Rect(cx - 10, cy - 10, 20, 20)
    if not any(b.rect.colliderect(c_rect) for b in buildings):
      coins.append(Coin(cx, cy))

  return buildings, coins


def draw_pause_menu(screen, font_lg, font_sm, selected_idx):
  """Renders interactive ESC Pause Menu Overlay."""
  overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
  overlay.fill((0, 0, 0, 180))  # Semi-transparent backdrop
  screen.blit(overlay, (0, 0))

  panel_rect = pygame.Rect(
      SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 170, 400, 340
  )
  pygame.draw.rect(screen, DARK_PANEL, panel_rect, border_radius=12)
  pygame.draw.rect(screen, CYAN, panel_rect, width=3, border_radius=12)

  title = font_lg.render("GAME PAUSED", True, GOLD)
  screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, panel_rect.y + 25))

  options = [
      "1. RESUME GAME",
      "2. TOGGLE FULLSCREEN",
      "3. QUIT TO MAIN MENU",
      "4. QUIT TO DESKTOP",
  ]

  for i, opt in enumerate(options):
    col = GREEN if i == selected_idx else WHITE
    bg_col = (30, 45, 65) if i == selected_idx else (20, 28, 40)

    btn_rect = pygame.Rect(panel_rect.x + 30, panel_rect.y + 85 + (i * 55), 340, 42)
    pygame.draw.rect(screen, bg_col, btn_rect, border_radius=6)
    pygame.draw.rect(
        screen, col if i == selected_idx else GREY, btn_rect, width=2, border_radius=6
    )

    lbl = font_sm.render(opt, True, col)
    screen.blit(
        lbl,
        (
            btn_rect.x + 20,
            btn_rect.y + 12,
        ),
    )

  hint = font_sm.render("[UP/DOWN/ENTER] Select | [ESC] Resume", True, GREY)
  screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, panel_rect.bottom - 25))


def run_multiplayer_game(
    city_name, player_name, server_host, game_mode, api_key
):
  pygame.init()
  screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
  pygame.display.set_caption(f"MINI MILITIA STYLE ARCADE - [{player_name}]")
  clock = pygame.time.Clock()

  # Load Theme Palette for City
  city_theme = get_city_theme(city_name)

  # Fetch Live Weather
  weather_data = weather.fetch_weather_data(city_name, api_key)
  temp = weather_data.get("temp", "N/A")
  condition = weather_data.get("condition", "clear")
  description = weather_data.get("description", "CLEAR SKY").upper()
  tz_offset = weather_data.get("timezone_offset", 21600)
  time_str, current_hour = weather.get_city_current_time(tz_offset)

  is_night = current_hour < 6 or current_hour >= 18
  bg_color = city_theme["sky_night"] if is_night else city_theme["sky_day"]

  # Network Client
  host = "sakura.proxy.rlwy.net" if (
      "rlwy" in server_host or "pixel" in server_host or not server_host
  ) else server_host
  net = NetworkClient(host, 44908)
  is_multiplayer = "MULTIPLAYER" in game_mode.upper() or "CO-OP" in game_mode.upper()
  if is_multiplayer and net.connect():
    net.send({"type": "join", "name": player_name})

  # Camera & World Setup
  camera = Camera(WORLD_WIDTH, WORLD_HEIGHT)
  buildings, coins = generate_map()

  # Player Physics
  player_rect = pygame.Rect(100, WORLD_HEIGHT - 200, 28, 36)
  vel_x, vel_y = 0, 0
  gravity = 0.5
  jetpack_thrust = -0.9
  move_speed = 6
  jetpack_fuel = 100.0
  score = 0
  on_ground = False

  # Pause State
  is_paused = False
  pause_selected = 0
  is_fullscreen = False

  font_lg = pygame.font.SysFont("Consolas", 18, bold=True)
  font_sm = pygame.font.SysFont("Consolas", 14, bold=True)
  particle_sys = WeatherParticleSystem()

  running = True
  while running:
    clock.tick(60)

    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        running = False

      elif event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
          is_paused = not is_paused

        if is_paused:
          if event.key == pygame.K_UP:
            pause_selected = (pause_selected - 1) % 4
          elif event.key == pygame.K_DOWN:
            pause_selected = (pause_selected + 1) % 4
          elif event.key == pygame.K_RETURN:
            if pause_selected == 0:  # Resume
              is_paused = False
            elif pause_selected == 1:  # Fullscreen Toggle
              is_fullscreen = not is_fullscreen
              screen = (
                  pygame.display.set_mode(
                      (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN
                  )
                  if is_fullscreen
                  else pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
              )
            elif pause_selected == 2:  # Main Menu
              running = False
            elif pause_selected == 3:  # Quit Desktop
              if net.socket:
                net.socket.close()
              pygame.quit()
              sys.exit()

    if not is_paused:
      keys = pygame.key.get_pressed()

      # Horizontal Movement
      vel_x = 0
      if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        vel_x = -move_speed
      if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        vel_x = move_speed

      # Jetpack & Gravity
      if (
          keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]
      ) and jetpack_fuel > 0:
        vel_y += jetpack_thrust
        jetpack_fuel = max(0, jetpack_fuel - 0.8)
      else:
        vel_y += gravity
        if on_ground:
          jetpack_fuel = min(100.0, jetpack_fuel + 0.5)

      vel_y = min(12, vel_y)

      # Collisions X
      player_rect.x += int(vel_x)
      for b in buildings:
        if player_rect.colliderect(b.rect):
          if vel_x > 0:
            player_rect.right = b.rect.left
          elif vel_x < 0:
            player_rect.left = b.rect.right

      # Collisions Y
      player_rect.y += int(vel_y)
      on_ground = False
      for b in buildings:
        if player_rect.colliderect(b.rect):
          if vel_y > 0:
            player_rect.bottom = b.rect.top
            vel_y = 0
            on_ground = True
          elif vel_y < 0:
            player_rect.top = b.rect.bottom
            vel_y = 0

      player_rect.x = max(
          0, min(WORLD_WIDTH - player_rect.width, player_rect.x)
      )
      player_rect.y = max(
          0, min(WORLD_HEIGHT - player_rect.height, player_rect.y)
      )

      camera.update(player_rect)

      if net.connected:
        net.send(
            {"type": "update", "x": player_rect.centerx, "y": player_rect.centery}
        )

      for coin in coins[:]:
        if player_rect.colliderect(coin.get_rect()):
          coins.remove(coin)
          score += 1

    # --- RENDER GAME ---
    screen.fill(bg_color)

    # Render City Objects with Custom Theme
    for building in buildings:
      building.draw(screen, camera, city_theme)

    for coin in coins:
      coin.draw(screen, camera)

    particle_sys.update_and_draw(screen, condition)

    # Remote Players
    for p_id, p_data in net.other_players.items():
      rx, ry = p_data.get("x", 0), p_data.get("y", 0)
      rname = p_data.get("name", "Player")
      cam_rx, cam_ry = camera.apply_pos(rx - 14, ry - 18)
      pygame.draw.rect(screen, RED, (cam_rx, cam_ry, 28, 36), border_radius=4)
      label = font_sm.render(rname, True, WHITE)
      screen.blit(label, (cam_rx - label.get_width() // 2 + 14, cam_ry - 20))

    # Local Player
    cam_px, cam_py = camera.apply_pos(player_rect.x, player_rect.y)
    pygame.draw.rect(
        screen, GREEN, (cam_px, cam_py, player_rect.width, player_rect.height), border_radius=4
    )
    p_label = font_sm.render(f"{player_name} (YOU)", True, GOLD)
    screen.blit(
        p_label, (cam_px - p_label.get_width() // 2 + 14, cam_py - 20)
    )

    # Jetpack Flame
    keys = pygame.key.get_pressed()
    if (
        not is_paused
        and (keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE])
        and jetpack_fuel > 0
    ):
      pygame.draw.polygon(
          screen,
          GOLD,
          [
              (cam_px + 6, cam_py + player_rect.height),
              (cam_px + 22, cam_py + player_rect.height),
              (cam_px + 14, cam_py + player_rect.height + 12),
          ],
      )

    # --- TOP HUD ---
    pygame.draw.rect(screen, (10, 12, 20), (0, 0, SCREEN_WIDTH, 70))
    pygame.draw.line(screen, CYAN, (0, 70), (SCREEN_WIDTH, 70), 2)

    screen.blit(font_lg.render(f"MODE: {game_mode}", True, WHITE), (20, 12))
    status_txt = "ONLINE" if net.connected else "OFFLINE"
    status_col = GREEN if net.connected else GREY
    screen.blit(
        font_sm.render(f"SERVER: {status_txt}", True, status_col), (20, 38)
    )

    screen.blit(
        font_lg.render(f"THEME: {city_name.upper()}", True, GOLD), (250, 12)
    )
    screen.blit(
        font_sm.render(
            f"{description} | {temp}°C | TIME: {time_str}", True, CYAN
        ),
        (250, 38),
    )

    screen.blit(font_sm.render("JETPACK FUEL", True, WHITE), (700, 15))
    pygame.draw.rect(screen, GREY, (700, 36, 140, 16), width=2)
    pygame.draw.rect(
        screen,
        CYAN if jetpack_fuel > 20 else RED,
        (702, 38, int(1.36 * jetpack_fuel), 12),
    )

    screen.blit(font_lg.render(f"COINS: {score}", True, GOLD), (940, 20))

    # Pause Overlay Menu
    if is_paused:
      draw_pause_menu(screen, font_lg, font_sm, pause_selected)

    pygame.display.flip()

  if net.socket:
    net.socket.close()


if __name__ == "__main__":
  run_multiplayer_game(
      "Sylhet", "Soldier1", "sakura.proxy.rlwy.net", "SOLO_20", ""
  )