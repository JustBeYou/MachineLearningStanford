from abc import ABC, abstractmethod
from heapq import heappop, heappush
from typing import Optional, Callable, List, Iterable
from copy import copy

class StateNode(ABC):
    def __init__(self, state, parent: Optional['StateNode'] = None,
                 cost=0, heuristic_cost=0,
                 arc_cost_fn: Optional[Callable] = None,
                 heuristic_fn: Optional[Callable] = None):
        
        if arc_cost_fn is None:
            arc_cost_fn = StateNode.__default_arc_cost

        if heuristic_fn is None:
            heuristic_fn = StateNode.__default_heuristic

        self.state = state
        self.parent = parent
        self.cost = cost
        self.heuristic_cost = heuristic_cost
        self.final_cost = self.cost + self.heuristic_cost

        self.arc_cost_fn = arc_cost_fn
        self.heuristic_fn = heuristic_fn

    @abstractmethod
    def next_states(self, *args, **kwargs) -> Iterable:
        raise NotImplementedError

    @staticmethod
    def __default_arc_cost(current_state = None, next_state = None):
        return 1

    @staticmethod
    def __default_heuristic(*args, **kwargs):
        return 0

    def __repr__(self):
        return f"< {'(root) ' if self.parent is None else ''}Node ({self.state}) with cost {self.cost} >"

class Comparable(ABC):
    @abstractmethod
    def __lt__(self, value):
        raise NotImplementedError

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

class BreadthFirstTemplate(ABC):
    def traverse(self, root: StateNode, ordered = False, *args, **kwargs) -> list:
        if ordered and not isinstance(root, Comparable):
            raise Exception(f"{root.__class__.__name__} must implement Comparable")

        all_results: list = []
        queue: Queue = PriorityQueue([root]) if ordered else SimpleQueue([root])

        while queue.size():
            current_node: StateNode = queue.pop()

            if self.check_solution(current_node, *args, **kwargs):
                result = self.compute_solution(current_node, *args, **kwargs)
                all_results.append(result)

                if self.should_exit(all_results, *args, **kwargs):
                    break
            
            queue.extend(current_node.next_states(*args, **kwargs))

        return all_results

    @abstractmethod
    def check_solution(self, node: StateNode, *args, **kwargs) -> bool:
        raise NotImplementedError

    @abstractmethod
    def compute_solution(self, node: StateNode, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def should_exit(self, results, *args, **kwargs) -> bool:
        raise NotImplementedError

class Queue(ABC):
    def __init__(self, initial = []):
        self.q = copy(initial)

    def size(self):
        return len(self.q)

    def extend(self, items):
        for item in items:
            self.push(item)

    @abstractmethod
    def push(self, item):
        raise NotImplementedError

    @abstractmethod
    def pop(self):
        raise NotImplementedError

class SimpleQueue(Queue):
    def push(self, item):
        self.q.append(item)

    def pop(self):
        return self.q.pop(0)

class PriorityQueue(Queue):
    def push(self, item):
        heappush(self.q, item)

    def pop(self):
        return heappop(self.q)