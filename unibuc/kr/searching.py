from abc import ABC, abstractmethod
from heapq import heappop, heappush
from typing import Optional, Callable, List, Iterable, Set, Generic, TypeVar, cast, Any
from copy import copy
from pytictoc import TicToc
from threading import Timer

T = TypeVar('T')
class StateNode(ABC, Generic[T]):
    def __init__(self, state: T, parent: Optional['StateNode'] = None):
        self.depth: int = 0 if parent == None else cast('StateNode', parent).depth + 1

        self.state = state
        self.parent = parent
        self.cost = self.arc_cost_fn()
        self.heuristic_cost = self.heuristic_fn()
        self.final_cost = self.cost + self.heuristic_cost

    @abstractmethod
    def next_states(self, *args, **kwargs) -> Iterable:
        raise NotImplementedError

    def state_value(self):
        return self.state

    def arc_cost_fn(self):
        return 1

    def heuristic_fn(self):
        return 0

    def __repr__(self):
        return f"< {'(root) ' if self.parent is None else ''}Node ({self.state}) with cost {self.cost} >"

class Comparable(ABC):
    @abstractmethod
    def __lt__(self, value):
        raise NotImplementedError

class Hashable(ABC):
    @abstractmethod
    def hexdigest_internal(self):
        raise NotImplementedError

    def hexdigest(self):
        if not hasattr(self, 'cached_hash'):
            self.cached_hash = self.hexdigest_internal()
        return self.cached_hash

class PathIterator:
    NODE_MODE = lambda node: node
    STATE_ONLY_MODE = lambda node: node.state 

    def __init__(self, leaf: StateNode, mode: Callable = NODE_MODE):
        self.leaf = leaf
        self.mode = mode

    def __iter__(self):
        return self

    def __next__(self):
        if self.leaf is not None:
            current = self.mode(self.leaf)
            self.leaf = self.leaf.parent
            return current
        raise StopIteration

class SearchingTemplate(ABC):
    def __init__(self, logging=False, timeout=60):
        self.logging = logging
        self.timeout = timeout

    def bfs(self, root: StateNode, **kwargs) -> tuple:
        self.__log("Running BFS")
        return self.__bfs_traverse(root, **kwargs)

    def ucs(self, root: StateNode, **kwargs) -> tuple:
        self.__log("Running UCS")
        return self.__bfs_traverse(root, ordered=True, **kwargs)

    # same as UCS but you should pass a node comparable by f cost
    def a_star(self, root: StateNode, **kwargs) -> tuple:
        self.__log("Running A*")
        return self.__bfs_traverse(root, ordered=True, **kwargs)

    def a_star_opt(self, root: StateNode, **kwargs) -> tuple:
        self.__log("Running A* open-closed")
        return self.__bfs_traverse(root, ordered=True, open_closed=True, **kwargs)

    FOUND = -1
    UNINITIALIZED_MIN = -2

    def ida_star(self, root: StateNode, *args, **kwargs) -> tuple:
        self.__log("Running IDA*")

        bound = root.final_cost
        stack = [root]
        all_results: list = []

        statistics: dict = {
            'time': 0,
            'max_depth': 0,
            'times': [],
            'max_in_memory': 1,
            'total_states': 1,
        }

        timer = TicToc()
        timer.tic()

        timeout_exit = [False]
        def handle_timeout():
            timeout_exit[0] = True

        th_timer = Timer(self.timeout, handle_timeout)
        th_timer.start()

        if not self.initial_has_solution(root, *args, **kwargs):
            timeout_exit[0] = True

        while not timeout_exit[0]:
            t = self.__iter_dfs(stack, bound, timeout_exit, statistics, *args, **kwargs)
            if t == self.FOUND: 
                result = self.compute_solution(stack[-1], *args, **kwargs) 
                statistics['times'].append(round(timer.tocvalue(), 5))
                all_results.append(result)

                if self.should_exit(all_results, *args, **kwargs):
                    break
            if t == self.UNINITIALIZED_MIN:
                break
            bound = t
        statistics['time'] = round(timer.tocvalue(), 5)
        self.__log(f"Finished in {statistics['time']}s")

        th_timer.cancel()

        return all_results, statistics

    def __iter_dfs(self, stack: List[StateNode], bound: int, timeout_exit: list, *args, **kwargs) -> int:
        if len(stack) == 0: return 0
        if timeout_exit[0]: return self.UNINITIALIZED_MIN

        statistics = args[0]
        statistics['max_in_memory'] = max(statistics['max_in_memory'], len(stack))

        node = stack[-1]

        if statistics['max_depth'] < node.depth:
            statistics['max_depth'] = node.depth
            self.__log(f"New depth reached {statistics['max_depth']}")

        if node.final_cost > bound: return node.final_cost
        if self.check_solution(node): return self.FOUND

        min_cost = self.UNINITIALIZED_MIN
        for next_node in node.next_states():
            statistics['total_states'] += 1

            stack.append(next_node)
            t = self.__iter_dfs(stack, bound, timeout_exit, statistics)
            if t == self.FOUND: return self.FOUND
            if min_cost == self.UNINITIALIZED_MIN or t < min_cost:
                min_cost = t
            stack.pop()
        return min_cost

    def __bfs_traverse(self, root: StateNode, ordered=False, open_closed=False, *args, **kwargs) -> tuple:
        if ordered and not isinstance(root, Comparable):
            raise Exception(f"{root.__class__.__name__} must implement Comparable")
        if open_closed and not isinstance(root, Hashable):
            raise Exception(f"{root.__class__.__name__} must implement Hashable")

        all_results: list = []
        queue: Queue = PriorityQueue([root]) if ordered else SimpleQueue([root])

        if open_closed:
            closed_list: Set[str] = set()

        statistics: dict = {
            'time': 0,
            'times': [],
            'max_in_memory': 1,
            'total_states': 1,
        }

        max_depth = 0

        timer = TicToc()
        timer.tic()
        timeout_exit = [False]

        def handle_timeout():
            timeout_exit[0] = True

        th_timer = Timer(self.timeout, handle_timeout)
        th_timer.start()

        if not self.initial_has_solution(root, *args, **kwargs):
            timeout_exit[0] = True

        while not timeout_exit[0] and queue.size():
            statistics['max_in_memory'] = max(statistics['max_in_memory'], queue.size())

            current_node: StateNode = queue.pop()

            if open_closed:
                current_node_hash = cast(Hashable, current_node).hexdigest()
                
                if current_node_hash in closed_list:
                    continue
                
                closed_list.add(current_node_hash)

            if max_depth < current_node.depth:
                max_depth = current_node.depth
                self.__log(f"New depth reached {max_depth}")

            if self.check_solution(current_node, *args, **kwargs):
                result = self.compute_solution(current_node, *args, **kwargs)
                all_results.append(result)
                statistics['times'].append(round(timer.tocvalue(), 5))

                if self.should_exit(all_results, *args, **kwargs):
                    break
            
            
            successors = current_node.next_states(*args, **kwargs)

            for succ in successors:
                statistics['total_states'] += 1
                if open_closed and succ.hexdigest() in closed_list:
                    continue

                queue.push(succ)

        th_timer.cancel()

        statistics['time'] = round(timer.tocvalue(), 5)
        self.__log(f"Finished in {statistics['time']}s")

        statistics['max_depth'] = max_depth
        return (all_results, statistics)

    def __log(self, msg, level="INFO"):
        if self.logging:
            print (f"[{level}] {msg}")

    @abstractmethod
    def initial_has_solution(self, node: StateNode, *args, **kwargs) -> bool:
        raise NotImplementedError

    @abstractmethod
    def check_solution(self, node: StateNode, *args, **kwargs) -> bool:
        raise NotImplementedError

    @abstractmethod
    def compute_solution(self, node: StateNode, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def should_exit(self, results, *args, **kwargs) -> bool:
        raise NotImplementedError

class Queue(ABC, Generic[T]):
    def __init__(self, initial: List[T] = []):
        self.q = copy(initial)

    def size(self) -> int:
        return len(self.q)

    def extend(self, items: Iterable[T]):
        for item in items:
            self.push(item)

    @abstractmethod
    def push(self, item: T):
        raise NotImplementedError

    @abstractmethod
    def pop(self) -> T:
        raise NotImplementedError

class SimpleQueue(Queue):
    def push(self, item: T):
        self.q.append(item)

    def pop(self) -> T:
        return self.q.pop(0)

class PriorityQueue(Queue):
    def push(self, item: T):
        heappush(self.q, item)

    def pop(self) -> T:
        return heappop(self.q)