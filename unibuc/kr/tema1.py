from copy import copy, deepcopy
from searching import SearchingTemplate, StateNode, PathIterator, Comparable, Hashable
from copy import deepcopy
from hashlib import md5
from sys import argv
from os import path, listdir

def main():
    if len(argv) < 5:
        print (f"Usage: {argv[0]} <solutions count> <timeout> <input directory> <output directory>")
        return

    nsol = int(argv[1])
    timeout = int(argv[2])
    input_dir = argv[3]
    input_files = listdir(input_dir)
    output_dir = argv[4]

    for filename in input_files:
        solve_for_input(nsol, timeout, filename, input_dir, output_dir)  

def solve_for_input(nsol, timeout, filename, input_dir, outdir):
    f = open(path.join(outdir, filename), "w")

    try:
        N, K, lock, keys = load_from_file(path.join(input_dir, filename))
    except Exception as e:
        custom_print(f"Invalid input\n{str(e)}", f=f)
        return

    print (lock)
    for k in keys:
        print (k)
    print ('--- ' * 3)

    initial_state = {
        'lock': lock,
        'keys': keys,
        'last_used': None,
    }

    root = Node(initial_state, None)

    s = Solver(nsol, logging=False, timeout=timeout)
    so, st = s.bfs(root)
    print_solutions("BFS", so, st, f=f)

    so, st = s.ucs(root)
    print_solutions("UCS", so, st, f=f)

    nodes = [HNaiveNode, H1Node, H2Node, HBadNode]
    for node in nodes:
        solve_with_heur(node, initial_state, s, f)

    f.close()

def solve_with_heur(node_type, initial_state, s, f):
    root = node_type(initial_state, None)
    so, st = s.a_star(root)
    print_solutions(f"A* using {node_type.title}", so, st, f=f)

    so, st = s.a_star_opt(root)
    print_solutions(f"A* open-closed using {node_type.title}", so, st, f=f)

    so, st = s.ida_star(root)
    print_solutions(f"IDA* using {node_type.title}", so, st, f=f)

def print_solutions(title, solutions, statistics, f=None):
    custom_print (f"*** {title} ***", f=f)
    custom_print (f"Total time elapsed {statistics['time']}s", f=f)
    ratio = round(statistics['max_in_memory'] / statistics['total_states'], 4)
    custom_print (f"Max in memory / Total generated = {statistics['max_in_memory']} / {statistics['total_states']} ratio = {ratio}", f=f)
    if len(solutions):
        for i, s in enumerate(solutions):
            custom_print (f"Solution {i}", f=f)
            custom_print (f"Length {len(s)} Time {statistics['times'][i]}s", f=f)
            custom_print ('\n'.join(s), f=f)
            custom_print (f=f)
    else:
        custom_print ("No solutions",f=f)
    custom_print (f=f)

def custom_print(s="", f=None):
    print(s)
    print(s, file=f)

def load_from_file(fname):
    content = open(fname).readlines()
    
    K = int(content[0].strip())
    tricks = {}

    i = 1
    while '->' in content[i]:
        a, b = map(int, content[i].strip().split('->'))
        tricks[a] = b
        i += 1

    N = len(content[i].strip())
    keys = [Key(content[j].strip(), K) for j in range(i, len(content))]
    lock = Lock(N, tricks)

    assert all(map(lambda key: len(key.value) == N, keys)), "Keys have invalid length"
    assert all(map(lambda i: tricks[i] != i, tricks)), "Self-referencing trick"
    assert min(tricks.keys()) >= 0, "Trick out of bounds (key < 0)"
    assert max(tricks.keys()) < N, "Trick out of bounds (key >= N)"
    assert min(tricks.values()) >= 0, "Trick out of bounds (value < 0)"
    assert max(tricks.values()) < N, "Trick out of bounds (value >= N)"

    return N, K, lock, keys

def perm_has_cycles(g, N):
    visited = [False for _ in range(N)]

    for k in g:
        if visited[k]:
            continue

        q = k
        while q in g:
            if visited[q]:
                return True

            visited[q] = True
            q = g[q]
        visited[q] = True

    return False

class Solver(SearchingTemplate):
    def __init__(self, solutions_count, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.solutions_count = solutions_count

    def initial_has_solution(self, node, *args, **kwargs):
        return not perm_has_cycles(node.state['lock'].tricks, len(node.state['lock'].value))

    def check_solution(self, node, *args, **kwargs):
        return sum(node.state['lock'].value) == 0

    def compute_solution(self, node, *args, **kwargs):
        display = lambda x: f"Lock {x.state['lock'].value} using key {x.state['last_used']} (cost {x.cost}, h {x.heuristic_cost}, f {x.final_cost})"
        return list(PathIterator(node, mode = display))[::-1]

    def should_exit(self, results, *args, **kwargs):
        return len(results) >= self.solutions_count

class Node(StateNode, Comparable, Hashable):
    def next_states(self, *args, **kwargs):
        for i, key in enumerate(self.state['keys']):
            # copy all references
            new_keys = copy(self.state['keys'])

            # compute the new state
            new_key_i, new_lock = key.apply(self.state['lock'])

            # check if we already reached this position
            if new_lock.value in PathIterator(self, mode = lambda x: x.state_value()):
                continue

            # replace only the used key
            if new_key_i.k > 0:
                new_keys[i] = new_key_i
            else:
                del new_keys[i]

            yield self.__class__({
                'keys': new_keys,
                'lock': new_lock,
                'last_used': key.value,
            }, parent=self)

    def state_value(self):
        return self.state['lock'].value

    def arc_cost_fn(self, *args, **kwargs):
        if self.parent == None: return 0

        key_value = self.state['last_used']
        parent_state = self.parent.state['lock'].value
        current_state = self.state['lock'].value
        tricks = self.state['lock'].tricks
        
        cost = self.parent.cost + sum([nv < v for v, nv in zip(parent_state, current_state)])

        for i in tricks:
            v, nv, j = parent_state[i], current_state[i], tricks[i]

            if nv == 0 and v != nv and (parent_state[j] > 0 or key_value[j] != -1) and (key_value[j] == -1):
                cost += 1

        return cost

    def __lt__(self, value):
        return self.cost < value.cost

    def hexdigest_internal(self):
        h = md5(ilstr(self.state['lock'].value))
        #for k in self.state['keys']:
        #    h.update(ilstr(k.value))
        return h.hexdigest()

def ilstr(l):
    return ''.join(map(str, l)).encode('ascii')

class HNode(Node):
    def __lt__(self, value):
        return self.final_cost < value.final_cost

class HNaiveNode(HNode):
    title = "Naive heuristic"

    def heuristic_fn(self, *args, **kwargs):
        return 0 if sum(self.state['lock'].value) == 0 else 1


class H1Node(HNode):
    title = "Heuristic 1"

    def heuristic_fn(self, *args, **kwargs):
        return sum(self.state['lock'].value)

class H2Node(HNode):
    title = "Heuristic 2"

    def heuristic_fn(self, *args, **kwargs):
        tricks_cost = sum(self.state['lock'].value)
        for i, v in enumerate(self.state['lock'].value):
            tricks_cost += (1 if (v > 0 and 
                i in self.state['lock'].tricks and
                not any(filter(lambda key: key.value[self.state['lock'].tricks[i]] < 0, self.state['keys']))
                ) else 0)
        return tricks_cost

class HBadNode(HNode):
    title = "Inadmissible heuristic"

    def heuristic_fn(self, *args, **kwargs):
        tricks_cost = 0
        for i, v in enumerate(self.state['lock'].value):
            tricks_cost += 1 if v > 0 and i in self.state['lock'].tricks else 0
        return tricks_cost

class Lock:
    def __init__(self, n, tricks):
        self.value = [1 for i in range(n)]
        self.tricks = tricks

    @staticmethod
    def from_value(value, tricks):
        lock = Lock(0, tricks)
        lock.value = value
        return lock

    def __repr__(self):
        return f"Lock {self.value}"

class Key:
    values_table = {
        'i': +1,
        'd': -1,
        'g':  0,
    }

    def __init__(self, s, k):
        if type(s) == str:
            self.value = [self.values_table[c] for c in s]
        elif type(s) == list:
            self.value = s
        else:
            raise Exception("Argument must be of type str or list")
        self.k = k

    def apply(self, lock):
        if self.k == 0:
            raise Exception("The key is broken")

        add_rule = lambda a, b: max(a + b, 0)
        new_lock_value = [add_rule(a, b) for a, b in zip(self.value, lock.value)]

        for i in lock.tricks:
            v, nv, j = lock.value[i], new_lock_value[i], lock.tricks[i]

            # the (naive) trick rule :P
            # if the position is unlocked (nv == 0)
            # and it was unlocked just now (v != nv)
            # and the target position was locked before (lock.value[j] > 0)
            # or the key was not unlocking on the target position (self.value[j] != -1)
            # then we should lock the target position one time (new_lock_value[j] += 1)
            if nv == 0 and v != nv and (lock.value[j] > 0 or self.value[j] != -1):
                new_lock_value[j] += 1
                
        return Key(self.value, self.k - 1), Lock.from_value(new_lock_value, lock.tricks)

    def __repr__(self):
        return f'Key ({self.k}) {self.value}'

main()