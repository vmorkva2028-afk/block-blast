import pygame
import sys
import random
import os
import math
import array

pygame.init()

# --- Звук: если не заведётся — работаем молча ---
AUDIO_OK = True
try:
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.mixer.init()
except Exception:
    AUDIO_OK = False

# --- Размер экрана: на Android info.current_w может быть 0 ---
try:
    info = pygame.display.Info()
    WIDTH = info.current_w
    HEIGHT = info.current_h
except Exception:
    WIDTH = 0
    HEIGHT = 0

if WIDTH < 100 or HEIGHT < 100:
    WIDTH = 720
    HEIGHT = 1280

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Block Blast")

GRID_N = 8
CELL_SIZE = WIDTH // (GRID_N + 1)
BOARD_SIZE = CELL_SIZE * GRID_N
BOARD_X = (WIDTH - BOARD_SIZE) // 2
BOARD_Y = 200

BG = (20, 20, 32)
GRID_BG = (40, 40, 60)
CELL_EMPTY = (70, 70, 90)
CELL_BORDER = (110, 110, 140)
TEXT_COLOR = (240, 240, 255)
ACCENT = (255, 220, 90)

try:
    font_big = pygame.font.SysFont(None, 90)
    font_mid = pygame.font.SysFont(None, 60)
    font_small = pygame.font.SysFont(None, 40)
except Exception:
    font_big = pygame.font.Font(None, 90)
    font_mid = pygame.font.Font(None, 60)
    font_small = pygame.font.Font(None, 40)

DIR = os.path.dirname(os.path.abspath(__file__))
HIGHSCORE_FILE = os.path.join(DIR, "highscore.txt")


def make_sound(freq, duration, volume=0.4):
    sample_rate = 22050
    n_samples = int(sample_rate * duration)
    buf = array.array("h")
    amplitude = int(32767 * volume)
    for i in range(n_samples):
        env = 1.0 - (i / n_samples) * 0.9
        value = int(amplitude * env * math.sin(2 * math.pi * freq * i / sample_rate))
        buf.append(value)
    return pygame.mixer.Sound(buffer=buf.tobytes())


class _Silent:
    def play(self):
        pass


if AUDIO_OK:
    try:
        SOUND_CLICK = make_sound(880, 0.05, 0.3)
        SOUND_PLACE = make_sound(440, 0.08, 0.35)
        SOUND_CLEAR = make_sound(1200, 0.15, 0.45)
        SOUND_COMBO = make_sound(1600, 0.25, 0.5)
        SOUND_OVER = make_sound(180, 0.6, 0.4)
    except Exception:
        AUDIO_OK = False

if not AUDIO_OK:
    SOUND_CLICK = SOUND_PLACE = SOUND_CLEAR = SOUND_COMBO = SOUND_OVER = _Silent()

SHAPES = [
    [(0, 0)],
    [(0, 0), (0, 1)],
    [(0, 0), (1, 0)],
    [(0, 0), (0, 1), (0, 2)],
    [(0, 0), (1, 0), (2, 0)],
    [(0, 0), (0, 1), (0, 2), (0, 3)],
    [(0, 0), (1, 0), (2, 0), (3, 0)],
    [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)],
    [(0, 0), (1, 0), (1, 1)],
    [(0, 1), (1, 0), (1, 1)],
    [(0, 0), (0, 1), (1, 0), (1, 1)],
    [(0, 0), (0, 1), (1, 0)],
    [(0, 0), (0, 1), (0, 2), (1, 1)],
    [(0, 0), (1, 0), (1, 1), (2, 1)],
    [(0, 1), (1, 0), (1, 1), (2, 0)],
]

COLORS = [
    (255, 90, 90),
    (90, 200, 255),
    (255, 200, 80),
    (150, 255, 120),
    (200, 120, 255),
    (255, 150, 90),
    (100, 255, 200),
]

random.seed()


def load_highscore():
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return 0


def save_highscore(value):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(value))
    except Exception:
        pass


def rotate_shape(shape):
    rotated = [(c, -r) for (r, c) in shape]
    min_r = min(r for r, c in rotated)
    min_c = min(c for r, c in rotated)
    return [(r - min_r, c - min_c) for r, c in rotated]


class Piece:
    def __init__(self):
        self.shape = list(random.choice(SHAPES))
        self.color = random.choice(COLORS)
        self.x = 0
        self.y = 0
        self.drag_x = 0
        self.drag_y = 0
        self.cell = CELL_SIZE // 2

    def size_cells(self):
        mr = max(r for r, c in self.shape) + 1
        mc = max(c for r, c in self.shape) + 1
        return mr, mc


class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[0] * GRID_N for _ in range(GRID_N)]
        self.score = 0
        self.tray = [Piece() for _ in range(3)]
        self.dragging = None
        self.drag_dx = 0
        self.drag_dy = 0
        self.game_over = False
        self.clear_anim = []
        self.popups = []
        self.score_display = 0.0
        self.drag_moved = False
        self.drop_anim = []

    def can_place(self, shape, row, col):
        for dr, dc in shape:
            r, c = row + dr, col + dc
            if r < 0 or r >= GRID_N or c < 0 or c >= GRID_N:
                return False
            if self.board[r][c] != 0:
                return False
        return True

    def place(self, shape, color, row, col):
        for dr, dc in shape:
            self.board[row + dr][col + dc] = color

    def any_move_possible(self):
        for p in self.tray:
            for r in range(GRID_N):
                for c in range(GRID_N):
                    if self.can_place(p.shape, r, c):
                        return True
        return False

    def clear_lines(self):
        cleared_cells = []
        lines = 0
        for r in range(GRID_N):
            if all(self.board[r][c] != 0 for c in range(GRID_N)):
                for c in range(GRID_N):
                    cleared_cells.append((r, c, self.board[r][c]))
                lines += 1
        for c in range(GRID_N):
            if all(self.board[r][c] != 0 for r in range(GRID_N)):
                for r in range(GRID_N):
                    if (r, c, self.board[r][c]) not in cleared_cells:
                        cleared_cells.append((r, c, self.board[r][c]))
                lines += 1
        for r, c, _ in cleared_cells:
            self.board[r][c] = 0
        gained = 0
        if lines == 1:
            gained = 10
        elif lines == 2:
            gained = 30
        elif lines >= 3:
            gained = 60
        return cleared_cells, lines, gained


game = Game()
highscore = load_highscore()


def draw_cell(px, py, size, color, alpha=255):
    rect = pygame.Rect(px + 2, py + 2, size - 4, size - 4)
    if alpha >= 255:
        pygame.draw.rect(screen, color, rect, border_radius=8)
        pygame.draw.rect(screen, CELL_BORDER, rect, 2, border_radius=8)
    else:
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha), (2, 2, size - 4, size - 4), border_radius=8)
        screen.blit(s, (px, py))


def draw_board():
    pygame.draw.rect(screen, GRID_BG,
                     (BOARD_X - 5, BOARD_Y - 5, BOARD_SIZE + 10, BOARD_SIZE + 10),
                     border_radius=10)
    for r in range(GRID_N):
        for c in range(GRID_N):
            px = BOARD_X + c * CELL_SIZE
            py = BOARD_Y + r * CELL_SIZE
            if game.board[r][c] == 0:
                draw_cell(px, py, CELL_SIZE, CELL_EMPTY)
            else:
                draw_cell(px, py, CELL_SIZE, game.board[r][c])


def draw_shape(shape, color, px, py, cell, alpha=255):
    for dr, dc in shape:
        draw_cell(px + dc * cell, py + dr * cell, cell, color, alpha)


def draw_tray():
    tray_y = BOARD_Y + BOARD_SIZE + 70
    slot_w = WIDTH // 3
    tray_cell = CELL_SIZE // 2
    for i, p in enumerate(game.tray):
        if i == game.dragging:
            continue
        mr, mc = p.size_cells()
        w = mc * tray_cell
        h = mr * tray_cell
        cx = slot_w * i + slot_w // 2
        px = cx - w // 2
        py = tray_y
        p.x = px
        p.y = py
        p.cell = tray_cell
        draw_shape(p.shape, p.color, px, py, tray_cell)


def draw_hud():
    score_text = font_mid.render(f"Очки: {int(game.score_display)}", True, TEXT_COLOR)
    screen.blit(score_text, (30, 40))
    hs_text = font_small.render(f"Рекорд: {highscore}", True, ACCENT)
    screen.blit(hs_text, (WIDTH - hs_text.get_width() - 30, 50))


def draw_clear_anim():
    for r, c, color, prog in game.clear_anim:
        px = BOARD_X + c * CELL_SIZE
        py = BOARD_Y + r * CELL_SIZE
        t = prog
        blend = (
            min(255, int(color[0] + (255 - color[0]) * t)),
            min(255, int(color[1] + (255 - color[1]) * t)),
            min(255, int(color[2] + (255 - color[2]) * t)),
        )
        alpha = int(255 * (1 - t))
        draw_cell(px, py, CELL_SIZE, blend, alpha)


def draw_drop_anim():
    for r, c, color, t in game.drop_anim:
        px = BOARD_X + c * CELL_SIZE
        py = BOARD_Y + r * CELL_SIZE
        size = int(CELL_SIZE * (0.5 + 0.5 * t))
        offset = (CELL_SIZE - size) // 2
        rect = pygame.Rect(px + offset + 2, py + offset + 2, size - 4, size - 4)
        pygame.draw.rect(screen, color, rect, border_radius=8)


def draw_popups():
    for text, x, y, life in game.popups:
        surf = font_mid.render(text, True, ACCENT)
        surf.set_alpha(int(255 * min(1, life)))
        screen.blit(surf, (x - surf.get_width() // 2, y))


def draw_game_over():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))
    title = font_big.render("Игра окончена", True, TEXT_COLOR)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 150))
    sc = font_mid.render(f"Очки: {int(game.score_display)}", True, TEXT_COLOR)
    screen.blit(sc, (WIDTH // 2 - sc.get_width() // 2, HEIGHT // 2 - 40))
    hs = font_mid.render(f"Рекорд: {highscore}", True, ACCENT)
    screen.blit(hs, (WIDTH // 2 - hs.get_width() // 2, HEIGHT // 2 + 30))
    hint = font_small.render("Тапни, чтобы начать заново", True, TEXT_COLOR)
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 120))


def find_tray_piece_at(mx, my):
    for i, p in enumerate(game.tray):
        if i == game.dragging:
            continue
        mr, mc = p.size_cells()
        w = mc * p.cell
        h = mr * p.cell
        rect = pygame.Rect(p.x, p.y, w, h)
        if rect.collidepoint(mx, my):
            return i
    return None


def snap_to_board(p):
    rel_x = p.drag_x - BOARD_X
    rel_y = p.drag_y - BOARD_Y
    col = round(rel_x / CELL_SIZE)
    row = round(rel_y / CELL_SIZE)
    return row, col


def main():
    global highscore
    clock = pygame.time.Clock()

    while True:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

            if game.game_over:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    game.reset()
                continue

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                idx = find_tray_piece_at(mx, my)
                if idx is not None:
                    game.dragging = idx
                    game.drag_moved = False
                    p = game.tray[idx]
                    game.drag_dx = mx - p.x
                    game.drag_dy = my - p.y
                    p.drag_x = p.x
                    p.drag_y = p.y
                    SOUND_CLICK.play()

            elif event.type == pygame.MOUSEMOTION and game.dragging is not None:
                mx, my = event.pos
                p = game.tray[game.dragging]
                nx = mx - game.drag_dx
                ny = my - game.drag_dy
                if abs(nx - p.drag_x) > 5 or abs(ny - p.drag_y) > 5:
                    game.drag_moved = True
                p.drag_x = nx
                p.drag_y = ny

            elif event.type == pygame.MOUSEBUTTONUP:
                if game.dragging is not None:
                    p = game.tray[game.dragging]
                    if not game.drag_moved:
                        p.shape = rotate_shape(p.shape)
                    else:
                        row, col = snap_to_board(p)
                        if game.can_place(p.shape, row, col):
                            game.place(p.shape, p.color, row, col)
                            SOUND_PLACE.play()
                            for dr, dc in p.shape:
                                game.drop_anim.append([row + dr, col + dc, p.color, 0.0])
                            cleared, lines, gained = game.clear_lines()
                            if lines > 0:
                                for r, c, color in cleared:
                                    game.clear_anim.append([r, c, color, 0.0])
                                cx = BOARD_X + BOARD_SIZE // 2
                                cy = BOARD_Y + BOARD_SIZE // 2
                                game.popups.append([f"+{gained}", cx, cy, 1.0])
                                if lines >= 2:
                                    SOUND_COMBO.play()
                                else:
                                    SOUND_CLEAR.play()
                            game.score += gained
                            game.tray[game.dragging] = Piece()
                            if not game.any_move_possible():
                                game.game_over = True
                                SOUND_OVER.play()
                                if game.score > highscore:
                                    highscore = game.score
                                    save_highscore(highscore)
                    game.dragging = None

        target = game.score
        if game.score_display < target:
            game.score_display = min(target, game.score_display + 200 * dt)
        elif game.score_display > target:
            game.score_display = target

        new_anim = []
        for item in game.clear_anim:
            item[3] += dt / 0.25
            if item[3] < 1.0:
                new_anim.append(item)
        game.clear_anim = new_anim

        new_drop = []
        for item in game.drop_anim:
            item[3] += dt / 0.15
            if item[3] < 1.0:
                new_drop.append(item)
        game.drop_anim = new_drop

        new_popups = []
        for p in game.popups:
            p[2] -= 60 * dt
            p[3] -= dt
            if p[3] > 0:
                new_popups.append(p)
        game.popups = new_popups

        screen.fill(BG)
        draw_hud()
        draw_board()
        draw_drop_anim()
        draw_clear_anim()
        draw_tray()

        if game.dragging is not None:
            p = game.tray[game.dragging]
            row, col = snap_to_board(p)
            ok = game.can_place(p.shape, row, col)
            for dr, dc in p.shape:
                px = BOARD_X + (col + dc) * CELL_SIZE
                py = BOARD_Y + (row + dr) * CELL_SIZE
                if 0 <= row + dr < GRID_N and 0 <= col + dc < GRID_N:
                    if ok:
                        draw_cell(px, py, CELL_SIZE, p.color, alpha=160)
                    else:
                        draw_cell(px, py, CELL_SIZE, (255, 60, 60), alpha=160)
            draw_shape(p.shape, p.color, p.drag_x, p.drag_y, p.cell)

        draw_popups()

        if game.game_over:
            draw_game_over()

        pygame.display.flip()


if __name__ == "__main__":
    main()
