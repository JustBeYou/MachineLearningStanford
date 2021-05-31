from enum import Enum
from operator import add
import arcade as arcade
import arcade.gui as gui
import numpy as np
from itertools import product
from threading import Thread
from time import sleep
from copy import deepcopy
from pytictoc import TicToc
from heapq import heappush, heappop
import sys
from random import choice
from hashlib import sha1
from marshal import dumps
from sys import argv

WIN_VALUE = 10**6
LOSE_VALUE = -10**6

DEPTH_TRESHOLD = 1000

POS_INF = WIN_VALUE + DEPTH_TRESHOLD
NEG_INF = LOSE_VALUE - DEPTH_TRESHOLD

WINNING_TRESHOLD = WIN_VALUE - DEPTH_TRESHOLD
LOSING_TRESHOLD = LOSE_VALUE + DEPTH_TRESHOLD

#
# === Game state and logic ===
#

class HexCellStatus():
    FREE = 0
    RED  = 1
    BLUE = 2

    LIGHT_RED = 3
    LIGHT_BLUE = 4
    LIGHT_PURPLE = 5
    GOLDEN_BORDER = 6

    def __str__(self):
        if self.value == 2:
            return "B"
        if self.value == 1:
            return "R"
        return "F"

    def __repr__(self):
        return self.__str__()

class HexDirections(Enum):
    LEFT         = ( 0, -1)
    TOP_LEFT     = (-1,  0)
    TOP_RIGHT    = (-1, +1)
    RIGHT        = ( 0, +1)
    BOTTOM_RIGHT = (+1,  0)
    BOTTOM_LEFT  = (+1, -1)

class HexBoardZone():
    TOP_LEFT     = 0
    TOP          = 1
    TOP_RIGHT    = 2
    RIGHT        = 3
    BOTTOM_RIGHT = 4
    BOTTOM       = 5
    BOTTOM_LEFT  = 6
    LEFT         = 7
    INSIDE       = 8

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
    cnt = 0

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

    # TODO: for some reason cloning the object causes infinite recursion
    # use reference for now (but with care!!!)
    def clone(self):
        return self
        #new_board = [[self.board[r][q] for q in range(self.m)] for r in range(self.n)] 
        #new_board_state = HexBoardState(self.n, self.m, self.board)
        #return new_board_state

    def reset(self):
        self.board = [[HexCellStatus.FREE for _ in range(self.m)] for _ in range(self.n)]
        self.ghost_board = [[HexCellStatus.FREE for _ in range(self.m)] for _ in range(self.n)]

    def valid_cell(self, r, q):
        return r >= 0 and q >= 0 and r < self.n and q < self.m

    def neighbours_of(self, r, q):
        #assert self.valid_cell(r, q)
        for direction in HexDirections:
            new_r, new_q = tuple(map(add, (r, q), direction.value))
            if self.valid_cell(new_r, new_q):
                yield new_r, new_q

    def available(self):
        for r in range(self.n):
            for q in range(self.m):
                if self.board[r][q] == HexCellStatus.FREE:
                    yield (r, q)

    def get(self, r, q):
        return self.board[r][q]

    def set(self, r, q, value):
        self.board[r][q] = value

    def zone_of(self, r, q):
        #assert self.valid_cell(r, q)
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
                path = self.__dfs(0, q, board_copy, redGoal, [])
                if redGoal.accomplished():
                    return redGoal.color, path

        # explore from left
        for r in range(0, self.n):
            if board_copy[r][0] == blueGoal.color:
                path = self.__dfs(r, 0, board_copy, blueGoal, [])
                if blueGoal.accomplished():
                    return blueGoal.color, path

        return None

    def __dfs(self, r, q, board_copy, goal, path):
        board_copy[r][q] = None
        z = self.zone_of(r, q)

        if z != HexBoardZone.INSIDE:
            goal.mark(z)

            if goal.accomplished():
                path.append((r, q))
                return path

        for nr, nq in self.neighbours_of(r, q):
            if board_copy[nr][nq] == goal.color:
                path = self.__dfs(nr, nq, board_copy, goal, path)

                if goal.accomplished():
                    path.append((r, q))
                    return path

        return path

    def __str__(self):
        return "\n".join([" | ".join([str(c) for c in r]) for r in self.board])

    def hexdigest(self):
        return sha1(dumps(self.board)).hexdigest()

#
# === Testing the correctness of the implementation ===
#

def autoplay(engine_class, engine_class2, config, games):
    score1 = 0
    score2 = 0
    name1 = engine_class.__name__
    name2 = engine_class2.__name__

    print("[i] === Auto-playing ===")
    for i in range(games):
        print(f"[i] Auto-playing game {i}")

        b = HexBoardState(N, M)
        B = HexBoard(b, 100, 100, 5, 10)

        engine = engine_class(B, HexCellStatus.RED, config)
        engine2 = engine_class2(B, HexCellStatus.BLUE, config)

        while B.winner == None:
            if B.current_player == HexCellStatus.RED:
                engine.move()
            else:
                engine2.move()

        print(f"[i] Game {i} won by player {B.winner}")
        if B.winner[0] == HexCellStatus.RED:
            score1 += 1
        else:
            score2 += 1

    print()
    print(f"[i] Final score {score1} ({name1}) - {score2} ({name2})")
    print()

"""
Battles between engines (20 games per pair, 6x6 grid)

=== Depth 1 ===
( ㅅ ) ❯ ❯) python3 tema2.py TEST | grep "Final score"
[i] Final score 4 (HexRandomEngine) - 6 (HexRandomEngine)
[i] Final score 6 (HexDijkstraEngine) - 4 (HexDijkstraEngine)
[i] Final score 5 (HexOptimizedDijkstraEngine) - 5 (HexOptimizedDijkstraEngine)
[i] Final score 0 (HexRandomEngine) - 10 (HexDijkstraEngine)
[i] Final score 0 (HexRandomEngine) - 10 (HexOptimizedDijkstraEngine)
[i] Final score 10 (HexDijkstraEngine) - 0 (HexRandomEngine)
[i] Final score 4 (HexDijkstraEngine) - 6 (HexOptimizedDijkstraEngine)
[i] Final score 10 (HexOptimizedDijkstraEngine) - 0 (HexRandomEngine)
[i] Final score 7 (HexOptimizedDijkstraEngine) - 3 (HexDijkstraEngine)

Engine                     | Wins
===========================|=====
HexOptimizedDijkstraEngine |  4
HexDijkstraEngine          |  2
HexRandomEngine            |  0

=== Depth 2 ===
( ㅅ ) ❯ ❯) python3 tema2.py TEST | grep "Final score"
[i] Final score 3 (HexRandomEngine) - 7 (HexRandomEngine)
[i] Final score 6 (HexDijkstraEngine) - 4 (HexDijkstraEngine)
[i] Final score 8 (HexOptimizedDijkstraEngine) - 2 (HexOptimizedDijkstraEngine)
[i] Final score 0 (HexRandomEngine) - 10 (HexDijkstraEngine)
[i] Final score 0 (HexRandomEngine) - 10 (HexOptimizedDijkstraEngine)
[i] Final score 10 (HexDijkstraEngine) - 0 (HexRandomEngine)
[i] Final score 3 (HexDijkstraEngine) - 7 (HexOptimizedDijkstraEngine)
[i] Final score 10 (HexOptimizedDijkstraEngine) - 0 (HexRandomEngine)
[i] Final score 9 (HexOptimizedDijkstraEngine) - 1 (HexDijkstraEngine)

Engine                     | Wins
===========================|=====
HexOptimizedDijkstraEngine |  4
HexDijkstraEngine          |  2
HexRandomEngine            |  0

As we can clearly see, the optimized version of the engine wins almost all the time.
"""

def testing():
    print("[i] Testing correctness")
    b = HexBoardState(4, 4)
    B = HexBoard(b, 100, 100, 5, 10)

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
    assert b.winner()[0] == HexCellStatus.BLUE

    b.set(1, 3, HexCellStatus.FREE)
    b.set(1, 2, HexCellStatus.RED)
    print("[i] Check RED winner")
    assert b.winner()[0] == HexCellStatus.RED

    b = HexBoardState(6, 6)
    B = HexBoard(b, 100, 100, 5, 10)

    print("[i] Check Dijkstra")
    conf = Configuration()
    eng = HexDijkstraEngine(B, HexCellStatus.RED, conf)
    
    b.set(3, 0, HexCellStatus.RED)
    b.set(4, 0, HexCellStatus.RED)
    b.set(3, 1, HexCellStatus.RED)
    b.set(1, 2, HexCellStatus.RED)
    
    b.set(2, 0, HexCellStatus.BLUE)
    b.set(2, 1, HexCellStatus.BLUE)
    b.set(2, 2, HexCellStatus.BLUE)
    b.set(3, 2, HexCellStatus.BLUE)

    assert eng.evaluate(HexCellStatus.RED, b, None) == -3
    assert eng.dij(HexCellStatus.RED, b, reconstruct=True)[0] == 6
    assert eng.dij(HexCellStatus.BLUE, b, reconstruct=True)[0] == 3

    print("[+] All tests passed.\n")

    config = Configuration()
    config.depth1 = 1
    config.depth2 = 1
    config.algorithm = EngineAlgorithms.ALPHA_BETA

    autoplay(HexRandomEngine, HexRandomEngine, config, 10)
    autoplay(HexDijkstraEngine, HexDijkstraEngine, config, 10)
    autoplay(HexOptimizedDijkstraEngine, HexOptimizedDijkstraEngine, config, 10)

    autoplay(HexRandomEngine, HexDijkstraEngine, config, 10)
    autoplay(HexRandomEngine, HexOptimizedDijkstraEngine, config, 10)
    autoplay(HexDijkstraEngine, HexRandomEngine, config, 10)
    autoplay(HexDijkstraEngine, HexOptimizedDijkstraEngine, config, 10)
    autoplay(HexOptimizedDijkstraEngine, HexRandomEngine, config, 10)
    autoplay(HexOptimizedDijkstraEngine, HexDijkstraEngine, config, 10)

#
# === Geometry helpers for drawing hexagons ===
#

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

#
# === Graphical logic for the game ===
#

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

        self.thinking = False

        self.reset()

    def reset(self):
        self.current_player = HexCellStatus.RED
        self.winner = None

        self.move_timer = TicToc()
        self.move_timer.tic()
        self.player1_times = []
        self.player2_times = []

    def draw(self):
        x, y, length = self.x_align, self.y_align, self.hexagon_length

        if self.thinking:
            arcade.draw_text("Thinking...", x, y, arcade.color.BLACK, 30)
            return

        if self.winner != None:
            arcade.draw_text(f"{self.winner[0]} won the game!", x, y + 70, arcade.color.BLACK, 18)

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
                ghost_cell = self.state.ghost_board[r][q]

                if cell != HexCellStatus.FREE:
                    color = arcade.color.RED if cell == HexCellStatus.RED else arcade.color.BLUE
                    arcade.draw_polygon_filled(poly, color)
                elif ghost_cell != HexCellStatus.FREE:
                    color = arcade.color.LIGHT_PINK if ghost_cell == HexCellStatus.LIGHT_RED else arcade.color.LIGHT_BLUE
                    if ghost_cell == HexCellStatus.LIGHT_PURPLE:
                        color = arcade.color.LIGHT_PASTEL_PURPLE
                    
                    arcade.draw_polygon_filled(poly, color)

                #if zone == HexBoardZone.TOP or zone == HexBoardZone.BOTTOM:
                #    arcade.draw_point(x_center_col, y_center_col, arcade.color.RED, 4)
                #elif zone == HexBoardZone.LEFT or zone == HexBoardZone.RIGHT:
                #    arcade.draw_point(x_center_col, y_center_col, arcade.color.BLUE, 4)
                
                arcade.draw_polygon_outline(poly, arcade.color.BLACK, self.hexagon_border)

                self.centers[r][q] = (x_center_col, y_center_col)
                x_center_col += displacement

            x_center_row += x_coef
            y_center_row += y_coef
            hexagons = [translate_points(h, x_coef, y_coef) for h in hexagons]

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
                ghost_cell = self.state.ghost_board[r][q]

                if self.state.ghost_board[r][q] == HexCellStatus.GOLDEN_BORDER:
                    arcade.draw_polygon_outline(poly, arcade.color.GOLD, self.hexagon_border)

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

            t = self.move_timer.tocvalue()
            self.move_timer.tic()

            if self.current_player == HexCellStatus.RED:
                self.player1_times.append(round(t, 2))
            else:
                self.player2_times.append(round(t, 2))

            print(f"[i] Player {self.current_player} moved in {round(t, 2)}s")
            print(self.state)

            self.winner = self.state.winner()
            if self.winner != None:
                print(f"[i] Player {self.current_player} won the game!")
                self.print_debug_state()
                for wr, wq in self.winner[1]:
                    self.state.ghost_board[wr][wq] = HexCellStatus.GOLDEN_BORDER
                return (r, q)

            self.current_player = HexCellStatus.BLUE if self.current_player == HexCellStatus.RED else HexCellStatus.RED
            return (r, q)
        return None

    def print_debug_state(self):
        print(f"[i] Player RED times: min {min(self.player1_times)}s max {max(self.player1_times)}s mean {round(np.mean(self.player1_times), 2)}s median {np.median(self.player1_times)}s total {sum(self.player1_times)}s")
        print(f"[i] Player BLUE times: min {min(self.player2_times)}s max {max(self.player2_times)}s mean {round(np.mean(self.player2_times), 2)}s median {np.median(self.player2_times)}s total {sum(self.player2_times)}s")
        print(f"[i] Total gameplay: {sum(self.player1_times) + sum(self.player2_times)}s")


#
# === GUI helpers for creating buttons and input fields ===
# 

def createButtonClass(handler):

    class MyButton(gui.UIFlatButton):
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
    if thread != None:
        obj.cleanup()

    board.reset()
    board.state.reset()

    if obj.mode == GameMode.CvC:
        obj.reinit_threading()
    
    print()
    print("[i] Game restarted")

def handle_go(window, view_before_class, cleanup, *args):
    if cleanup != None:
        cleanup()
    view_before = view_before_class(*args)
    window.show_view(view_before)

def handle_depth1(config, depth, label):
    config.depth1 = depth
    label.text = f"Red Bot (depth {depth})"

def handle_depth2(config, depth, label):
    config.depth2 = depth
    label.text = f"Blue Bot (depth {depth})"

def handle_debug(board):
    board.print_debug_state()

RestartButton = createButtonClass(handle_reset)
GoButton = createButtonClass(handle_go)
Depth1Button = createButtonClass(handle_depth1)
Depth2Button = createButtonClass(handle_depth2)
DebugButton = createButtonClass(handle_debug)

def createToggleClass(handler):

    class MyToggle(gui.UIToggle):
        def __init__(self, center_x, center_y, *args, height=10):
                super().__init__(center_x, center_y, value=False, height=height)
                self.args = args

        def on_click(self):
            self.value = not self.value
            handler(*self.args)

    return MyToggle

def handle_alg_switch(config, label):
    if config.algorithm == EngineAlgorithms.MINI_MAX:
        config.algorithm = EngineAlgorithms.ALPHA_BETA
    else:
        config.algorithm = EngineAlgorithms.MINI_MAX

    text = "Mini-Max" if config.algorithm == EngineAlgorithms.MINI_MAX else "Alpha-Beta"
    label.text = text

AlgToggle = createToggleClass(handle_alg_switch)

#
# === Global configuration ===
#

class EngineAlgorithms(Enum):
    MINI_MAX = 0
    ALPHA_BETA = 1

class Configuration:
    def __init__(self):
        self.algorithm = EngineAlgorithms.MINI_MAX
        self.engine = HexOptimizedDijkstraEngine
        self.engine2 = HexDijkstraEngine
        self.depth1 = 1
        self.depth2 = 1

#
# === Engine logic ===
#

def get_other_color(color):
    if color == HexCellStatus.RED:
        return HexCellStatus.BLUE
    return HexCellStatus.RED

class Minimax:
    def __init__(self, color, board_state, evaluate, available_moves, pruning = False):
        self.board_state = board_state
        self.evaluate = evaluate
        self.available_moves = available_moves
        self.color = color
        self.pruning = pruning
        self.other_color = get_other_color(color)

        self.node_cnt = 0
        self.total_node_cnt = 0

        self.state_cache = {}
        self.winner_cache = {}

    def do_move(self, r, q, color):
        self.board_state.set(r, q, color)

    def revert_move(self, r, q):
        self.board_state.set(r, q, HexCellStatus.FREE)

    def best_move(self, max_depth):
        self.cache_hits = 0
        self.copy_board_state = self.board_state.clone()
        self.node_cnt = 0

        score, move = self.__dfs(0, max_depth, NEG_INF, POS_INF)
        self.total_node_cnt += self.node_cnt

        print(f"[i] Engine {self.color} moved {move} with score estimation {score}.")
        print(f"[i] Explored {self.node_cnt} nodes. ({self.cache_hits} cache hits)")
        print(f"[i] Total nodes explored until now: {self.total_node_cnt}.")

        return move

    def cached_evaluate(self, color, copy_board_state, winner, level):
        """
        On larger boards the cache is useful only when using a large enough depth.
        """
        
        state_hexdigest = copy_board_state.hexdigest()
        if state_hexdigest in self.state_cache:
            self.cache_hits += 1
            return self.state_cache[state_hexdigest]
        value = self.evaluate(color, copy_board_state, winner)
        self.state_cache[state_hexdigest] = value
        return value

    def cached_winner(self, copy_board_state):
        state_hexdigest = copy_board_state.hexdigest()
        if state_hexdigest in self.winner_cache:
            self.cache_hits += 1
            return self.winner_cache[state_hexdigest]
        winner = self.copy_board_state.winner()
        winner = winner[0] if winner != None else None
        self.winner_cache[state_hexdigest] = winner
        return winner

    def __dfs(self, level, max_depth, alpha, beta):
        self.node_cnt += 1
        node_id = self.node_cnt

        #print(f"[DEBUG] Arrived at node {self.node_cnt} depth {level}")
        #print(self.copy_board_state)

        is_max_player = level % 2 == 0
        is_root = level == 0

        # check if this is a winning position (for any player)
        winner = self.cached_winner(self.copy_board_state)

        # if there is a winner or we reached maximal depth
        # return the evaluation of the current state
        if winner != None or level == max_depth:
            value = self.cached_evaluate(self.color, self.copy_board_state, winner, level)
            if value == WIN_VALUE:
                value -= level
            elif value == LOSE_VALUE:
                value += level

            #print(f"[DEBUG] ({self.node_cnt}) Evaluated {value}")      
            return value, None

        to_color = self.color if is_max_player else self.other_color
        best = NEG_INF if is_max_player else POS_INF
        best_moves = []

        # Generate all possible successor states and order them
        """Performing worse than without ordering"""
        moves_and_scores = []
        for r, q in self.available_moves(to_color, self.copy_board_state):
            self.do_move(r, q, to_color)
        
            winner = self.cached_winner(self.copy_board_state)
            score = self.cached_evaluate(self.color, self.copy_board_state, winner, level)
            moves_and_scores.append(((r, q), score))
        
            self.revert_move(r, q)
        moves_and_scores.sort(key = lambda x: x[1], reverse = is_max_player)

        #print(f"[DEBUG] ({self.node_cnt}) Expanding")
        for (r, q), _ in moves_and_scores:
            self.do_move(r, q, to_color)
            tree_value, _ = self.__dfs(level + 1, max_depth, alpha, beta)
            self.revert_move(r, q)

            #print(f"[DEBUG] ({node_id}) Move {(r, q)} returned tree value {tree_value}")
            #print(f"[DEBUG] ({node_id}) Current alpha = {alpha} beta = {beta}")
            
            if is_max_player:
                if tree_value > best:
                    #print(f"[DEBUG] ({node_id}) Update MAX {best} < {tree_value}")
                    best = tree_value
                    if is_root:
                        #print(f"[DEBUG] ({node_id}) Best move {(r, q)}")
                        best_moves = [(r, q)]
                elif is_root and tree_value == best:
                    best_moves.append((r, q))
                    #print(f"[DEBUG] ({node_id}) Another good MAX move {best_moves}") 

                if self.pruning:
                    alpha = max(alpha, best)
                    if alpha > beta:
                        #print(f"[DEBUG] ({node_id}) Prunning MAX! {alpha} >= {beta}")
                        break
            else:
                if tree_value < best:
                    #print(f"[DEBUG] ({node_id}) Update MIN {best} > {tree_value}")
                    best = tree_value
                    if is_root:
                        #print(f"[DEBUG] ({node_id}) Best move {(r, q)}")
                        best_moves = [(r, q)]
                elif is_root and tree_value == best:
                    best_moves.append((r, q))
                    #print(f"[DEBUG] ({node_id}) Another good MIN move {best_moves}")

                if self.pruning:
                    beta = min(beta, best)
                    if beta < alpha:
                        #print(f"[DEBUG] ({node_id}) Prunning MIN! {beta} <= {alpha}")
                        break

        if is_root:
            print(f"[i] ({node_id}) Found possible best moves: {best_moves} with score {best}, alpha = {alpha}, beta = {beta}.")

        return best, choice(best_moves) if is_root else None

class GameMode(Enum):
    PvP = 0
    PvC = 1
    CvC = 2

class HexDumbEngine:
    """Color the first empty hexagon.
    """
    def __init__(self, board, color, config):
        self.board = board
        self.config = config

    def move(self):
        print("[i] Engine is computing a move...")

        found = None
        for r, q in product(range(self.board.state.n), range(self.board.state.m)):
            if self.board.state.get(r, q) == HexCellStatus.FREE:
                found = (r, q)
                break
        self.board.set_cell(r, q)

        print(f"[i] Engine moved {found}")

class HexRandomEngine:
    """Color random hexagons.
    """
    def __init__(self, board, color, config):
        self.board = board
        self.config = config
        
    def move(self):
        print("[i] Engine is computing a move...")

        available = list(self.board.state.available())
        found = choice(available)
        r, q = found
        self.board.set_cell(r, q)

        print(f"[i] Engine moved {found}")

class HexNaiveEngine:
    """Generate the entire solution space.
    """
    def __init__(self, board, color, config):
        print(f"[i] Created engine with color {color}")
        self.board = board
        self.config = config
        
        self.predictor = Minimax(
            color, 
            self.board.state, 
            self.evaluate,
            self.available_moves,
            pruning=self.config.algorithm == EngineAlgorithms.ALPHA_BETA,
        )

    def available_moves(self, color, board_state):
        return board_state.available()

    def evaluate(self, color, board_state, winner):
        if winner == None:
            return 0
        if winner == color:
            return +1
        return -1

    def move(self):
        print("[i] Engine is computing a move...")
        found = self.predictor.best_move(999999)
        self.board.set_cell(found[0][0], found[0][1])
        print(f"[i] Engine moved {found}")

class HexDijkstraEngine:
    """Use Dijkstra to evaluate the shortest paths to a winning position.

    Each player wants to create a contiguous path from one side of the board to another.
    We aim to create this path as fast as possible so we should follow the shortest one.
    Therefore, using Dijkstra we can compute the shortest possible path for both players.
    We consider the cost of a free cell to be 1 and the cost of an occupied cell (by us) to 
    be 0. 
    The value of a given board would be: opponent's shortest path - our shortest path
    This value is increasing as we are getting closer to victory and decreasing as our 
    opponent is getting closer to victory.
    """

    def __init__(self, board, color, config):
        self.board = board
        self.config = config
        self.color = color
        self.other_color = get_other_color(color)

        self.predictor = Minimax(
            color, 
            self.board.state, 
            self.evaluate,
            self.available_moves,
            pruning=self.config.algorithm == EngineAlgorithms.ALPHA_BETA,
        )

        self.start_pos_red = list(product([0], range(self.board.state.m)))
        self.end_pos_red = list(product([self.board.state.n-1], range(self.board.state.m)))

        self.start_pos_blue = list(product(range(self.board.state.n), [0]))
        self.end_pos_blue = list(product(range(self.board.state.n), [self.board.state.m-1]))

        self.turn = 0 if color == HexCellStatus.RED else 1
        self.centrals = set()

        a = board.state.n // 2
        b = board.state.m // 2
        for direction in HexDirections:
            p = tuple(map(add, (a, b), direction.value))
            self.centrals.add(p)


    def dij(self, color, board_state, reconstruct = False):
        other_color = get_other_color(color)
        if color == HexCellStatus.RED:
            start_pos = self.start_pos_red
            end_pos = self.end_pos_red
        else:
            start_pos = self.start_pos_blue
            end_pos = self.end_pos_blue

        queue = []

        # from start to end
        start_costs = [[POS_INF for _ in range(board_state.m)] for _ in range(board_state.n)]
        start_prev = [[(None,None) for _ in range(board_state.m)] for _ in range(board_state.n)]
        for r, q in start_pos:
            cost = 1
            v = board_state.get(r, q)
            if v == color:
                cost = 0
            elif v != HexCellStatus.FREE:
                continue

            start_costs[r][q] = cost
            heappush(queue, (cost, (r, q)))
        
        visited = set()
        while len(queue):
            curr_cost, p = heappop(queue)
            r, q = p
            if p in visited: continue
            visited.add(p)

            for next_p in board_state.neighbours_of(r, q):
                next_r, next_q = next_p
                v = board_state.get(next_r, next_q)
                if v == other_color:
                    continue

                if next_p in visited: continue
                next_r, next_q = next_p

                arc_cost = 1
                if v == color:
                    arc_cost = 0

                if curr_cost + arc_cost < start_costs[next_r][next_q]:
                    start_costs[next_r][next_q] = curr_cost + arc_cost
                    start_prev[next_r][next_q] = (r, q)
                    heappush(queue, (start_costs[next_r][next_q], (next_r, next_q)))

        # from end to start
        end_costs = [[POS_INF for _ in range(board_state.m)] for _ in range(board_state.n)]
        end_prev = [[(None,None) for _ in range(board_state.m)] for _ in range(board_state.n)]
        for r, q in end_pos:
            cost = 1
            v = board_state.get(r, q)
            if v == color:
                cost = 0
            elif v != HexCellStatus.FREE:
                continue

            end_costs[r][q] = cost
            heappush(queue, (cost, (r, q)))

        visited = set()
        while len(queue):
            curr_cost, p = heappop(queue)
            r, q = p
            if p in visited: continue
            visited.add(p)

            for next_p in board_state.neighbours_of(r, q):
                next_r, next_q = next_p
                v = board_state.get(next_r, next_q)
                if v == other_color:
                    continue

                if next_p in visited: continue

                arc_cost = 1
                if v == color:
                    arc_cost = 0

                if curr_cost + arc_cost < end_costs[next_r][next_q]:
                    end_costs[next_r][next_q] = curr_cost + arc_cost
                    end_prev[next_r][next_q] = (r, q)
                    heappush(queue, (end_costs[next_r][next_q], (next_r, next_q)))

        best = POS_INF
        best_pos = None
        for r in range(board_state.n):
            for q in range(board_state.m):
                new_cost = start_costs[r][q] + end_costs[r][q]
                if best > new_cost:
                    best = new_cost
                    best_pos = (r, q) 

        start_path = []
        end_path = []
        the_path = []

        if reconstruct:
            cr, cq = best_pos
            while cr != None:
                start_path.append((cr, cq))
                cr, cq = start_prev[cr][cq]       
            cr, cq = best_pos
            while cr != None:
                end_path.append((cr, cq))
                cr, cq = end_prev[cr][cq]
            the_path = start_path + end_path 
    
        return best, the_path 

    def available_moves(self, color, board_state):
        moves = board_state.available()
        if self.turn < 2:
            moves = filter(lambda m: m in self.centrals, moves)
        return moves

    def evaluate(self, color, board_state, winner):
        if winner != None and winner == color:
            return WIN_VALUE
        elif winner != None:
            return LOSE_VALUE

        # __bfs returns the cost ie. the length of the shortest path to victory
        # score: enemy cost - my cost. the bigger, the better
        return self.dij(get_other_color(color), board_state)[0] - self.dij(color, board_state)[0]

    def move(self):
        print("[i] Engine is computing a move...")
        depth = self.config.depth1 if self.color == HexCellStatus.RED else self.config.depth2
        found = self.predictor.best_move(depth)
        self.board.set_cell(found[0], found[1])

        print(f"[i] Engine moved {found}")
        self.turn += 2
        if self.board.state.winner() != None:
            return

        for r in range(self.board.state.n):
            for q in range(self.board.state.m):
                self.board.state.ghost_board[r][q] = HexCellStatus.FREE

        for r, q in self.dij(HexCellStatus.BLUE, self.board.state, reconstruct=True)[1]:
            if self.board.state.get(r, q) == HexCellStatus.FREE:
                self.board.state.ghost_board[r][q] = HexCellStatus.LIGHT_BLUE
        for r, q in self.dij(HexCellStatus.RED, self.board.state, reconstruct=True)[1]:
            if self.board.state.get(r, q) == HexCellStatus.FREE:
                if self.board.state.ghost_board[r][q] == HexCellStatus.FREE:
                    self.board.state.ghost_board[r][q] = HexCellStatus.LIGHT_RED
                elif self.board.state.ghost_board[r][q] == HexCellStatus.LIGHT_BLUE:
                    self.board.state.ghost_board[r][q] = HexCellStatus.LIGHT_PURPLE

class HexOptimizedDijkstraEngine(HexDijkstraEngine):
    """Use Dijkstra to find the shortest path but also prioritize bridges.

    Consider the following to be 4 hexagonal spaces on our board:
        A
       / \\
       B  C
       \\ / 
         D

    If positions A and D are occupied by us, we consider this to be a bridge.
    If the opponent occupies B, we can occupy C and still have a connected path.
    The same is true for C.

    We assign score values to the following situations:
    - we have a bridge (good)
    - we have the possibility to make a bridge (good)
    - we blocked a possible bridge of our opponent (good)
    - our opponent has a bridge (bad)
    - our opponent has the possibility of making a bridge (bad)
    - our opponent blocked one of our possible bridges (bad)

    The values chosen are arbitrary and tweaked until I've found the engine was performing
    well enough.
    """

    def __init__(self, board, color, config):
        super().__init__(board, color, config)

        self.second_neighbours_dir = []
        dirs = list(HexDirections)
        for i in range(len(dirs)):
            new_dir = tuple(map(add, dirs[i].value, dirs[(i+1)%len(dirs)].value))
            self.second_neighbours_dir.append(new_dir)
        assert len(self.second_neighbours_dir) == 6

    def second_neighbours_of(self, r, q):
        for direction in self.second_neighbours_dir:
            new_r, new_q = tuple(map(add, (r, q), direction))
            if self.board.state.valid_cell(new_r, new_q):
                yield new_r, new_q

    def evaluate(self, color, board_state, winner):
        value = super().evaluate(color, board_state, winner)
        if value == WIN_VALUE or value == LOSE_VALUE:
            return value

        value *= 1000

        other_color = get_other_color(color)
        to_add = 0
        for r in range(board_state.n):
            for q in range(board_state.m):
                v = board_state.get(r, q)
                if v == HexCellStatus.FREE:
                    continue

                for neigh_r, neigh_q in self.second_neighbours_of(r, q):
                    neigh_v = board_state.get(neigh_r, neigh_q)

                    if v == color and neigh_v == color:
                        to_add += 10
                    elif v == color and neigh_v == other_color:
                        to_add -=  5
                    elif v == color and neigh_v == HexCellStatus.FREE:
                        to_add +=  2
                    elif v == other_color and neigh_v == other_color:
                        to_add -= 10
                    elif v == other_color and neigh_v == color:
                        to_add +=  5
                    elif v == other_color and neigh_v == HexCellStatus.FREE:
                        to_add -= 2
        to_add //= 6

        return value + to_add

def computer_play(obj, board, engine, engine2):
    print("[i] Computers should play")
    sleep(ENGINE_DELAY)
    while board.winner == None and obj.should_stop == False:
        print(f"[i] Current player {board.current_player}")
        board.thinking = True
        if board.current_player == HexCellStatus.RED:
            engine.move()
        else:
            engine2.move()
        board.thinking = False
        sleep(ENGINE_DELAY)
    print("[+] Computers done.")

#
# === Game user interface ===
#

class GameView(arcade.View):
    def __init__(self, mode, config, engine_class = None, engine_class2 = None):
        super().__init__()

        self.config = config

        self.hs = HexBoardState(N, M)
        self.hb = HexBoard(self.hs, SCREEN_WIDTH, SCREEN_HEIGHT, HEXAGON_LENGTH, HEXAGON_BORDER)
        self.ui_manager = gui.UIManager()

        self.mode = mode

        first_comp_color = HexCellStatus.BLUE
        if self.mode == GameMode.CvC:
            first_comp_color = HexCellStatus.RED

        self.engine = engine_class(self.hb, first_comp_color, config) if engine_class != None else None
        self.engine2 = engine_class2(self.hb, HexCellStatus.BLUE, config) if engine_class2 != None else None

        self.reinit_threading()

        print("[i] New game started")

    def reinit_threading(self):
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
        if self.mode == GameMode.PvC:
            arcade.draw_text(f"Player - Computer ({self.config.depth2})", 20, SCREEN_HEIGHT - 50, arcade.color.BLACK, 15)
        elif self.mode == GameMode.CvC:
            arcade.draw_text(f"Computer ({self.config.depth1}) - Computer ({self.config.depth2})", 20, SCREEN_HEIGHT - 50, arcade.color.BLACK, 15)

        self.hb.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        if self.hb.winner != None:
            return

        if self.mode == GameMode.CvC:
            return 
        elif self.mode == GameMode.PvC and self.hb.current_player == HexCellStatus.RED:
            last_move = self.hb.on_click(x, y)
            if last_move != None and self.hb.winner == None:
                t = TicToc()
                t.tic()
                self.engine.move()
                t.toc()
        else:
            self.hb.on_click(x, y)

    def cleanup(self):
        if self.thread != None:
            self.should_stop = True
            self.thread.join()

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

        self.ui_manager.add_ui_element(
            GoButton(
                "Back",
                self.hb.x_align + self.hb.total_width // 2 + 130, 
                self.hb.y_align - self.hb.total_height - 30, 
                self.window,
                MenuView,
                self.cleanup,
                self.config,
            )
        )

        self.ui_manager.add_ui_element(
            DebugButton(
                "Debug",
                self.hb.x_align + self.hb.total_width // 2, 
                self.hb.y_align - self.hb.total_height - 100, 
                self.hb, 
            )
        )

class MenuView(arcade.View):
    def __init__(self, config):
        super().__init__()
        self.ui_manager = gui.UIManager()
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT - (0.15 * SCREEN_HEIGHT)
        self.config = config

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
                self.config,
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
                self.config,
                self.config.engine,
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
                self.config,
                self.config.engine,
                self.config.engine2,
                width=380,
            )
        )

        self.ui_manager.add_ui_element(
            GoButton(
                "Settings",
                self.x,
                self.y - 260,
                self.window,
                SettingsView,
                None,
                self.config,
                width=380,
            )
        )

class SettingsView(arcade.View):
    def __init__(self, config):
        super().__init__()
        self.ui_manager = gui.UIManager()
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT - (0.15 * SCREEN_HEIGHT)
        self.config = config

    def on_show_view(self):
        self.setup()
        arcade.set_background_color(arcade.color.WHITE)

    def on_draw(self):
        arcade.start_render()
        arcade.draw_text("Settings", self.x, self.y,
                         arcade.color.BLACK, font_size=30, anchor_x="center")

    def on_hide_view(self):
        self.ui_manager.unregister_handlers()

    def setup(self):
        self.ui_manager.purge_ui_elements()

        label1 = gui.UILabel(
            "Mini-Max" if self.config.algorithm == EngineAlgorithms.MINI_MAX else "Alpha-Beta",
            self.x - 50,
            self.y - 50,
            width=380,
        )
        self.ui_manager.add_ui_element(label1)

        self.ui_manager.add_ui_element(
            AlgToggle(
                self.x + 150,
                self.y - 50,
                self.config,
                label1,
                height=25,
            )
        )

        label_bot1 = gui.UILabel(
            f"Red Bot (depth {self.config.depth1})",
            self.x - 210,
            self.y - 100,
            width=380,
        )
        self.ui_manager.add_ui_element(label_bot1)

        self.ui_manager.add_ui_element(
            Depth1Button(
                "Easy",
                self.x,
                self.y - 100,
                self.config,
                1,
                label_bot1,
                width=120,
            )
        )
        self.ui_manager.add_ui_element(
            Depth1Button(
                "Medium",
                self.x + 130,
                self.y - 100,
                self.config,
                2,
                label_bot1,
                width=120,
            )
        )
        self.ui_manager.add_ui_element(
            Depth1Button(
                "Hard",
                self.x + 260,
                self.y - 100,
                self.config,
                3,
                label_bot1,
                width=120,
            )
        )

        label_bot2 = gui.UILabel(
            f"Blue Bot (depth {self.config.depth2})",
            self.x - 210,
            self.y - 155,
            width=380,
        )
        self.ui_manager.add_ui_element(label_bot2)

        self.ui_manager.add_ui_element(
            Depth2Button(
                "Easy",
                self.x,
                self.y - 155,
                self.config,
                1,
                label_bot2,
                width=120,
            )
        )
        self.ui_manager.add_ui_element(
            Depth2Button(
                "Medium",
                self.x + 130,
                self.y - 155,
                self.config,
                2,
                label_bot2,
                width=120,
            )
        )
        self.ui_manager.add_ui_element(
            Depth2Button(
                "Hard",
                self.x + 260,
                self.y - 155,
                self.config,
                3,
                label_bot2,
                width=120,
            )
        )

        self.ui_manager.add_ui_element(
            GoButton(
                "Back",
                self.x,
                self.y - 260,
                self.window,
                MenuView,
                None,
                self.config,
                width=380,
            )
        )

class MainWindow(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.WHITE)

#
# === Constants ===
#

SCREEN_WIDTH = 900
SCREEN_HEIGHT = 700
SCREEN_TITLE = "Hex Game - Proiect IA - Mihail Feraru 242"

HEXAGON_LENGTH = 20
HEXAGON_BORDER = 3
N = 6
M = 6

assert M == N
assert N >= 2 and M >= 2
assert N <= 20 and M <= 20

ENGINE_DELAY = 0.25

#
# === Main ===
#

def main():
    if len(argv) >= 2 and argv[1] == "TEST":
        testing()
        return

    config = Configuration()
    mainWindow = MainWindow()
    menuView = MenuView(config)
    mainWindow.show_view(menuView)
    arcade.run()

main()