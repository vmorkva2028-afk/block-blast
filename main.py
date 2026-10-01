import random
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
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
    (1, 0.35, 0.35, 1),
    (0.35, 0.78, 1, 1),
    (1, 0.78, 0.31, 1),
    (0.59, 1, 0.47, 1),
    (0.78, 0.47, 1, 1),
    (1, 0.59, 0.35, 1),
    (0.39, 1, 0.78, 1),
]


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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.board = [[0] * GRID_N for _ in range(GRID_N)]
        self.score = 0
        self.highscore = 0
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
        self.bind(pos=self.update_layout, size=self.update_layout)
        Clock.schedule_interval(self.redraw, 1 / 60)

    def update_layout(self, *args):
        w = min(self.width, self.height)
        self.cell = int(w / (GRID_N + 1))
        board_size = self.cell * GRID_N
        self.board_x = int((self.width - board_size) / 2)
        self.board_y = int(self.height - board_size - self.cell * 1.5)
        self.tray_y = int(self.board_y - self.cell * 1.8)
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

    def new_piece(self):
        return Piece()

    def can_place(self, shape, row, col):
        for dr, dc in shape:
            r, c = row + dr, col + dc
            if r < 0 or r >= GRID_N or c < 0 or c >= GRID_N:
                return False
            if self.board[r][c] != 0:
                return False
        return True

    def clear_lines(self):
        lines = 0
        for r in range(GRID_N):
            if all(self.board[r][c] != 0 for c in range(GRID_N)):
                for c in range(GRID_N):
                    self.board[r][c] = 0
                lines += 1
        for c in range(GRID_N):
            if all(self.board[r][c] != 0 for r in range(GRID_N)):
                for r in range(GRID_N):
                    self.board[r][c] = 0
                lines += 1
        if lines == 1:
            self.score += 10
        elif lines == 2:
            self.score += 30
        elif lines >= 3:
            self.score += 60
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
        if self.dragging is not None:
            return False
        slot_w = self.width / 3
        for i, p in enumerate(self.tray):
            px = slot_w * i
            if px <= touch.x <= px + slot_w and self.tray_y - 30 <= touch.y <= self.tray_y + self.tray_cell * 4:
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
                self.clear_lines()
                self.tray[self.dragging] = Piece()
            self.position_tray()
        self.dragging = None
        if not self.any_move_possible():
            self.reset_game()
        return True

    def rotate(self, p):
        rotated = [(c, -r) for (r, c) in p.shape]
        min_r = min(r for r, c in rotated)
        min_c = min(c for r, c in rotated)
        p.shape = [(r - min_r, c - min_c) for r, c in rotated]

    def reset_game(self):
        self.board = [[0] * GRID_N for _ in range(GRID_N)]
        self.score = 0
        self.tray = [Piece() for _ in range(3)]
        self.position_tray()

    def redraw(self, dt):
        self.canvas.clear()
        with self.canvas:
            Color(0.08, 0.08, 0.12, 1)
            Rectangle(pos=(0, 0), size=(self.width, self.height))

            # сетка
            Color(0.16, 0.16, 0.24, 1)
            RoundedRectangle(pos=(self.board_x - 5, self.board_y - 5),
                             size=(self.cell * GRID_N + 10, self.cell * GRID_N + 10),
                             radius=[12])

            for r in range(GRID_N):
                for c in range(GRID_N):
                    px = self.board_x + c * self.cell
                    py = self.board_y + r * self.cell
                    if self.board[r][c] == 0:
                        Color(0.27, 0.27, 0.35, 1)
                    else:
                        Color(*self.board[r][c])
                    RoundedRectangle(pos=(px + 2, py + 2),
                                     size=(self.cell - 4, self.cell - 4),
                                     radius=[8])

            # tray
            for i, p in enumerate(self.tray):
                if i == self.dragging:
                    continue
                for dr, dc in p.shape:
                    px = p.x + dc * self.tray_cell
                    py = p.y + dr * self.tray_cell
                    Color(*p.color)
                    RoundedRectangle(pos=(px + 2, py + 2),
                                     size=(self.tray_cell - 4, self.tray_cell - 4),
                                     radius=[6])

            # dragging piece
            if self.dragging is not None:
                p = self.tray[self.dragging]
                for dr, dc in p.shape:
                    px = p.x + dc * self.tray_cell
                    py = p.y + dr * self.tray_cell
                    Color(p.color[0], p.color[1], p.color[2], 0.8)
                    RoundedRectangle(pos=(px + 2, py + 2),
                                     size=(self.tray_cell - 4, self.tray_cell - 4),
                                     radius=[6])


class GameRoot(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.board = Board(size_hint=(1, 1))
        self.add_widget(self.board)
        self.score_label = Label(
            text="Очки: 0",
            font_size="32sp",
            pos_hint={"x": 0.03, "top": 0.98},
            size_hint=(0.4, 0.1),
            halign="left",
            valign="top",
        )
        self.add_widget(self.score_label)
        Clock.schedule_interval(self.update_score, 0.2)

    def update_score(self, dt):
        self.score_label.text = f"Очки: {self.board.score}"


class BlockBlastApp(App):
    def build(self):
        Window.clearcolor = (0.08, 0.08, 0.12, 1)
        return GameRoot()


if __name__ == "__main__":
    BlockBlastApp().run()
