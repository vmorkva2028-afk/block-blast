import random
import os
import json
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.core.window import Window
from kivy.clock import Clock

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
]

COLORS = [
    (1.0, 0.35, 0.35, 1),
    (0.35, 0.78, 1.0, 1),
    (1.0, 0.78, 0.31, 1),
    (0.59, 1.0, 0.47, 1),
    (0.78, 0.47, 1.0, 1),
    (1.0, 0.59, 0.35, 1),
    (0.39, 1.0, 0.78, 1),
]

BG_COLOR = (0.08, 0.10, 0.16, 1)
GRID_BG = (0.16, 0.18, 0.28, 1)
CELL_EMPTY = (0.24, 0.26, 0.36, 1)
CELL_BORDER = (0.42, 0.46, 0.62, 1)
TEXT_COLOR = (0.95, 0.95, 1.0, 1)
ACCENT = (1.0, 0.86, 0.35, 1)

DIR = os.path.dirname(os.path.abspath(__file__))
HIGHSCORE_FILE = os.path.join(DIR, "highscore.json")


def load_highscore():
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            return json.load(f).get("highscore", 0)
    except Exception:
        return 0


def save_highscore(value):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            json.dump({"highscore": value}, f)
    except Exception:
        pass


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


class Popup:
    def __init__(self, text, x, y):
        self.text = text
        self.x = x
        self.y = y
        self.life = 1.0


class Board(Widget):
    def __init__(self, on_game_over=None, **kwargs):
        super().__init__(**kwargs)
        self.on_game_over = on_game_over
        self.reset()
        self.highscore = load_highscore()
        self.bind(pos=self.update_layout, size=self.update_layout)
        Clock.schedule_interval(self.tick, 1 / 60)

    def reset(self):
        self.board = [[0] * GRID_N for _ in range(GRID_N)]
        self.score = 0
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
        self.clear_anim = []      # [(r, c, color, t)]
        self.drop_anim = []       # [(r, c, color, t)]
        self.popups = []          # [Popup]
        self.shake_t = 0.0
        self.pulse_t = 0.0

    def update_layout(self, *args):
        w = min(self.width, self.height)
        self.cell = int(w / (GRID_N + 1))
        board_size = self.cell * GRID_N
        self.board_x = int((self.width - board_size) / 2)
        self.board_y = int(self.height - board_size - self.cell * 1.8)
        self.tray_y = int(self.board_y - self.cell * 2.0)
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
        if lines == 1:
            self.score += 10
            popup_text = "+10"
        elif lines == 2:
            self.score += 30
            popup_text = "+30"
            self.shake_t = 0.15
            self.pulse_t = 0.6
        elif lines >= 3:
            self.score += 60
            popup_text = "+60"
            self.shake_t = 0.25
            self.pulse_t = 1.0
        else:
            popup_text = None
        if lines > 0 and popup_text:
            cx = self.board_x + (self.cell * GRID_N) / 2
            cy = self.board_y + (self.cell * GRID_N) / 2
            self.popups.append(Popup(popup_text, cx, cy))
            for (r, c, color) in cleared:
                self.clear_anim.append([r, c, color, 0.0])
        return lines

    def any_move_possible(self):
        for p in self.tray:
            for r in range(GRID_N):
                for c in range(GRID_N):
                    if self.can_place(p.shape, r, c):
                        return True
        return False

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
            self.position_tray()
        self.dragging = None

        if not self.any_move_possible():
            self.game_over = True
            if self.score > self.highscore:
                self.highscore = self.score
                save_highscore(self.highscore)
            if self.on_game_over:
                self.on_game_over()
        return True

    def rotate(self, p):
        rotated = [(c, -r) for (r, c) in p.shape]
        min_r = min(r for r, c in rotated)
        min_c = min(c for r, c in rotated)
        p.shape = [(r - min_r, c - min_c) for r, c in rotated]

    def tick(self, dt):
        # обновление анимаций
        self.clear_anim = [[r, c, col, t + dt / 0.4] for (r, c, col, t) in self.clear_anim if t + dt / 0.4 < 1.0]
        self.drop_anim = [[r, c, col, t + dt / 0.18] for (r, c, col, t) in self.drop_anim if t + dt / 0.18 < 1.0]
        for p in self.popups:
            p.y += 80 * dt
            p.life -= dt * 1.2
        self.popups = [p for p in self.popups if p.life > 0]
        if self.shake_t > 0:
            self.shake_t = max(0, self.shake_t - dt)
        if self.pulse_t > 0:
            self.pulse_t = max(0, self.pulse_t - dt)

    def redraw(self):
        self.canvas.clear()
        import math
        shake_x = shake_y = 0
        if self.shake_t > 0:
            amp = int(10 * (self.shake_t / 0.25))
            shake_x = random.randint(-amp, amp)
            shake_y = random.randint(-amp, amp)

        with self.canvas:
            Color(*BG_COLOR)
            Rectangle(pos=(0, 0), size=(self.width, self.height))

            # Заголовок / очки сверху
            # (текст рисуется через Label в GameRoot, не тут)

            # Сетка
            pad = 6
            if self.pulse_t > 0:
                extra = int(6 * abs(math.sin(self.pulse_t * 12)))
                pad += extra
            Color(*GRID_BG)
            RoundedRectangle(
                pos=(self.board_x - pad + shake_x, self.board_y - pad + shake_y),
                size=(self.cell * GRID_N + pad * 2, self.cell * GRID_N + pad * 2),
                radius=[16])
            Color(*CELL_BORDER)
            RoundedRectangle(
                pos=(self.board_x - pad + shake_x, self.board_y - pad + shake_y),
                size=(self.cell * GRID_N + pad * 2, self.cell * GRID_N + pad * 2),
                radius=[16])
            Color(*GRID_BG)
            RoundedRectangle(
                pos=(self.board_x - pad + 2 + shake_x, self.board_y - pad + 2 + shake_y),
                size=(self.cell * GRID_N + pad * 2 - 4, self.cell * GRID_N + pad * 2 - 4),
                radius=[14])

            # Клетки
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

            # Анимация приземления
            for (r, c, color, t) in self.drop_anim:
                px = self.board_x + c * self.cell + shake_x
                py = self.board_y + r * self.cell + shake_y
                size = int(self.cell * (0.4 + 0.6 * (1 - (1 - t) ** 3)))
                offset = (self.cell - size) // 2
                Color(*color)
                RoundedRectangle(pos=(px + offset + 2, py + offset + 2),
                                 size=(size - 4, size - 4),
                                 radius=[8])

            # Анимация очистки
            for (r, c, color, t) in self.clear_anim:
                px = self.board_x + c * self.cell + shake_x
                py = self.board_y + r * self.cell + shake_y
                if t < 0.3:
                    tt = t / 0.3
                    mix = (min(1, color[0] + (1 - color[0]) * tt),
                           min(1, color[1] + (1 - color[1]) * tt),
                           min(1, color[2] + (1 - color[2]) * tt), 1)
                    Color(*mix)
                    RoundedRectangle(pos=(px + 2, py + 2),
                                     size=(self.cell - 4, self.cell - 4),
                                     radius=[8])
                else:
                    tt = (t - 0.3) / 0.7
                    Color(1, 1, 1, 1 - tt)
                    RoundedRectangle(pos=(px + 2, py + 2),
                                     size=(self.cell - 4, self.cell - 4),
                                     radius=[8])

            # Лоток
            for i, p in enumerate(self.tray):
                if i == self.dragging:
                    continue
                for dr, dc in p.shape:
                    px = p.x + dc * self.tray_cell
                    py = p.y + dr * self.tray_cell
                    self._draw_3d_cell(px, py, self.tray_cell, p.color, no_shadow=True)

            # Перетаскиваемая фигура
            if self.dragging is not None:
                p = self.tray[self.dragging]
                # preview на поле
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
                            Color(p.color[0], p.color[1], p.color[2], 0.5)
                            RoundedRectangle(pos=(px + 2, py + 2),
                                             size=(self.cell - 4, self.cell - 4),
                                             radius=[8])
                # сама фигура
                for dr, dc in p.shape:
                    px = p.x + dc * self.tray_cell
                    py = p.y + dr * self.tray_cell
                    self._draw_3d_cell(px, py, self.tray_cell, p.color, alpha=0.9)

            # Всплывающие очки — рисуются в GameRoot

    def _draw_3d_cell(self, px, py, size, color, alpha=1.0, no_shadow=False):
        # тень
        if not no_shadow:
            Color(0, 0, 0, 0.25)
            RoundedRectangle(pos=(px + 3, py + 3),
                             size=(size - 4, size - 4),
                             radius=[10])
        # тело
        Color(color[0], color[1], color[2], alpha)
        RoundedRectangle(pos=(px + 2, py + 2),
                         size=(size - 4, size - 4),
                         radius=[10])
        # блик сверху
        Color(min(1, color[0] + 0.25), min(1, color[1] + 0.25), min(1, color[2] + 0.25), 0.7 * alpha)
        RoundedRectangle(pos=(px + 4, py + size - 2 - (size // 3)),
                         size=(size - 8, (size // 3) - 6),
                         radius=[8])
        # рамка
        Color(1, 1, 1, 0.15 * alpha)
        RoundedRectangle(pos=(px + 2, py + 2),
                         size=(size - 4, size - 4),
                         radius=[10])


class GameRoot(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.board = Board(on_game_over=self.show_game_over)
        self.add_widget(self.board)

        # Очки и рекорд
        self.score_label = Label(
            text="Очки: 0",
            font_size="34sp",
            bold=True,
            color=TEXT_COLOR,
            pos_hint={"x": 0.03, "top": 0.98},
            size_hint=(0.6, 0.08),
            halign="left",
            valign="middle",
        )
        self.add_widget(self.score_label)

        self.record_label = Label(
            text=f"Рекорд: {load_highscore()}",
            font_size="22sp",
            color=ACCENT,
            pos_hint={"right": 0.97, "top": 0.98},
            size_hint=(0.4, 0.08),
            halign="right",
            valign="middle",
        )
        self.add_widget(self.record_label)

        # Пауза
        self.pause_btn = Button(
            text="II",
            font_size="22sp",
            size_hint=(None, None),
            size=("60dp", "60dp"),
            pos_hint={"right": 0.97, "top": 0.90},
            background_color=(0.4, 0.45, 0.7, 1),
        )
        self.pause_btn.bind(on_release=self.toggle_pause)
        self.add_widget(self.pause_btn)

        self.paused = False
        self.game_over_overlay = None
        Clock.schedule_interval(self.update_hud, 0.1)

    def update_hud(self, dt):
        self.score_label.text = f"Очки: {self.board.score}"
        if self.board.highscore > 0:
            self.record_label.text = f"Рекорд: {self.board.highscore}"

    def toggle_pause(self, *args):
        self.paused = not self.paused
        self.board.disabled = self.paused

    def show_game_over(self):
        if self.game_over_overlay:
            return
        overlay = FloatLayout()
        with overlay.canvas:
            Color(0, 0, 0, 0.75)
            Rectangle(pos=(0, 0), size=Window.size)
        title = Label(
            text="Игра окончена",
            font_size="52sp",
            bold=True,
            color=TEXT_COLOR,
            pos_hint={"center_x": 0.5, "center_y": 0.7},
        )
        overlay.add_widget(title)
        sc = Label(
            text=f"Очки: {self.board.score}",
            font_size="34sp",
            color=TEXT_COLOR,
            pos_hint={"center_x": 0.5, "center_y": 0.55},
        )
        overlay.add_widget(sc)
        rec = Label(
            text=f"Рекорд: {self.board.highscore}",
            font_size="28sp",
            color=ACCENT,
            pos_hint={"center_x": 0.5, "center_y": 0.47},
        )
        overlay.add_widget(rec)
        btn = Button(
            text="Играть заново",
            font_size="26sp",
            size_hint=(0.6, 0.09),
            pos_hint={"center_x": 0.5, "center_y": 0.32},
            background_color=(0.4, 0.7, 0.4, 1),
        )
        btn.bind(on_release=lambda *a: self.restart())
        overlay.add_widget(btn)
        self.game_over_overlay = overlay
        self.add_widget(overlay)

    def restart(self):
        if self.game_over_overlay:
            self.remove_widget(self.game_over_overlay)
            self.game_over_overlay = None
        self.board.reset()
        self.board.highscore = load_highscore()


class BlockBlastApp(App):
    def build(self):
        Window.clearcolor = BG_COLOR
        return GameRoot()


if __name__ == "__main__":
    BlockBlastApp().run()
