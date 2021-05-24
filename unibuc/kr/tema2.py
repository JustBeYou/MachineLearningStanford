from enum import Enum
from operator import add

class HexCellStatus(Enum):
    FREE = 0
    RED  = 1
    BLUE = 2

    def __str__(self):
        if self.value == 2:
            return "B"
        if self.value == 1:
            return "R"
        return "F"

class HexDirections(Enum):
    LEFT         = ( 0, -1)
    RIGHT        = ( 0, +1)
    TOP_LEFT     = (-1,  0)
    TOP_RIGHT    = (-1, +1)
    BOTTOM_LEFT  = (+1, -1)
    BOTTOM_RIGHT = (+1,  0)

class HexBoardZone(Enum):
    TOP_LEFT     = (-1, -1)
    TOP          = (-1,  0)
    TOP_RIGHT    = (-1, +1)
    RIGHT        = ( 0, +1)
    BOTTOM_RIGHT = (+1, +1)
    BOTTOM       = (+1,  0)
    BOTTOM_LEFT  = (+1, -1)
    LEFT         = ( 0, -1)
    INSIDE       = ( 0,  0)

class HexGoal:
    def __init__(self, start, end, color):
        self.start = {k: False for k in start}
        self.end = {k: False for k in end}
        self.color = color

    def mark(self, value):
        if value in self.start:
            self.start[value] = True
        elif value in self.end:
            self.end[value] = True

    def accomplished(self):
        return any(self.start.values()) and any(self.end.values())

class HexRedGoal(HexGoal):
    def __init__(self):
        super().__init__([
            HexBoardZone.TOP,
            HexBoardZone.TOP_LEFT,
            HexBoardZone.TOP_RIGHT,
        ], [
            HexBoardZone.BOTTOM,
            HexBoardZone.BOTTOM_LEFT,
            HexBoardZone.BOTTOM_RIGHT,
        ], HexCellStatus.RED)

class HexBlueGoal(HexGoal):
    def __init__(self):
        super().__init__([
            HexBoardZone.LEFT,
            HexBoardZone.TOP_LEFT,
            HexBoardZone.BOTTOM_LEFT,
        ], [
            HexBoardZone.RIGHT,
            HexBoardZone.TOP_RIGHT,
            HexBoardZone.BOTTOM_RIGHT,
        ], HexCellStatus.BLUE)

class HexBoardState:
    """State of the game.

    RED is always playing for a TOP-BOTTOM path.
    BLUE is always playing for a LEFT-RIGHT path.
    """

    def __init__(self, n = 11, m = 11):
        self.n = n
        self.m = m
        self.board = [[HexCellStatus.FREE for _ in range(m)] for _ in range(n)]

    def valid_cell(self, r, q):
        return r >= 0 and q >= 0 and r < self.n and q < self.m

    def neighbours_of(self, r, q):
        assert self.valid_cell(r, q)
        for direction in HexDirections:
            new_r, new_q = tuple(map(add, (r, q), direction.value))
            if self.valid_cell(new_r, new_q):
                yield new_r, new_q

    def get(self, r, q):
        return self.board[r][q]

    def set(self, r, q, value):
        self.board[r][q] = value

    def zone_of(self, r, q):
        assert self.valid_cell(r, q)
        p = (r, q)

        if p == (0, 0): return HexBoardZone.TOP_LEFT
        if p == (0, self.m-1): return HexBoardZone.TOP_RIGHT
        if p == (self.n-1, 0): return HexBoardZone.BOTTOM_LEFT 
        if p == (self.n-1, self.m-1): return HexBoardZone.BOTTOM_RIGHT
        if r == 0: return HexBoardZone.TOP
        if r == self.n-1: return HexBoardZone.BOTTOM
        if q == 0: return HexBoardZone.LEFT
        if q == self.m-1: return HexBoardZone.RIGHT

        return HexBoardZone.INSIDE
    
    def winner(self):
        board_copy = [[self.board[r][q] for q in range(self.m)] for r in range(self.n)] 
        redGoal = HexRedGoal()
        blueGoal = HexBlueGoal()

        # explore from TOP
        for q in range(0, self.m):
            if board_copy[0][q] == redGoal.color:
                self.__dfs(0, q, board_copy, redGoal)
        if redGoal.accomplished():
            return redGoal.color

        # explore from left
        for r in range(0, self.n):
            if board_copy[r][0] == blueGoal.color:
                self.__dfs(r, 0, board_copy, blueGoal)
        if blueGoal.accomplished():
            return blueGoal.color

        return None

    def __dfs(self, r, q, board_copy, goal):
        board_copy[r][q] = None
        z = self.zone_of(r, q)

        if z != HexBoardZone.INSIDE:
            goal.mark(z)

        for nr, nq in self.neighbours_of(r, q):
            if board_copy[nr][nq] == goal.color:
                self.__dfs(nr, nq, board_copy, goal)

    def __str__(self):
        return "\n".join([" | ".join([str(c) for c in r]) for r in self.board])

def testing():
    print("[i] Testing correctness")
    b = HexBoardState(4, 4)
    
    b.set(0, 2, HexCellStatus.RED)
    b.set(1, 1, HexCellStatus.RED)
    b.set(2, 2, HexCellStatus.RED)
    b.set(3, 2, HexCellStatus.RED)

    b.set(1, 0, HexCellStatus.BLUE)
    b.set(2, 0, HexCellStatus.BLUE)
    b.set(2, 1, HexCellStatus.BLUE)
    b.set(1, 2, HexCellStatus.BLUE)
    print("[i] Check no winner")
    assert b.winner() == None
    
    b.set(1, 3, HexCellStatus.BLUE)
    print("[i] Check BLUE winner")
    assert b.winner() == HexCellStatus.BLUE

    b.set(1, 3, HexCellStatus.FREE)
    b.set(1, 2, HexCellStatus.RED)
    print("[i] Check RED winner")
    assert b.winner() == HexCellStatus.RED

    print("[+] All tests passed.")

def main():
    pass

testing()
main()