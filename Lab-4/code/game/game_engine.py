"""
GameEngine: owns the frog and all vehicles, and runs one frame's worth
of game logic.

States:
  playing   - normal play, timer running
  hit       - brief pause after losing a life (frog flashes red)
  won       - frog reached the goal
  game_over - all lives used up
"""

import random

import pygame

from game.frog import Frog
from game.vehicle import Vehicle
from game.collisions import check_collision
from game import renderer
from game.renderer import (
    GRID_COLS, GOAL_ROW, ROAD_ROWS, START_ROW, CELL_SIZE, WIDTH, HEIGHT,
)

LANE_SPEEDS = [1.5, -2, 2, -2.5, 1.5, -2]   # one entry per road row, alternating direction

START_LIVES = 3
ATTEMPT_SECONDS = 30
HIT_PAUSE_MS = 800
WIN_POINTS = 100
TIME_BONUS_PER_SEC = 10


class GameEngine:
    def __init__(self):
        self._build_entities()

    def _build_entities(self):
        """Builds a fresh game. Also used by R to restart from scratch."""
        start_col = GRID_COLS // 2
        self.frog = Frog(
            col=start_col, row=START_ROW,
            start_col=start_col, start_row=START_ROW,
            cols=GRID_COLS, start_row_limit=START_ROW,
        )
        frog_x_range = (start_col * CELL_SIZE, start_col * CELL_SIZE + CELL_SIZE)

        self.vehicles = []
        for i, row in enumerate(ROAD_ROWS):
            speed = LANE_SPEEDS[i % len(LANE_SPEEDS)]
            vehicle_width = 40 if i % 2 == 0 else 70   # mix of cars and wider trucks
            spacing = 300
            count = 2

            # Try a few random phases and keep the first one that doesn't
            # already overlap the frog's starting column.
            for _attempt in range(20):
                phase = random.randint(0, spacing - 1)
                positions = []
                safe = True
                for n in range(count):
                    offset = phase + n * spacing
                    x = offset if speed > 0 else WIDTH - offset - vehicle_width
                    positions.append(x)
                    if not (x + vehicle_width <= frog_x_range[0] or x >= frog_x_range[1]):
                        safe = False
                if safe:
                    break

            for x in positions:
                self.vehicles.append(Vehicle(x=x, row=row, width=vehicle_width,
                                             height=CELL_SIZE - 8, speed=speed))

        # Game state
        self.state = "playing"
        self.lives = START_LIVES
        self.score = 0
        self.time_left = float(ATTEMPT_SECONDS)
        self.hit_reason = ""
        self.hit_until = 0
        self.last_tick = pygame.time.get_ticks()

    def handle_keydown(self, key):
        if key == pygame.K_r:
            self._build_entities()
            return
        if self.state != "playing":
            return   # no movement during the hit pause or after the game ends
        if key == pygame.K_UP:
            self.frog.move(0, -1)
        elif key == pygame.K_DOWN:
            self.frog.move(0, 1)
        elif key == pygame.K_LEFT:
            self.frog.move(-1, 0)
        elif key == pygame.K_RIGHT:
            self.frog.move(1, 0)

    def _lose_life(self, reason):
        self.lives -= 1
        self.hit_reason = reason
        self.state = "hit"
        self.hit_until = pygame.time.get_ticks() + HIT_PAUSE_MS

    def _finish_hit(self):
        if self.lives <= 0:
            self.state = "game_over"
        else:
            self.frog.reset()
            self.time_left = float(ATTEMPT_SECONDS)
            self.state = "playing"

    def update(self):
        now = pygame.time.get_ticks()
        dt = (now - self.last_tick) / 1000.0
        self.last_tick = now

        if self.state in ("playing", "hit"):
            for v in self.vehicles:
                v.update(road_width_px=WIDTH)

        if self.state == "playing":
            self.time_left = max(0.0, self.time_left - dt)
            if self.frog.row == GOAL_ROW:
                self.score += WIN_POINTS + int(self.time_left) * TIME_BONUS_PER_SEC
                self.state = "won"
            elif check_collision(self.frog, self.vehicles):
                self._lose_life("Hit!")
            elif self.time_left <= 0:
                self._lose_life("Time's up!")
        elif self.state == "hit":
            if now >= self.hit_until:
                self._finish_hit()

    def draw(self, surface, font):
        frog_color = None
        if self.state == "hit":
            # blink red/white so the hit is clearly visible
            frog_color = renderer.COLOR_FROG_HIT if (pygame.time.get_ticks() // 120) % 2 == 0 else (255, 255, 255)

        renderer.draw_scene(surface, self.frog, self.vehicles, frog_color)
        renderer.draw_hud(surface, font, self.lives, self.score, self.time_left)

        if self.state == "hit":
            renderer.draw_banner(surface, font, self.hit_reason)
        elif self.state == "won":
            renderer.draw_overlay(surface)
            renderer.draw_banner(surface, font, "You Won!  Score: %d" % self.score, dy=-12)
            renderer.draw_banner(surface, font, "Press R to play again", dy=16, color=(255, 255, 255))
        elif self.state == "game_over":
            renderer.draw_overlay(surface)
            renderer.draw_banner(surface, font, "Game Over  Score: %d" % self.score, dy=-12)
            renderer.draw_banner(surface, font, "Press R to restart", dy=16, color=(255, 255, 255))
        else:
            renderer.draw_text(surface, font, "Arrow keys to move. R to restart.", (10, HEIGHT - 24))
