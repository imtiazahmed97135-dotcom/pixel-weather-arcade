import asyncio
import sys
import pygame

from game import run_multiplayer_game
from weather import fetch_weather_data, get_city_current_time

SCREEN_WIDTH = 1100
SCREEN_HEIGHT = 650

CYAN = (0, 240, 255)
GOLD = (255, 215, 0)
GREEN = (40, 230, 110)
RED = (255, 60, 60)
WHITE = (255, 255, 255)
GREY = (140, 150, 170)
DARK_BG = (12, 15, 24)


async def main():
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("WEATHER-PIXEL GAME - ARCADE DASHBOARD")
    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont("Impact", 42)
    font_sub = pygame.font.SysFont("Trebuchet MS", 14, bold=True)
    font_ui = pygame.font.SysFont("Consolas", 16, bold=True)
    font_clock = pygame.font.SysFont("Consolas", 20, bold=True)
    font_large = pygame.font.SysFont("Impact", 32)

    city_name = "Dhaka"
    player_name = "Soldier1"
    server_ip = "sakura.proxy.rlwy.net"  # Updated to your Railway server domain
    game_mode = "SOLO_20"
    api_key = ""

    active_input = "city"
    active_view = "DASHBOARD"

    input_city = pygame.Rect(180, 140, 280, 42)
    input_name = pygame.Rect(180, 195, 280, 42)
    input_ip = pygame.Rect(180, 250, 280, 42)

    city_presets = ["Dhaka", "Sylhet", "London", "Tokyo", "New York"]

    btn_play_action = pygame.Rect(180, 470, 350, 55)
    btn_weather_action = pygame.Rect(560, 470, 360, 55)

    btn_quit = pygame.Rect(960, 20, 110, 40)
    btn_back_details = pygame.Rect(50, 560, 180, 45)

    weather_data = fetch_weather_data(city_name, api_key)

    running = True
    while running:
        clock.tick(30)
        tz_offset = weather_data.get("timezone_offset", 0)
        live_time, local_hour = get_city_current_time(tz_offset)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            if event.type == pygame.MOUSEBUTTONDOWN:
                if btn_quit.collidepoint(event.pos):
                    running = False
                    break

                if active_view == "DASHBOARD":
                    if input_city.collidepoint(event.pos):
                        active_input = "city"
                    elif input_name.collidepoint(event.pos):
                        active_input = "name"
                    elif input_ip.collidepoint(event.pos):
                        active_input = "ip"

                    elif btn_play_action.collidepoint(event.pos):
                        # Transition to game loop asynchronously
                        await run_multiplayer_game(
                            city_name, player_name, server_ip, game_mode, api_key
                        )

                    elif btn_weather_action.collidepoint(event.pos):
                        active_view = "WEATHER_DETAILS"

                    for i, c in enumerate(city_presets):
                        pill = pygame.Rect(180 + (i * 95), 305, 85, 28)
                        if pill.collidepoint(event.pos):
                            city_name = c
                            weather_data = fetch_weather_data(city_name, api_key)

                elif active_view == "WEATHER_DETAILS":
                    if btn_back_details.collidepoint(event.pos):
                        active_view = "DASHBOARD"

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if active_view == "WEATHER_DETAILS":
                        active_view = "DASHBOARD"
                    else:
                        running = False
                        break

                if active_view == "DASHBOARD":
                    need_update = False
                    if event.key == pygame.K_RETURN:
                        need_update = True
                    elif event.key == pygame.K_BACKSPACE:
                        if active_input == "city" and len(city_name) > 0:
                            city_name = city_name[:-1]
                            need_update = True
                        elif active_input == "name":
                            player_name = player_name[:-1]
                        elif active_input == "ip":
                            server_ip = server_ip[:-1]
                    else:
                        if (
                            active_input == "city"
                            and len(city_name) < 16
                            and event.unicode.isprintable()
                        ):
                            city_name += event.unicode
                            need_update = True
                        elif (
                            active_input == "name"
                            and len(player_name) < 12
                            and event.unicode.isprintable()
                        ):
                            player_name += event.unicode
                        elif (
                            active_input == "ip"
                            and len(server_ip) < 18
                            and event.unicode.isprintable()
                        ):
                            server_ip += event.unicode

                    if need_update and len(city_name.strip()) >= 2:
                        weather_data = fetch_weather_data(
                            city_name.strip(), api_key
                        )

        screen.fill(DARK_BG)

        # Header Navigation
        pygame.draw.rect(screen, (20, 26, 40), (0, 0, SCREEN_WIDTH, 85))
        pygame.draw.line(screen, CYAN, (0, 85), (SCREEN_WIDTH, 85), 3)
        screen.blit(
            font_title.render("⚡ WEATHER-PIXEL GAME ⚡", True, CYAN), (30, 15)
        )

        # Quit Button
        pygame.draw.rect(screen, (40, 20, 30), btn_quit, border_radius=6)
        pygame.draw.rect(screen, RED, btn_quit, 2, border_radius=6)
        screen.blit(
            font_ui.render("✖ QUIT", True, RED),
            (btn_quit.x + 22, btn_quit.y + 10),
        )

        if active_view == "DASHBOARD":
            for lbl, rect, val, key in [
                ("CITY:", input_city, city_name, "city"),
                ("NAME:", input_name, player_name, "name"),
                ("SERVER:", input_ip, server_ip, "ip"),
            ]:
                screen.blit(font_sub.render(lbl, True, GREY), (50, rect.y + 12))
                col = CYAN if active_input == key else (50, 60, 80)
                pygame.draw.rect(screen, (22, 28, 42), rect, border_radius=6)
                pygame.draw.rect(screen, col, rect, 2, border_radius=6)
                screen.blit(
                    font_ui.render(
                        val + ("_" if active_input == key else ""), True, WHITE
                    ),
                    (rect.x + 12, rect.y + 12),
                )

            screen.blit(font_sub.render("PRESETS:", True, GREY), (50, 308))
            for i, c in enumerate(city_presets):
                pill = pygame.Rect(180 + (i * 95), 305, 85, 28)
                is_active = city_name.lower() == c.lower()
                pygame.draw.rect(
                    screen,
                    CYAN if is_active else (30, 38, 55),
                    pill,
                    border_radius=14,
                )
                t_surf = font_sub.render(
                    c, True, (10, 15, 25) if is_active else WHITE
                )
                screen.blit(
                    t_surf,
                    (
                        pill.centerx - t_surf.get_width() // 2,
                        pill.centery - t_surf.get_height() // 2,
                    ),
                )

            card = pygame.Rect(180, 350, 740, 100)
            pygame.draw.rect(screen, (22, 28, 42), card, border_radius=10)
            pygame.draw.rect(screen, CYAN, card, 2, border_radius=10)

            disp_city = weather_data.get("city", city_name).upper()
            screen.blit(
                font_large.render(f"LOCATION: {disp_city}", True, WHITE),
                (200, 362),
            )
            screen.blit(
                font_sub.render(
                    f"TEMP: {weather_data.get('temp', '--')}°C  |  COND: {weather_data.get('description', 'CLEAR').upper()}",
                    True,
                    GOLD,
                ),
                (200, 410),
            )
            screen.blit(
                font_clock.render(f"🕒 {live_time}", True, CYAN), (680, 385)
            )

            pygame.draw.rect(screen, GREEN, btn_play_action, border_radius=8)
            t_play = font_large.render("🎮 PLAY GAME ▶", True, (10, 25, 15))
            screen.blit(
                t_play,
                (
                    btn_play_action.centerx - t_play.get_width() // 2,
                    btn_play_action.centery - t_play.get_height() // 2,
                ),
            )

            pygame.draw.rect(
                screen, (30, 40, 60), btn_weather_action, border_radius=8
            )
            pygame.draw.rect(screen, CYAN, btn_weather_action, 2, border_radius=8)
            t_wx = font_large.render("🌤️ WEATHER DETAILS", True, CYAN)
            screen.blit(
                t_wx,
                (
                    btn_weather_action.centerx - t_wx.get_width() // 2,
                    btn_weather_action.centery - t_wx.get_height() // 2,
                ),
            )

        elif active_view == "WEATHER_DETAILS":
            panel = pygame.Rect(100, 120, 900, 410)
            pygame.draw.rect(screen, (22, 28, 42), panel, border_radius=12)
            pygame.draw.rect(screen, CYAN, panel, 2, border_radius=12)

            screen.blit(
                font_large.render(
                    f"METEOROLOGICAL REPORT: {weather_data.get('city', city_name).upper()}",
                    True,
                    GOLD,
                ),
                (130, 145),
            )
            pygame.draw.line(screen, (40, 50, 70), (130, 195), (970, 195), 2)

            metrics = [
                f"TEMPERATURE: {weather_data.get('temp')}°C",
                f"FEELS LIKE: {weather_data.get('feels_like')}°C",
                f"CONDITION: {weather_data.get('description').upper()}",
                f"HUMIDITY: {weather_data.get('humidity')}%",
                f"WIND SPEED: {weather_data.get('wind_speed')} km/h",
                f"ATMOSPHERIC PRESSURE: {weather_data.get('pressure')} hPa",
                f"LOCAL TIME: {live_time}",
            ]

            for idx, m in enumerate(metrics):
                y_pos = 220 + (idx * 38)
                screen.blit(
                    font_ui.render(f"• {m}", True, WHITE), (140, y_pos)
                )

            pygame.draw.rect(
                screen, (40, 50, 70), btn_back_details, border_radius=8
            )
            pygame.draw.rect(
                screen, CYAN, btn_back_details, 1, border_radius=8
            )
            screen.blit(
                font_ui.render("◄ BACK TO MENU", True, WHITE),
                (btn_back_details.x + 20, btn_back_details.y + 12),
            )

        pygame.display.flip()

        # CRITICAL FOR BROWSER RUNTIME (Pygbag): yields execution back to JavaScript browser engine
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    asyncio.run(main())