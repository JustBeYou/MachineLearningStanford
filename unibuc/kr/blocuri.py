from searching import BreadthFirstTemplate, StateNode, PathIterator, Comparable, Hashable
from copy import deepcopy
from hashlib import md5

def main():
    initial_state, final_states = load_from_file("input.txt")
    print("Starting position")
    print_stacks(initial_state)
    print()

    print ("Target positions")
    for i, state in enumerate(final_states):
        print(f"Position #{i+1}")
        print_stacks(state)
        print()

    root: StacksStateNode[list] = StacksStateNode(initial_state)
    solver = BFSolver(final_states, 1)
    
    solutions, statistics = solver.traverse(root)
    print(f"One solution using BFS ({statistics['steps']} steps with cost {statistics['best_cost']})")
    for i, step in enumerate(solutions[0][1:]):
        print(f"Move #{i+1}")
        print_stacks(step.state)
        print()

    solutions, statistics =  solver.traverse(root, open_closed=True)
    print(f"One solution using BFS (open-closed) ({statistics['steps']} steps with cost {statistics['best_cost']})")
    for i, step in enumerate(solutions[0][1:]):
        print(f"Move #{i+1}")
        print_stacks(step.state)
        print()

    solutions, statistics =  solver.traverse(root, ordered=True)
    print(f"One solution using UCS ({statistics['steps']} steps with cost {statistics['best_cost']})")
    for i, step in enumerate(solutions[0][1:]):
        print(f"Move #{i+1}")
        print_stacks(step.state)
        print()

    solutions, statistics =  solver.traverse(root, ordered=True, open_closed=True)
    print(f"One solution using UCS (open-closed) ({statistics['steps']} steps with cost {statistics['best_cost']})")
    for i, step in enumerate(solutions[0][1:]):
        print(f"Move #{i+1}")
        print_stacks(step.state)
        print()

class BFSolver(BreadthFirstTemplate):
    def __init__(self, final_states, solutions_count, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.final_states = final_states
        self.solutions_count = solutions_count

    def check_solution(self, node, *args, **kwargs):
        return node.state in self.final_states

    def compute_solution(self, node, *args, **kwargs):
        return list(PathIterator(node, mode = PathIterator.NODE_MODE))[::-1]

    def should_exit(self, results, *args, **kwargs):
        return len(results) >= self.solutions_count

class StacksStateNode(StateNode, Comparable, Hashable):
    def next_states(self, *args, **kwargs):
        stacks = self.state
        stacks_size = len(stacks)

        for i in range(stacks_size):
            if len(stacks[i]) == 0:
                continue

            temp_stacks = deepcopy(stacks)
            block = temp_stacks[i].pop()

            for j in range(stacks_size):
                if i == j:
                    continue

                new_stacks = deepcopy(temp_stacks)
                new_stacks[j].append(block)

                if new_stacks not in PathIterator(self, mode = PathIterator.STATE_ONLY_MODE):
                    new_cost = self.cost + self.arc_cost_fn(block=block)
                    yield StacksStateNode(new_stacks, 
                        parent=self, 
                        cost=new_cost, heuristic_cost=0)

    def arc_cost_fn(self, *args, **kwargs):
        return ord(kwargs['block']) - ord('a') + 1

    def __lt__(self, other):
        return self.cost < other.cost

    def hexdigest_internal(self):
        s = '|'.join([''.join(x) if len(x) else '#' for x in self.state])
        return s

def load_from_file(name):
    content = open(name).read().split('stari_finale')
    initial_state = parse_stacks(content[0].strip())
    final_states = [
            parse_stacks(stare.strip())
            for stare in content[1].split('---')]

    return initial_state, final_states

def parse_stacks(string):
    parts = string.split('\n')
    return [[c for c in s.split(' ')]
            if '#' != s else [] for s in parts]

def print_stacks(stacks):
    print("--- --- ---")
    for stack in stacks:
        print(f"# {' '.join(stack)}")
    print("--- --- ---")

main()