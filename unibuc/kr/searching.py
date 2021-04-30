from abc import ABC, abstractmethod
from heapq import heappop, heappush
from typing import Optional, Callable, List, Iterable, Set, Generic, TypeVar, cast
from copy import copy

T = TypeVar('T')
class StateNode(ABC, Generic[T]):
    def __init__(self, state: T, parent: Optional['StateNode'] = None,
                 cost=0, heuristic_cost=0):

        self.state = state
        self.parent = parent
        self.cost = cost
        self.heuristic_cost = heuristic_cost
        self.final_cost = self.cost + self.heuristic_cost

    @abstractmethod
    def next_states(self, *args, **kwargs) -> Iterable:
        raise NotImplementedError

    def arc_cost_fn(self, *args, **kwargs):
        return 1

    def heuristic_fn(self, *args, **kwargs):
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

class BreadthFirstTemplate(ABC):
    def traverse(self, root: StateNode, ordered=False, open_closed=False, *args, **kwargs) -> tuple:
        if ordered and not isinstance(root, Comparable):
            raise Exception(f"{root.__class__.__name__} must implement Comparable")
        if open_closed and not isinstance(root, Hashable):
            raise Exception(f"{root.__class__.__name__} must implement Hashable")

        all_results: list = []
        queue: Queue = PriorityQueue([root]) if ordered else SimpleQueue([root])
        hashes: Set[str] = set()
        statistics = {
            'steps': 0,
        }

        while queue.size():
            statistics['steps'] += 1

            current_node: StateNode = queue.pop()
            if open_closed and cast(Hashable, current_node).hexdigest() in hashes:
                continue
            elif open_closed:
                hashes.add(cast(Hashable, current_node).hexdigest())

            if self.check_solution(current_node, *args, **kwargs):
                result = self.compute_solution(current_node, *args, **kwargs)
                all_results.append(result)

                if self.should_exit(all_results, *args, **kwargs):
                    break
            
            successors = current_node.next_states(*args, **kwargs)
            queue.extend(
                filter(
                    lambda x: cast(Hashable, x).hexdigest() not in hashes, 
                    successors) if open_closed else successors
            )

        return (all_results, statistics)

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