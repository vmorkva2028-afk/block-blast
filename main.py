import random
import os
import json
import math
from datetime import datetime, date
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.metrics import dp

GRID_N = 8

SHAPES = [
    [(0, 0)],
    [(0, 0), (0, 1)],
    [(0, 0), (1, 0)],
    [(0, 0), (0, 1), (0, 2)],
    [(0, 0), (1, 0), (2, 0)],
    [(0, 0), (0, 1), (0, 2), (0, 3)],
    [(0, 0), (0, 1), (1, 0), (1, 1)],
    [(0, 0), (0, 1), (1, 0)],
    [(0, 0), (0, 1), (0, 2), (1, 1)],
    [(0, 0), (1, 0), (1, 1)],
    [(0, 0), (0, 1), (1, 1), (1, 2)],
]

COLORS = [
    (1.0, 0.35, 0.35),
    (0.35, 0.78, 1.0),
    (1.0, 0.78, 0.31),
    (0.59, 1.0, 0.47),
    (0.78, 0.47, 1.0),
    (1.0, 0.59, 0.35),
    (0.39, 1.0, 0.78),
]

BG_TOP = (0.10, 0.12, 0.22)
BG_BOT = (0.05, 0.06, 0.12)
MENU_BG_TOP = (0.16, 0.35, 0.78)
MENU_BG_BOT = (0.08, 0.18, 0.52)
GRID_BG = (0.14, 0.16, 0.26)
CELL_EMPTY = (0.22, 0.24, 0.34)
CELL_BORDER = (0.40, 0.44, 0.60)
TEXT_COLOR = (0.95, 0.95, 1.0)
ACCENT = (1.0, 0.86, 0.35)
BTN_BG = (0.35, 0.45, 0.75)
BTN_GREEN = (0.35, 0.65, 0.4)
BTN_RED = (0.6, 0.3, 0.3)
BTN_ORANGE = (1.0, 0.62, 0.15)
BTN_BLUE = (0.20, 0.65, 0.85)

DIR = os.path.dirname(os.path.abspath(__file__))
HIGHSCORE_FILE = os.path.join(DIR, "highscore.json")
SETTINGS_FILE = os.path.join(DIR, "settings.json")
STATS_FILE = os.path.join(DIR, "stats.json")
DAILY_FILE = os.path.join(DIR, "daily.json")


def load_json(path, default):
    try:
        with open(path, "r") as f:
            data = json.load(f)
            if isinstance(default, dict):
                default.update(data)
            return default
    except Exception:
        return default


def save_json(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def load_highscore():
    return load_json(HIGHSCORE_FILE, {"highscore": 0}).get("highscore", 0)


def save_highscore(value):
    save_json(HIGHSCORE_FILE, {"highscore": value})


def load_settings():
    return load_json(SETTINGS_FILE, {
        "vibration": True,
        "sound": True,
        "bgm": True,
        "volume": 100,
        "graphics": "high",
    })


def save_settings(s):
    save_json(SETTINGS_FILE, s)


def load_stats():
    return load_json(STATS_FILE, {
        "games": 0,
        "total_score": 0,
        "best_score": 0,
        "lines_cleared": 0,
        "max_combo": 0,
        "total_time": 0,
    })


def save_stats(s):
    save_json(STATS_FILE, s)


def load_daily():
    return load_json(DAILY_FILE, {"last_reward": "", "streak": 0})


def save_daily(d):
    save_json(DAILY_FILE, d)


class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-220, 220)
        self.vy = random.uniform(-220, 280)
        self.color = color
        self.life = 1.0
        self.size = random.randint(5, 12)


class Popup:
    def __init__(self, text, x, y):
        self.text = text
        self.x = x
        self.y = y
        self.life = 1.0


class Piece:
    def __init__(self):
        self.shape = list(random.choice(SHAPES))
        self.color = random.choice(COLORS)
        self.x = 0
        self.y = 0
        self.w = 0
        self.h = 0

    def size_cells(self):
        mr = max(r for r, c in self.shape) + 1
        mc = max(c for r, c in self.shape) + 1
        return mr, mc


class Board(Widget):
    def __init__(self, on_game_over=None, **kwargs):
        super().__init__(**kwargs)
        self.on_game_over = on_game_over
        self.settings = load_settings()
        self.stats = load_stats()
        self.reset()
        self.highscore = load_highscore()
        self.bind(pos=self.update_layout, size=self.update_layout)
        Clock.schedule_interval(self.tick, 1 / 60)
        self.game_start_time = datetime.now()

    def reset(self):
        self.board = [[0] * GRID_N for _ in range(GRID_N)]
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.tray = [Piece() for _ in range(3)]
        self.dragging = None
        self.drag_dx = 0
        self.drag_dy = 0
        self.drag_moved = False
        self.cell = 0
        self.board_x = 0
        self.board_y = 0
        self.tray_y = 0
        self.tray_cell = 0
        self.game_over = False
        self.clear_anim = []
        self.drop_anim = []
        self.popups = []
        self.particles = []
        self.shake_t = 0.0
        self.pulse_t = 0.0
        self.time = 0.0
        self.hint_t = 0.0

    def update_layout(self, *args):
        w = min(self.width, self.height)
        self.cell = int(w / (GRID_N + 1))
        board_size = self.cell * GRID_N
        self.board_x = int((self.width - board_size) / 2)
        self.board_y = int(self.height - board_size - self.cell * 2.0)
        self.tray_y = int(self.board_y - self.cell * 2.2)
        self.tray_cell = int(self.cell * 0.7)
        self.position_tray()

    def position_tray(self):
        slot_w = self.width / 3
        for i, p in enumerate(self.tray):
            mr, mc = p.size_cells()
            w = mc * self.tray_cell
            h = mr * self.tray_cell
            cx = slot_w * i + slot_w / 2
            p.x = cx - w / 2
            p.y = self.tray_y
            p.w = w
            p.h = h

    def vibrate(self, ms=30):
        if not self.settings.get("vibration", True):
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            vibrator = PythonActivity.mActivity.getSystemService(Context.VIBRATOR_SERVICE)
            vibrator.vibrate(ms)
        except Exception:
            pass

    def can_place(self, shape, row, col):
        for dr, dc in shape:
            r, c = row + dr, col + dc
            if r < 0 or r >= GRID_N or c < 0 or c >= GRID_N:
                return False
            if self.board[r][c] != 0:
                return False
        return True

    def clear_lines(self):
        cleared = []
        lines = 0
        for r in range(GRID_N):
            if all(self.board[r][c] != 0 for c in range(GRID_N)):
                for c in range(GRID_N):
                    cleared.append((r, c, self.board[r][c]))
                    self.board[r][c] = 0
                lines += 1
        for c in range(GRID_N):
            if all(self.board[r][c] != 0 for r in range(GRID_N)):
                for r in range(GRID_N):
                    if (r, c, self.board[r][c]) not in cleared:
                        cleared.append((r, c, self.board[r][c]))
                    self.board[r][c] = 0
                lines += 1

        if lines > 0:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            multiplier = min(self.combo, 5)
        else:
            multiplier = 1

        if lines == 1:
            gained = 10 * multiplier
        elif lines == 2:
            gained = 30 * multiplier
        elif lines >= 3:
            gained = 60 * multiplier
        else:
            gained = 0

        self.score += gained
        self.stats["lines_cleared"] += lines

        if lines > 0:
            popup_text = f"+{gained}"
            if self.combo > 1:
                popup_text += f" x{self.combo}"
            cx = self.board_x + (self.cell * GRID_N) / 2
            cy = self.board_y + (self.cell * GRID_N) / 2
            self.popups.append(Popup(popup_text, cx, cy))

            for (r, c, color) in cleared:
                self.clear_anim.append([r, c, color, 0.0])
                if self.settings.get("graphics", "high") == "high":
                    px = self.board_x + c * self.cell + self.cell / 2
                    py = self.board_y + r * self.cell + self.cell / 2
                    for _ in range(3):
                        self.particles.append(Particle(px, py, color))

            if lines == 2:
                self.shake_t = 0.15
                self.pulse_t = 0.6
                self.vibrate(40)
            elif lines >= 3:
                self.shake_t = 0.3
                self.pulse_t = 1.0
                self.vibrate(60)
            else:
                self.vibrate(20)
        else:
            self.combo = 0

        return lines

    def any_move_possible(self):
        for p in self.tray:
            for r in range(GRID_N):
                for c in range(GRID_N):
                    if self.can_place(p.shape, r, c):
                        return True
        return False

    def find_hint(self):
        for i, p in enumerate(self.tray):
            for r in range(GRID_N):
                for c in range(GRID_N):
                    if self.can_place(p.shape, r, c):
                        return i, r, c
        return None

    def cell_at(self, x, y):
        col = int((x - self.board_x) / self.cell)
        row = int((y - self.board_y) / self.cell)
        return row, col

    def on_touch_down(self, touch):
        if self.game_over or self.dragging is not None:
            return False
        slot_w = self.width / 3
        for i, p in enumerate(self.tray):
            px = slot_w * i
            if px <= touch.x <= px + slot_w and self.tray_y - 40 <= touch.y <= self.tray_y + self.tray_cell * 4:
                self.dragging = i
                self.drag_moved = False
                self.drag_dx = touch.x - p.x
                self.drag_dy = touch.y - p.y
                return True
        return False

    def on_touch_move(self, touch):
        if self.dragging is None:
            return False
        p = self.tray[self.dragging]
        if abs(touch.x - (p.x + self.drag_dx)) > 5 or abs(touch.y - (p.y + self.drag_dy)) > 5:
            self.drag_moved = True
        p.x = touch.x - self.drag_dx
        p.y = touch.y - self.drag_dy
        return True

    def on_touch_up(self, touch):
        if self.dragging is None:
            return False
        p = self.tray[self.dragging]
        if not self.drag_moved:
            self.rotate(p)
            self.vibrate(15)
        else:
            row, col = self.cell_at(p.x + p.w / 2, p.y + p.h / 2)
            mr, mc = p.size_cells()
            row -= mr // 2
            col -= mc // 2
            if self.can_place(p.shape, row, col):
                for dr, dc in p.shape:
                    self.board[row + dr][col + dc] = p.color
                    self.drop_anim.append([row + dr, col + dc, p.color, 0.0])
                self.clear_lines()
                self.tray[self.dragging] = Piece()
                self.vibrate(15)
            self.position_tray()
        self.dragging = None

        if not self.any_move_possible():
            self.game_over = True
            if self.score > self.highscore:
                self.highscore = self.score
                save_highscore(self.highscore)
            self.stats["games"] += 1
            self.stats["total_score"] += self.score
            self.stats["best_score"] = max(self.stats["best_score"], self.score)
            elapsed = (datetime.now() - self.game_start_time).total_seconds()
            self.stats["total_time"] += int(elapsed)
            save_stats(self.stats)
            if self.on_game_over:
                self.on_game_over()
        return True

    def rotate(self, p):
        rotated = [(c, -r) for (r, c) in p.shape]
        min_r = min(r for r, c in rotated)
        min_c = min(c for r, c in rotated)
        p.shape = [(r - min_r, c - min_c) for r, c in rotated]

    def tick(self, dt):
        self.time += dt
        self.clear_anim = [[r, c, col, t + dt / 0.45] for (r, c, col, t) in self.clear_anim if t + dt / 0.45 < 1.0]
        self.drop_anim = [[r, c, col, t + dt / 0.18] for (r, c, col, t) in self.drop_anim if t + dt / 0.18 < 1.0]
        for p in self.popups:
            p.y += 80 * dt
            p.life -= dt * 1.2
        self.popups = [p for p in self.popups if p.life > 0]
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy -= 500 * dt
            p.life -= dt * 1.4
        self.particles = [p for p in self.particles if p.life > 0]
        if self.shake_t > 0:
            self.shake_t = max(0, self.shake_t - dt)
        if self.pulse_t > 0:
            self.pulse_t = max(0, self.pulse_t - dt)
        if self.hint_t > 0:
            self.hint_t = max(0, self.hint_t - dt)
        self.redraw()

    def redraw(self):
        self.canvas.clear()
        gfx = self.settings.get("graphics", "high")
        shake_x = shake_y = 0
        if gfx == "high" and self.shake_t > 0:
            amp = int(10 * (self.shake_t / 0.3))
            shake_x = random.randint(-amp, amp)
            shake_y = random.randint(-amp, amp)

        with self.canvas:
            if gfx == "high":
                t = (math.sin(self.time * 0.6) + 1) / 2
                r = BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t
                g = BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t
                b = BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t
                Color(r, g, b, 1)
            else:
                Color(*BG_TOP, 1)
            Rectangle(pos=(0, 0), size=(self.width, self.height))

            pad = 6
            if self.pulse_t > 0:
                extra = int(8 * abs(math.sin(self.pulse_t * 14)))
                pad += extra
            Color(*GRID_BG)
            RoundedRectangle(
                pos=(self.board_x - pad + shake_x, self.board_y - pad + shake_y),
                size=(self.cell * GRID_N + pad * 2, self.cell * GRID_N + pad * 2),
                radius=[18])
            Color(*CELL_BORDER)
            RoundedRectangle(
                pos=(self.board_x - pad + shake_x, self.board_y - pad + shake_y),
                size=(self.cell * GRID_N + pad * 2, self.cell * GRID_N + pad * 2),
                radius=[18])
            Color(*GRID_BG)
            RoundedRectangle(
                pos=(self.board_x - pad + 3 + shake_x, self.board_y - pad + 3 + shake_y),
                size=(self.cell * GRID_N + pad * 2 - 6, self.cell * GRID_N + pad * 2 - 6),
                radius=[15])

            for r in range(GRID_N):
                for c in range(GRID_N):
                    px = self.board_x + c * self.cell + shake_x
                    py = self.board_y + r * self.cell + shake_y
                    if self.board[r][c] == 0:
                        Color(*CELL_EMPTY)
                        RoundedRectangle(pos=(px + 2, py + 2),
                                         size=(self.cell - 4, self.cell - 4),
                                         radius=[8])
                    else:
                        self._draw_3d_cell(px, py, self.cell, self.board[r][c])

            for (r, c, color, t2) in self.drop_anim:
                px = self.board_x + c * self.cell + shake_x
                py = self.board_y + r * self.cell + shake_y
                size = int(self.cell * (0.4 + 0.6 * (1 - (1 - t2) ** 3)))
                offset = (self.cell - size) // 2
                Color(*color)
                RoundedRectangle(pos=(px + offset + 2, py + offset + 2),
                                 size=(size - 4, size - 4),
                                 radius=[8])

            for (r, c, color, t2) in self.clear_anim:
                px = self.board_x + c * self.cell + shake_x
                py = self.board_y + r * self.cell + shake_y
                if t2 < 0.3:
                    tt = t2 / 0.3
                    mix = (min(1, color[0] + (1 - color[0]) * tt),
                           min(1, color[1] + (1 - color[1]) * tt),
                           min(1, color[2] + (1 - color[2]) * tt), 1)
                    Color(*mix)
                    RoundedRectangle(pos=(px + 2, py + 2),
                                     size=(self.cell - 4, self.cell - 4),
                                     radius=[8])
                else:
                    tt = (t2 - 0.3) / 0.7
                    Color(1, 1, 1, 1 - tt)
                    RoundedRectangle(pos=(px + 2, py + 2),
                                     size=(self.cell - 4, self.cell - 4),
                                     radius=[8])

            if gfx == "high":
                for p in self.particles:
                    Color(p.color[0], p.color[1], p.color[2], p.life)
                    RoundedRectangle(pos=(p.x - p.size / 2, p.y - p.size / 2),
                                     size=(p.size, p.size),
                                     radius=[3])

            if self.hint_t > 0:
                hint = self.find_hint()
                if hint:
                    i, hr, hc = hint
                    p = self.tray[i]
                    for dr, dc in p.shape:
                        pr, pc = hr + dr, hc + dc
                        if 0 <= pr < GRID_N and 0 <= pc < GRID_N:
                            px = self.board_x + pc * self.cell + shake_x
                            py = self.board_y + pr * self.cell + shake_y
                            pulse = 0.4 + 0.4 * abs(math.sin(self.time * 8))
                            Color(1, 1, 1, pulse)
                            RoundedRectangle(pos=(px + 2, py + 2),
                                             size=(self.cell - 4, self.cell - 4),
                                             radius=[8])

            for i, p in enumerate(self.tray):
                if i == self.dragging:
                    continue
                for dr, dc in p.shape:
                    px = p.x + dc * self.tray_cell
                    py = p.y + dr * self.tray_cell
                    self._draw_3d_cell(px, py, self.tray_cell, p.color, no_shadow=True)

            if self.dragging is not None:
                p = self.tray[self.dragging]
                row, col = self.cell_at(p.x + p.w / 2, p.y + p.h / 2)
                mr, mc = p.size_cells()
                row -= mr // 2
                col -= mc // 2
                ok = self.can_place(p.shape, row, col)
                if ok:
                    for dr, dc in p.shape:
                        pr, pc = row + dr, col + dc
                        if 0 <= pr < GRID_N and 0 <= pc < GRID_N:
                            px = self.board_x + pc * self.cell + shake_x
                            py = self.board_y + pr * self.cell + shake_y
                            Color(p.color[0], p.color[1], p.color[2], 0.45)
                            RoundedRectangle(pos=(px + 2, py + 2),
                                             size=(self.cell - 4, self.cell - 4),
                                             radius=[8])
                if gfx != "low":
                    glow_r = 0.5 + 0.3 * abs(math.sin(self.time * 8))
                    Color(p.color[0], p.color[1], p.color[2], 0.15 * glow_r)
                    RoundedRectangle(pos=(p.x - 8, p.y - 8),
                                     size=(p.w + 16, p.h + 16),
                                     radius=[16])
                for dr, dc in p.shape:
                    px = p.x + dc * self.tray_cell
                    py = p.y + dr * self.tray_cell
                    self._draw_3d_cell(px, py, self.tray_cell, p.color, alpha=0.95)

    def _draw_3d_cell(self, px, py, size, color, alpha=1.0, no_shadow=False):
        if not no_shadow:
            Color(0, 0, 0, 0.3)
            RoundedRectangle(pos=(px + 3, py + 3),
                             size=(size - 4, size - 4),
                             radius=[10])
        Color(color[0], color[1], color[2], alpha)
        RoundedRectangle(pos=(px + 2, py + 2),
                         size=(size - 4, size - 4),
                         radius=[10])
        Color(min(1, color[0] + 0.3), min(1, color[1] + 0.3), min(1, color[2] + 0.3), 0.75 * alpha)
        RoundedRectangle(pos=(px + 4, py + size - 2 - (size // 3)),
                         size=(size - 8, (size // 3) - 6),
                         radius=[8])
        Color(1, 1, 1, 0.18 * alpha)
        RoundedRectangle(pos=(px + 2, py + 2),
                         size=(size - 4, size - 4),
                         radius=[10])


class GameRoot(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = load_settings()
        self.stats = load_stats()
        self.state = "menu"
        self.menu_widget = None
        self.scores_widget = None
        self.settings_widget = None
        self.stats_widget = None
        self.pause_widget = None
        self.game_over_widget = None
        self.board = None
        self.score_label = None
        self.record_label = None
        self.pause_btn = None
        self.hint_btn = None
        self.show_menu()

    def make_btn(self, text, y, cb, color=BTN_BG, size=(0.7, 0.08), font="26sp"):
        btn = Button(
            text=text,
            font_size=font,
            bold=True,
            size_hint=size,
            pos_hint={"center_x": 0.5, "center_y": y},
            background_color=(*color, 1),
            background_normal="",
            background_down="",
        )
        btn.bind(on_release=cb)
        return btn

    def clear_overlays(self):
        for w in [self.menu_widget, self.scores_widget, self.settings_widget,
                  self.stats_widget, self.pause_widget, self.game_over_widget]:
            if w and w.parent:
                self.remove_widget(w)
        self.menu_widget = None
        self.scores_widget = None
        self.settings_widget = None
        self.stats_widget = None
        self.pause_widget = None
        self.game_over_widget = None

    def draw_bg(self, overlay, top, bot):
        with overlay.canvas:
            Color(*top, 1)
            Rectangle(pos=(0, 0), size=(Window.width, Window.height))

    def show_menu(self):
        self.clear_overlays()
        if self.board:
            self.remove_widget(self.board)
            self.board = None
        for lbl in [self.score_label, self.record_label, self.pause_btn, self.hint_btn]:
            if lbl and lbl.parent:
                self.remove_widget(lbl)
        self.state = "menu"

        overlay = FloatLayout()
        with overlay.canvas:
            Color(*MENU_BG_TOP, 1)
            Rectangle(pos=(0, 0), size=(Window.width, Window.height))
            Color(0, 0, 0, 0.35)
            RoundedRectangle(pos=(-50, -100), size=(Window.width + 100, Window.height * 0.55), radius=[200])

        title = Label(
            text="BLOCK",
            font_size="72sp",
            bold=True,
            color=(1, 0.65, 0.1, 1),
            outline_width=6,
            outline_color=(0.6, 0.3, 0, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.86},
        )
        overlay.add_widget(title)

        title2 = Label(
            text="BLAST",
            font_size="72sp",
            bold=True,
            color=(0.3, 0.85, 1.0, 1),
            outline_width=6,
            outline_color=(0.05, 0.3, 0.6, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.76},
        )
        overlay.add_widget(title2)

        sub = Label(
            text="ADVENTURE MASTER",
            font_size="18sp",
            bold=True,
            color=(0.9, 0.95, 1, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.7},
        )
        overlay.add_widget(sub)

        daily = load_daily()
        streak = daily.get("streak", 0)
        streak_lbl = Label(
            text=f"🔥 Серия побед: {streak}",
            font_size="20sp",
            bold=True,
            color=(1, 0.9, 0.4, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.62},
        )
        overlay.add_widget(streak_lbl)

        overlay.add_widget(self.make_btn(
            "▶  КЛАССИК", 0.5, self.start_game, BTN_GREEN, size=(0.72, 0.09), font="28sp"))
        overlay.add_widget(self.make_btn(
            "🎮  БОЛЬШЕ ИГР", 0.4, self.show_stats, BTN_ORANGE, size=(0.72, 0.09), font="24sp"))
        overlay.add_widget(self.make_btn(
            "🏆  РЕКОРДЫ", 0.3, self.show_scores, BTN_BLUE, size=(0.72, 0.09), font="24sp"))
        overlay.add_widget(self.make_btn(
            "⚙  НАСТРОЙКИ", 0.2, self.show_settings, (0.4, 0.45, 0.65), size=(0.72, 0.09), font="24sp"))

        self.menu_widget = overlay
        self.add_widget(overlay)

    def show_stats(self):
        self.clear_overlays()
        overlay = FloatLayout()
        self.draw_bg(overlay, MENU_BG_TOP, MENU_BG_BOT)

        title = Label(
            text="СТАТИСТИКА",
            font_size="42sp",
            bold=True,
            color=ACCENT,
            outline_width=4,
            outline_color=(0.3, 0.15, 0, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.88},
        )
        overlay.add_widget(title)

        s = self.stats
        rows = [
            f"🎮 Игр сыграно: {s.get('games', 0)}",
            f"🏆 Лучший счёт: {s.get('best_score', 0)}",
            f"⭐ Всего очков: {s.get('total_score', 0)}",
            f"📊 Линий очищено: {s.get('lines_cleared', 0)}",
            f"🔥 Макс. комбо: x{s.get('max_combo', 0)}",
            f"⏱ Время в игре: {s.get('total_time', 0) // 60} мин",
        ]
        y = 0.75
        for r in rows:
            lbl = Label(
                text=r,
                font_size="22sp",
                color=TEXT_COLOR,
                pos_hint={"center_x": 0.5, "center_y": y},
            )
            overlay.add_widget(lbl)
            y -= 0.08

        overlay.add_widget(self.make_btn("Назад", 0.18, self.show_menu, BTN_GREEN))
        self.stats_widget = overlay
        self.add_widget(overlay)

    def show_scores(self):
        self.clear_overlays()
        overlay = FloatLayout()
        self.draw_bg(overlay, MENU_BG_TOP, MENU_BG_BOT)

        title = Label(
            text="РЕКОРДЫ",
            font_size="52sp",
            bold=True,
            color=ACCENT,
            outline_width=5,
            outline_color=(0.3, 0.15, 0, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.82},
        )
        overlay.add_widget(title)

        hs = load_highscore()
        medal = Label(
            text="🏆" if hs > 0 else "—",
            font_size="90sp",
            pos_hint={"center_x": 0.5, "center_y": 0.68},
        )
        overlay.add_widget(medal)

        score_lbl = Label(
            text=f"{hs}",
            font_size="52sp",
            bold=True,
            color=TEXT_COLOR,
            pos_hint={"center_x": 0.5, "center_y": 0.56},
        )
        overlay.add_widget(score_lbl)

        overlay.add_widget(self.make_btn("Назад", 0.22, self.show_menu, BTN_GREEN))
        self.scores_widget = overlay
        self.add_widget(overlay)

    def show_settings(self):
        self.clear_overlays()
        overlay = FloatLayout()
        self.draw_bg(overlay, MENU_BG_TOP, MENU_BG_BOT)

        title = Label(
            text="НАСТРОЙКИ",
            font_size="42sp",
            bold=True,
            color=ACCENT,
            outline_width=4,
            outline_color=(0.3, 0.15, 0, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.9},
        )
        overlay.add_widget(title)

        # Иконки сверху: Sound / BGM / Vibration
        icons_y = 0.79
        sound_state = "🔊" if self.settings.get("sound", True) else "🔇"
        bgm_state = "🎵" if self.settings.get("bgm", True) else "🎵"
        vib_state = "📳" if self.settings.get("vibration", True) else "📴"

        snd_btn = Button(
            text=f"{sound_state}\nSound",
            font_size="16sp",
            size_hint=(0.22, 0.1),
            pos_hint={"center_x": 0.2, "center_y": icons_y},
            background_color=(*BTN_BG, 1),
            background_normal="",
            background_down="",
        )
        snd_btn.bind(on_release=self.toggle_sound)
        overlay.add_widget(snd_btn)

        bgm_btn = Button(
            text=f"{bgm_state}\nBGM",
            font_size="16sp",
            size_hint=(0.22, 0.1),
            pos_hint={"center_x": 0.5, "center_y": icons_y},
            background_color=(*BTN_BG, 1),
            background_normal="",
            background_down="",
        )
        bgm_btn.bind(on_release=self.toggle_bgm)
        overlay.add_widget(bgm_btn)

        vib_btn = Button(
            text=f"{vib_state}\nVibration",
            font_size="16sp",
            size_hint=(0.22, 0.1),
            pos_hint={"center_x": 0.8, "center_y": icons_y},
            background_color=(*BTN_BG, 1),
            background_normal="",
            background_down="",
        )
        vib_btn.bind(on_release=self.toggle_vib)
        overlay.add_widget(vib_btn)

        # Кнопки-список
        vol = self.settings.get("volume", 100)
        vol_btn = self.make_btn(f"🔉 Громкость: {vol}%", 0.66, self.cycle_volume, BTN_BLUE, size=(0.72, 0.07), font="22sp")
        overlay.add_widget(vol_btn)

        gfx = self.settings.get("graphics", "high")
        gfx_names = {"high": "Высокая", "medium": "Средняя", "low": "Низкая"}
        gfx_btn = self.make_btn(f"🎨 Графика: {gfx_names.get(gfx, 'Высокая')}", 0.58, self.cycle_graphics, BTN_BLUE, size=(0.72, 0.07), font="22sp")
        overlay.add_widget(gfx_btn)

        reset_btn = self.make_btn("🏠 Сбросить рекорд", 0.49, self.confirm_reset, BTN_RED, size=(0.72, 0.07), font="22sp")
        overlay.add_widget(reset_btn)

        overlay.add_widget(self.make_btn("← Назад", 0.3, self.show_menu, BTN_GREEN))
        self.settings_widget = overlay
        self.add_widget(overlay)

    def toggle_vib(self, *a):
        self.settings["vibration"] = not self.settings.get("vibration", True)
        save_settings(self.settings)
        self.show_settings()

    def toggle_sound(self, *a):
        self.settings["sound"] = not self.settings.get("sound", True)
        save_settings(self.settings)
        self.show_settings()

    def toggle_bgm(self, *a):
        self.settings["bgm"] = not self.settings.get("bgm", True)
        save_settings(self.settings)
        self.show_settings()

    def cycle_volume(self, *a):
        volumes = [0, 25, 50, 75, 100]
        cur = self.settings.get("volume", 100)
        try:
            idx = volumes.index(cur)
        except ValueError:
            idx = 4
        self.settings["volume"] = volumes[(idx + 1) % len(volumes)]
        save_settings(self.settings)
        self.show_settings()

    def cycle_graphics(self, *a):
        modes = ["high", "medium", "low"]
        cur = self.settings.get("graphics", "high")
        try:
            idx = modes.index(cur)
        except ValueError:
            idx = 0
        self.settings["graphics"] = modes[(idx + 1) % len(modes)]
        save_settings(self.settings)
        self.show_settings()

    def confirm_reset(self, *a):
        self.clear_overlays()
        overlay = FloatLayout()
        self.draw_bg(overlay, MENU_BG_TOP, MENU_BG_BOT)
        t = Label(
            text="Сбросить рекорд?",
            font_size="36sp",
            bold=True,
            color=TEXT_COLOR,
            pos_hint={"center_x": 0.5, "center_y": 0.65},
        )
        overlay.add_widget(t)
        i = Label(
            text="Это нельзя отменить",
            font_size="20sp",
            color=(0.85, 0.85, 0.95, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.57},
        )
        overlay.add_widget(i)

        overlay.add_widget(self.make_btn("Да, сбросить", 0.44, self.do_reset, BTN_RED))
        overlay.add_widget(self.make_btn("Отмена", 0.33, self.show_settings, BTN_GREEN))
        self.settings_widget = overlay
        self.add_widget(overlay)

    def do_reset(self, *a):
        save_highscore(0)
        if self.board:
            self.board.highscore = 0
        self.show_settings()

    def start_game(self, *a):
        self.clear_overlays()
        for lbl in [self.score_label, self.record_label, self.pause_btn, self.hint_btn]:
            if lbl and lbl.parent:
                self.remove_widget(lbl)
        self.state = "game"
        self.board = Board(on_game_over=self.show_game_over)
        self.board.settings = self.settings
        self.add_widget(self.board)

        self.score_label = Label(
            text="Очки: 0",
            font_size="34sp",
            bold=True,
            color=TEXT_COLOR,
            outline_width=3,
            outline_color=(0, 0, 0, 1),
            pos_hint={"x": 0.03, "top": 0.98},
            size_hint=(0.6, 0.07),
            halign="left",
            valign="middle",
        )
        self.add_widget(self.score_label)

        self.record_label = Label(
            text=f"Рекорд: {load_highscore()}",
            font_size="22sp",
            color=ACCENT,
            pos_hint={"right": 0.97, "top": 0.98},
            size_hint=(0.4, 0.07),
            halign="right",
            valign="middle",
        )
        self.add_widget(self.record_label)

        self.pause_btn = Button(
            text="II",
            font_size="22sp",
            bold=True,
            size_hint=(None, None),
            size=(dp(60), dp(60)),
            pos_hint={"right": 0.97, "top": 0.90},
            background_color=(*BTN_BG, 1),
            background_normal="",
            background_down="",
        )
        self.pause_btn.bind(on_release=self.toggle_pause)
        self.add_widget(self.pause_btn)

        self.hint_btn = Button(
            text="?",
            font_size="22sp",
            bold=True,
            size_hint=(None, None),
            size=(dp(60), dp(60)),
            pos_hint={"right": 0.97, "top": 0.82},
            background_color=(0.5, 0.4, 0.7, 1),
            background_normal="",
            background_down="",
        )
        self.hint_btn.bind(on_release=self.use_hint)
        self.add_widget(self.hint_btn)

        Clock.schedule_interval(self.update_hud, 0.1)

    def use_hint(self, *a):
        if self.board:
            self.board.hint_t = 2.0

    def update_hud(self, dt):
        if self.board and self.state == "game":
            self.score_label.text = f"Очки: {self.board.score}"
            if self.board.highscore > 0:
                self.record_label.text = f"Рекорд: {self.board.highscore}"

    def toggle_pause(self, *a):
        if self.state not in ("game", "paused"):
            return
        if self.pause_widget:
            self.remove_widget(self.pause_widget)
            self.pause_widget = None
            self.state = "game"
        else:
            self.state = "paused"
            overlay = FloatLayout()
            with overlay.canvas:
                Color(0, 0, 0, 0.78)
                Rectangle(pos=(0, 0), size=Window.size)
            title = Label(
                text="ПАУЗА",
                font_size="56sp",
                bold=True,
                color=ACCENT,
                outline_width=5,
                outline_color=(0.3, 0.15, 0, 1),
                pos_hint={"center_x": 0.5, "center_y": 0.72},
            )
            overlay.add_widget(title)
            overlay.add_widget(self.make_btn("Продолжить", 0.5, self.toggle_pause, BTN_GREEN))
            overlay.add_widget(self.make_btn("В меню", 0.38, self.go_menu))
            self.pause_widget = overlay
            self.add_widget(overlay)

    def go_menu(self, *a):
        self.clear_overlays()
        if self.board:
            self.remove_widget(self.board)
            self.board = None
        for lbl in [self.score_label, self.record_label, self.pause_btn, self.hint_btn]:
            if lbl and lbl.parent:
                self.remove_widget(lbl)
        try:
            Clock.unschedule(self.update_hud)
        except Exception:
            pass
        self.show_menu()

    def show_game_over(self):
        if self.game_over_widget:
            return
        hs = load_highscore()
        overlay = FloatLayout()
        with overlay.canvas:
            Color(0, 0, 0, 0.85)
            Rectangle(pos=(0, 0), size=Window.size)

        title = Label(
            text="ИГРА ОКОНЧЕНА",
            font_size="48sp",
            bold=True,
            color=(1, 0.4, 0.4, 1),
            outline_width=4,
            outline_color=(0.3, 0, 0, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.78},
        )
        overlay.add_widget(title)

        score_lbl = Label(
            text=f"Очки: {self.board.score}",
            font_size="38sp",
            bold=True,
            color=TEXT_COLOR,
            pos_hint={"center_x": 0.5, "center_y": 0.64},
        )
        overlay.add_widget(score_lbl)

        record_lbl = Label(
            text=f"Рекорд: {hs}",
            font_size="30sp",
            color=ACCENT,
            pos_hint={"center_x": 0.5, "center_y": 0.56},
        )
        overlay.add_widget(record_lbl)

        if self.board.score >= hs and self.board.score > 0:
            nr = Label(
                text="✨ НОВЫЙ РЕКОРД! ✨",
                font_size="26sp",
                bold=True,
                color=ACCENT,
                pos_hint={"center_x": 0.5, "center_y": 0.48},
            )
            overlay.add_widget(nr)

        overlay.add_widget(self.make_btn("Играть заново", 0.35, self.restart_game, BTN_GREEN))
        overlay.add_widget(self.make_btn("В меню", 0.24, self.go_menu))
        self.game_over_widget = overlay
        self.add_widget(overlay)

    def restart_game(self, *a):
        if self.game_over_widget:
            self.remove_widget(self.game_over_widget)
            self.game_over_widget = None
        if self.board:
            self.board.reset()
            self.board.highscore = load_highscore()
            self.board.settings = self.settings
            self.board.stats = load_stats()
            self.board.game_start_time = datetime.now()
        self.state = "game"


class BlockBlastApp(App):
    def build(self):
        Window.clearcolor = (0.05, 0.06, 0.12, 1)
        return GameRoot()


if __name__ == "__main__":
    BlockBlastApp().run()
