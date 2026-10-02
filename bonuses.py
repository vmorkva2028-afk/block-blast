"""Модуль бонусов для Block Blast."""

BONUS_LIMITS = {
    "bomb": 2,
    "shuffle": 2,
    "freeze": 1,
    "undo": 3,
}

BONUS_SYMBOLS = {
    "bomb": "B",
    "shuffle": "S",
    "freeze": "F",
    "undo": "U",
}

BONUS_COLORS = {
    "bomb": (0.85, 0.30, 0.30),
    "shuffle": (0.30, 0.70, 0.85),
    "freeze": (0.40, 0.80, 1.0),
    "undo": (0.70, 0.50, 0.85),
}


class BonusManager:
    def __init__(self):
        self.reset()

    def reset(self):
        self.counts = dict(BONUS_LIMITS)
        self.active = None
        self.freeze_timer = 0.0
        self.history = []

    def has(self, key):
        return self.counts.get(key, 0) > 0

    def select(self, key):
        if not self.has(key):
            return False
        if key in ("shuffle", "undo", "freeze"):
            return key
        if key == "bomb":
            self.active = "bomb"
            return "bomb"
        return False

    def use(self, key):
        if self.counts.get(key, 0) > 0:
            self.counts[key] -= 1
            return True
        return False

    def push_history(self, board, score):
        snapshot = [row[:] for row in board]
        self.history.append((snapshot, score))
        if len(self.history) > 20:
            self.history.pop(0)

    def pop_history(self):
        if not self.history:
            return None
        return self.history.pop()

    def tick(self, dt):
        if self.freeze_timer > 0:
            self.freeze_timer = max(0.0, self.freeze_timer - dt)


def explode(board, row, col):
    cleared = []
    grid_n = len(board)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            r = row + dr
            c = col + dc
            if 0 <= r < grid_n and 0 <= c < grid_n:
                if board[r][c] != 0:
                    cleared.append((r, c, board[r][c]))
                    board[r][c] = 0
    return cleared
