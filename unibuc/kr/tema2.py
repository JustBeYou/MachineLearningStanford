from enum import Enum
from operator import add
import arcade
import arcade.gui
import numpy as np
from itertools import product
from threading import Thread
from time import sleep

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
        self.reset() 

    def reset(self):
        self.board = [[HexCellStatus.FREE for _ in range(self.m)] for _ in range(self.n)]

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

def compute_hexagon(x, y, length):
    points = []
    for i in range(6):
        angle = i/3 * np.pi + np.pi/2
        points.append((x + length * np.cos(angle), y + length * np.sin(angle)))
    return points

def compute_hexagon_below_coefs(length):
    angle = -1/3 * np.pi
    dist = length * np.sqrt(3)
    return (dist * np.cos(angle), dist * np.sin(angle))

def translate_points(points, vx, vy):
    return [(x + vx, y + vy) for x, y in points]

def distance(xa, ya, xb, yb):
    return np.sqrt((xa-xb)**2 + (ya-yb)**2)

class HexBoard:
    def __init__(self, state, screen_width, screen_height, hexagon_length, hexagon_border):
        self.state = state
        self.n = state.n
        self.m = state.m

        self.total_height = self.n * hexagon_length * np.sqrt(3)
        self.total_width = self.m * hexagon_length * np.sqrt(3) + self.n * hexagon_length / 2 * np.sqrt(3)
        left_margin = (screen_width - self.total_width) / 2
        top_margin = (screen_height * 1.1 - self.total_height) / 2

        self.hexagon_length = hexagon_length
        self.x_align = left_margin
        self.y_align = screen_height - top_margin
        self.hexagon_border = hexagon_border

        self.centers = [[(0, 0) for _ in range(self.m)] for _ in range(self.n)]
        self.radius = self.hexagon_length / 2 * np.sqrt(3)

        self.reset()

    def reset(self):
        self.current_player = HexCellStatus.RED
        self.winner = None

    def draw(self):
        x, y, length = self.x_align, self.y_align, self.hexagon_length

        if self.winner != None:
            arcade.draw_text(f"{self.winner} won the game!", x, y + 70, arcade.color.BLACK, 18)

        arcade.draw_text(f"Current player: {self.current_player}", x, y + 40, arcade.color.BLACK, 14)

        hexagon = compute_hexagon(x, y, length)
        hexagons = [hexagon]
        displacement = length * np.sqrt(3)
        for _ in range(self.state.m - 1):
            hexagons.append(translate_points(hexagons[-1], displacement, 0))
        
        x_coef, y_coef = compute_hexagon_below_coefs(length)
        x_center_row, y_center_row = x, y      

        for r, row in enumerate(self.state.board):
            x_center_col, y_center_col = x_center_row, y_center_row
            for q, (cell, poly) in enumerate(zip(row, hexagons)):
                zone = self.state.zone_of(r, q)

                if cell != HexCellStatus.FREE:
                    color = arcade.color.RED if cell == HexCellStatus.RED else arcade.color.BLUE
                    arcade.draw_polygon_filled(poly, color)

                if zone == HexBoardZone.TOP or zone == HexBoardZone.BOTTOM:
                    arcade.draw_point(x_center_col, y_center_col, arcade.color.RED, 4)
                elif zone == HexBoardZone.LEFT or zone == HexBoardZone.RIGHT:
                    arcade.draw_point(x_center_col, y_center_col, arcade.color.BLUE, 4)

                arcade.draw_polygon_outline(poly, arcade.color.BLACK, self.hexagon_border)

                self.centers[r][q] = (x_center_col, y_center_col)
                x_center_col += displacement

            x_center_row += x_coef
            y_center_row += y_coef
            hexagons = [translate_points(h, x_coef, y_coef) for h in hexagons]

    def on_click(self, x, y):
        if self.winner != None:
            return None

        found = None
        for r in range(self.n):
            for q in range(self.m):
                cx, cy = self.centers[r][q]                
                dist = distance(x, y, cx, cy)
                if dist <= self.radius:
                    found = (r, q)
                    break
            if found != None:
                break

        if found == None:
            return None

        return self.set_cell(found[0], found[1])

    def set_cell(self, r, q):
        if self.state.get(r, q) == HexCellStatus.FREE:
            self.state.set(r, q, self.current_player)
            self.winner = self.state.winner()
            if self.winner != None:
                return (r, q)

            self.current_player = HexCellStatus.BLUE if self.current_player == HexCellStatus.RED else HexCellStatus.RED
            return (r, q)
        return None

def createButtonClass(handler):

    class MyButton(arcade.gui.UIFlatButton):
        def __init__(self, text, center_x, center_y, *args, width=220):
            super().__init__(
                text,
                center_x=center_x,
                center_y=center_y,
                width=width,
                height=50,
            )
            self.args = args

            self.style.set_class_attrs("button", font_size=14)

        def on_click(self):
           handler(*self.args) 
    
    return MyButton

def handle_reset(board, thread, obj):
    board.reset()
    board.state.reset()

    if thread != None:
        obj.reinit_thrading()

def handle_go(window, view_before_class, cleanup, *args):
    if cleanup != None:
        cleanup()
    view_before = view_before_class(*args)
    window.show_view(view_before)

RestartButton = createButtonClass(handle_reset)
GoButton = createButtonClass(handle_go)

class GameMode(Enum):
    PvP = 0
    PvC = 1
    CvC = 2

class HexNaiveEngine:
    def __init__(self, board):
        self.board = board
        
    def move(self):
        print("[i] Engine is computing a move...")

        found = None
        for r, q in product(range(self.board.state.n), range(self.board.state.m)):
            if self.board.state.get(r, q) == HexCellStatus.FREE:
                found = (r, q)
                break
        self.board.set_cell(r, q)

        print(f"[i] Engine moved {found}")

def computer_play(obj, board, engine, engine2):
    print("[i] Computers should play")
    sleep(ENGINE_DELAY)
    while board.winner == None and obj.should_stop == False:
        if board.current_player == HexCellStatus.RED:
            engine.move()
        else:
            engine2.move()
        sleep(ENGINE_DELAY)
    print("[+] Computers done.")

class GameView(arcade.View):
    def __init__(self, mode, engine_class = None, engine_class2 = None):
        super().__init__()

        self.hs = HexBoardState(N, M)
        self.hb = HexBoard(self.hs, SCREEN_WIDTH, SCREEN_HEIGHT, HEXAGON_LENGTH, HEXAGON_BORDER)
        self.ui_manager = arcade.gui.UIManager()

        self.mode = mode
        self.engine = engine_class(self.hb) if engine_class != None else None
        self.engine2 = engine_class2(self.hb) if engine_class2 != None else None

        self.reinit_thrading()

    def reinit_thrading(self):
        self.should_stop = False
        if self.mode == GameMode.CvC:
            self.thread = Thread(target = computer_play, args = (self, self.hb, self.engine, self.engine2))
            self.thread.start()
        else:
            self.thread = None

    def on_show_view(self):
        self.setup()
        arcade.set_background_color(arcade.color.WHITE)

    def on_hide_view(self):
        self.ui_manager.unregister_handlers()

    def on_draw(self):
        arcade.start_render()
        arcade.draw_text(f"{self.mode}", 20, SCREEN_HEIGHT - 30, arcade.color.BLACK, 16)
        self.hb.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        if self.hb.winner != None:
            return

        if self.mode == GameMode.CvC:
            return 
        elif self.mode == GameMode.PvC and self.hb.current_player == HexCellStatus.RED:
            last_move = self.hb.on_click(x, y)
            if last_move != None: 
                self.engine.move()
        else:
            self.hb.on_click(x, y)

    def setup(self):
        self.ui_manager.purge_ui_elements()

        self.ui_manager.add_ui_element(
            RestartButton(
                "Restart game",
                self.hb.x_align + self.hb.total_width // 2 - 130, 
                self.hb.y_align - self.hb.total_height - 30, 
                self.hb,
                self.thread,
                self,
            )
        )

        def cleanup():
            if self.thread != None:
                self.should_stop = True
                self.thread.join()

        self.ui_manager.add_ui_element(
            GoButton(
                "Back",
                self.hb.x_align + self.hb.total_width // 2 + 130, 
                self.hb.y_align - self.hb.total_height - 30, 
                self.window,
                MenuView,
                cleanup,
            )
        )

class MenuView(arcade.View):
    def __init__(self):
        super().__init__()
        self.ui_manager = arcade.gui.UIManager()
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT - (0.15 * SCREEN_HEIGHT)

    def on_show_view(self):
        self.setup()
        arcade.set_background_color(arcade.color.WHITE)

    def on_draw(self):
        arcade.start_render()
        arcade.draw_text("Hex Game", self.x, self.y,
                         arcade.color.BLACK, font_size=30, anchor_x="center")

    def on_hide_view(self):
        self.ui_manager.unregister_handlers()

    def setup(self):
        self.ui_manager.purge_ui_elements()

        self.ui_manager.add_ui_element(
            GoButton(
                "Player vs Player",
                self.x,
                self.y - 50,
                self.window,
                GameView,
                None,
                GameMode.PvP,
                width=380,
            )
        )

        self.ui_manager.add_ui_element(
            GoButton(
                "Player vs Computer",
                self.x,
                self.y - 120,
                self.window,
                GameView,
                None,
                GameMode.PvC,
                HexNaiveEngine,
                width=380,
            )
        )

        self.ui_manager.add_ui_element(
            GoButton(
                "Computer vs Computer",
                self.x,
                self.y - 190,
                self.window,
                GameView,
                None,
                GameMode.CvC,
                HexNaiveEngine,
                HexNaiveEngine,
                width=380,
            )
        )

class MainWindow(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.WHITE)

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Hex Game"

HEXAGON_LENGTH = 20
HEXAGON_BORDER = 3
N = 11
M = 11

assert N <= 20 and M <= 20

ENGINE_DELAY = 0.05

def main():
    mainWindow = MainWindow()
    menuView = MenuView()
    mainWindow.show_view(menuView)
    arcade.run()

testing()
main()