import pygame
import sys
import random
import math
import socket
import json
import threading
from weather import fetch_weather_data, get_city_current_time

SCREEN_WIDTH = 1100
SCREEN_HEIGHT = 650
WORLD_WIDTH = 3200
WORLD_HEIGHT = 1200

CYAN = (0, 240, 255)
GOLD = (255, 215, 0)
RED = (255, 60, 60)
GREEN = (40, 230, 110)
WHITE = (255, 255, 255)
GREY = (140, 150, 170)


def get_sky_colors(hour):
    if 6 <= hour < 17:
        return (100, 180, 255), (200, 230, 255), (70, 130, 180)
    elif 17 <= hour < 20:
        return (255, 90, 60), (255, 180, 100), (120, 60, 90)
    else:
        return (10, 14, 26), (22, 30, 50), (25, 32, 48)


class WeatherSystem:
    def __init__(self):
        self.particles = []
        for _ in range(120):
            self.particles.append({
                "x": random.randint(0, SCREEN_WIDTH),
                "y": random.randint(0, SCREEN_HEIGHT),
                "speed": random.uniform(8, 15),
                "size": random.randint(2, 4)
            })

    def update_and_draw(self, surface, condition):
        if "rain" in condition or "thunder" in condition:
            for p in self.particles:
                p["y"] += p["speed"]
                p["x"] -= 2
                if p["y"] > SCREEN_HEIGHT:
                    p["y"] = -10
                    p["x"] = random.randint(0, SCREEN_WIDTH)
                pygame.draw.line(surface, (180, 210, 255), (p["x"], p["y"]), (p["x"] - 2, p["y"] + 12), 2)

        elif "snow" in condition:
            for p in self.particles:
                p["y"] += p["speed"] * 0.25
                p["x"] += math.sin(p["y"] * 0.05)
                if p["y"] > SCREEN_HEIGHT:
                    p["y"] = -10
                    p["x"] = random.randint(0, SCREEN_WIDTH)
                pygame.draw.circle(surface, WHITE, (int(p["x"]), int(p["y"])), p["size"])


def run_multiplayer_game(city_name, player_name, server_ip, game_mode, api_key):
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(f"WEATHER-PIXEL GAME - [{city_name.upper()}]")
    clock = pygame.time.Clock()

    font_hud = pygame.font.SysFont("Impact", 16)
    font_bold = pygame.font.SysFont("Impact", 22)
    font_victory = pygame.font.SysFont("Impact", 58)
    font_sub = pygame.font.SysFont("Consolas", 18, bold=True)

    weather_data = fetch_weather_data(city_name, api_key)
    tz_offset = weather_data.get("timezone_offset", 0)
    weather_system = WeatherSystem()

    # Character Physics
    px, py = random.randint(300, 1000), 700.0
    vel_x, vel_y = 0.0, 0.0
    fuel = 100.0
    hp = 100
    score = 0
    facing_right = True

    # 20 Coins Pool Setup
    active_coins = [
        {"id": i, "x": random.randint(300, 2900), "y": random.choice([920, 800, 680, 540])}
        for i in range(20)
    ]

    my_color = (0, 240, 255)

    # 3-Minute Match Countdown
    MATCH_DURATION = 180
    start_ticks = pygame.time.get_ticks()
    match_over = False
    winner_name = ""

    ground_y = WORLD_HEIGHT - 80
    platforms = [
        pygame.Rect(300, 950, 400, 22),
        pygame.Rect(850, 820, 450, 22),
        pygame.Rect(1450, 700, 400, 22),
        pygame.Rect(2000, 850, 450, 22)
    ]

    btn_back = pygame.Rect(20, 20, 100, 36)
    btn_lobby = pygame.Rect(SCREEN_WIDTH // 2 - 180, 480, 360, 55)

    other_players = {}
    net_connected = False
    collected_id = None
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        sock.connect((server_ip, 5555))
        init_data = json.loads(sock.recv(1024).decode())
        my_id = init_data["id"]
        my_color = tuple(init_data["color"])
        net_connected = True
    except:
        my_id = random.randint(1, 999)

    def network_loop():
        nonlocal other_players, active_coins, collected_id
        while net_connected and not match_over:
            try:
                p_payload = json.dumps({
                    "x": px, "y": py, "name": player_name,
                    "facing_right": facing_right, "hp": hp, "score": score,
                    "collected_coin_id": collected_id
                })
                collected_id = None
                sock.send(p_payload.encode())
                
                reply = sock.recv(2048).decode()
                if reply:
                    server_state = json.loads(reply)
                    p_dict = server_state.get("players", {})
                    other_players = {int(k): v for k, v in p_dict.items() if int(k) != my_id}
                    
                    server_coins = server_state.get("coins", [])
                    if server_coins:
                        active_coins = server_coins
            except:
                break

    if net_connected:
        threading.Thread(target=network_loop, daemon=True).start()

    move_left = move_right = move_up = False
    anim_tick = 0

    running = True
    while running:
        clock.tick(60)
        anim_tick += 1
        live_time_str, local_hour = get_city_current_time(tz_offset)

        # Match Countdown
        elapsed_seconds = (pygame.time.get_ticks() - start_ticks) // 1000
        time_remaining = max(0, MATCH_DURATION - elapsed_seconds)
        time_display = f"{time_remaining // 60:02d}:{time_remaining % 60:02d}"

        if time_remaining <= 0 and not match_over:
            match_over = True
            all_players = [{"name": player_name, "score": score, "hp": hp}]
            for p in other_players.values():
                all_players.append({"name": p.get("name", "Player"), "score": p.get("score", 0), "hp": p.get("hp", 100)})
            all_players.sort(key=lambda x: (x["score"], x["hp"]), reverse=True)
            winner_name = all_players[0]["name"]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if btn_back.collidepoint(event.pos) and not match_over:
                    return
                elif match_over and btn_lobby.collidepoint(event.pos):
                    return

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if not match_over:
                    if event.key in (pygame.K_a, pygame.K_LEFT): move_left = True
                    elif event.key in (pygame.K_d, pygame.K_RIGHT): move_right = True
                    elif event.key in (pygame.K_w, pygame.K_SPACE, pygame.K_UP): move_up = True

            elif event.type == pygame.KEYUP and not match_over:
                if event.key in (pygame.K_a, pygame.K_LEFT): move_left = False
                elif event.key in (pygame.K_d, pygame.K_RIGHT): move_right = False
                elif event.key in (pygame.K_w, pygame.K_SPACE, pygame.K_UP): move_up = False

        # Physics Updates
        if not match_over:
            vel_x = 0
            if move_left: vel_x = -6.0; facing_right = False
            if move_right: vel_x = 6.0; facing_right = True

            if move_up and fuel > 0:
                vel_y += -0.85
                fuel = max(0.0, fuel - 0.5)
            vel_y += 0.45
            vel_y = max(-8.0, min(12.0, vel_y))

            px += vel_x
            py += vel_y

            px = max(0, min(WORLD_WIDTH - 30, px))
            py = max(0, min(WORLD_HEIGHT - 46, py))

            player_rect = pygame.Rect(int(px), int(py), 30, 46)

            if player_rect.bottom >= ground_y:
                py = ground_y - 46
                vel_y = 0
                fuel = min(100.0, fuel + 0.8)

            for p in platforms:
                if player_rect.colliderect(p) and vel_y > 0:
                    if player_rect.bottom - vel_y <= p.top + 12:
                        py = p.top - 46
                        vel_y = 0
                        fuel = min(100.0, fuel + 0.8)

            # Check collision against all 20 active coins
            for coin in active_coins:
                coin_rect = pygame.Rect(coin["x"], coin["y"], 22, 22)
                if player_rect.colliderect(coin_rect):
                    score += 10
                    collected_id = coin["id"]
                    if not net_connected:
                        coin["x"] = random.randint(300, 2900)
                        coin["y"] = random.choice([920, 800, 680, 540])
                    break

        # Camera
        cam_x = int(px) - SCREEN_WIDTH // 2
        cam_y = int(py) - SCREEN_HEIGHT // 2
        cam_x = max(0, min(WORLD_WIDTH - SCREEN_WIDTH, cam_x))
        cam_y = max(0, min(WORLD_HEIGHT - SCREEN_HEIGHT, cam_y))

        # Sky Background
        top_sky, bot_sky, mountain_col = get_sky_colors(local_hour)
        for y in range(0, SCREEN_HEIGHT, 8):
            interp = y / SCREEN_HEIGHT
            r = int(top_sky[0] * (1 - interp) + bot_sky[0] * interp)
            g = int(top_sky[1] * (1 - interp) + bot_sky[1] * interp)
            b = int(top_sky[2] * (1 - interp) + bot_sky[2] * interp)
            pygame.draw.rect(screen, (r, g, b), (0, y, SCREEN_WIDTH, 8))

        pygame.draw.ellipse(screen, mountain_col, (-100 - int(cam_x * 0.2), SCREEN_HEIGHT - 350, 900, 400))
        
        # Terrain
        pygame.draw.rect(screen, (35, 42, 58), (0 - cam_x, ground_y - cam_y, WORLD_WIDTH, 80))
        pygame.draw.rect(screen, GREEN, (0 - cam_x, ground_y - cam_y, WORLD_WIDTH, 8))

        for p in platforms:
            pygame.draw.rect(screen, (60, 70, 90), (p.x - cam_x, p.y - cam_y, p.width, p.height), border_radius=4)
            pygame.draw.rect(screen, CYAN, (p.x - cam_x, p.y - cam_y, p.width, 3), border_radius=2)

        # Render 20 Animated Coins
        scale = abs(math.sin(anim_tick * 0.1))
        coin_w = max(3, int(18 * scale))
        for coin in active_coins:
            cx = coin["x"] - cam_x
            cy = coin["y"] - cam_y
            if -30 <= cx <= SCREEN_WIDTH + 30 and -30 <= cy <= SCREEN_HEIGHT + 30:
                pygame.draw.ellipse(screen, GOLD, (cx + 11 - coin_w // 2, cy + 2, coin_w, 18))

        # Weather Particles
        weather_system.update_and_draw(screen, weather_data.get("condition", "clear"))

        # Remote Players
        for p_id, p_data in other_players.items():
            p_color = tuple(p_data.get("color", RED))
            pygame.draw.rect(screen, p_color, (int(p_data["x"]) - cam_x, int(p_data["y"]) - cam_y, 30, 46), border_radius=4)
            p_lbl = font_hud.render(p_data.get("name", "Player"), True, WHITE)
            screen.blit(p_lbl, (int(p_data["x"]) - cam_x - 5, int(p_data["y"]) - cam_y - 20))

        # Local Player
        pygame.draw.rect(screen, my_color, (int(px) - cam_x, int(py) - cam_y, 30, 46), border_radius=4)
        me_lbl = font_hud.render(f"YOU ({player_name})", True, GOLD)
        screen.blit(me_lbl, (int(px) - cam_x - 15, int(py) - cam_y - 20))

        # HUD Overlay
        pygame.draw.rect(screen, (20, 26, 40), btn_back, border_radius=6)
        pygame.draw.rect(screen, CYAN, btn_back, 1, border_radius=6)
        screen.blit(font_hud.render("◄ BACK", True, WHITE), (btn_back.x + 18, btn_back.y + 8))

        hud = pygame.Surface((520, 50), pygame.SRCALPHA)
        hud.fill((12, 16, 26, 220))
        screen.blit(hud, (140, 15))
        pygame.draw.rect(screen, CYAN, (140, 15, 520, 50), 2, border_radius=6)

        screen.blit(font_bold.render(f"📍 {city_name.upper()}  |  🕒 {live_time_str}", True, GOLD), (155, 26))
        screen.blit(font_bold.render(f"⏱️ TIME: {time_display}", True, RED if time_remaining < 30 else GREEN), (410, 26))
        screen.blit(font_bold.render(f"🪙 COIN: {score}", True, GOLD), (550, 26))

        # Victory Screen
        if match_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 14, 24, 210))
            screen.blit(overlay, (0, 0))

            card = pygame.Rect(SCREEN_WIDTH // 2 - 300, 120, 600, 420)
            pygame.draw.rect(screen, (20, 26, 40), card, border_radius=12)
            pygame.draw.rect(screen, GOLD, card, 3, border_radius=12)

            t_vic = font_victory.render("MATCH FINISHED!", True, GOLD)
            screen.blit(t_vic, (card.centerx - t_vic.get_width() // 2, card.y + 30))

            is_me = (winner_name == player_name)
            sub = f"🎉 YOU WIN! 🎉" if is_me else f"🏆 WINNER: {winner_name.upper()}"
            t_sub = font_bold.render(sub, True, GREEN if is_me else CYAN)
            screen.blit(t_sub, (card.centerx - t_sub.get_width() // 2, card.y + 120))

            screen.blit(font_sub.render(f"YOUR SCORE: {score} COINS", True, WHITE), (card.centerx - 110, card.y + 190))

            pygame.draw.rect(screen, GREEN, btn_lobby, border_radius=8)
            t_btn = font_bold.render("RETURN TO DASHBOARD ▶", True, (10, 25, 15))
            screen.blit(t_btn, (btn_lobby.centerx - t_btn.get_width() // 2, btn_lobby.centery - t_btn.get_height() // 2))

        pygame.display.flip()