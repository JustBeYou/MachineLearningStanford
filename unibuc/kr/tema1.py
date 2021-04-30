from copy import copy, deepcopy
from searching import BreadthFirstTemplate, StateNode, PathIterator, Comparable, Hashable
from copy import deepcopy
from hashlib import md5

def main():
    N, K, lock, keys = load_from_file('tema1.txt')

    print (lock)
    for k in keys:
        print (k)
    print ('--- ' * 3)

    root = Node({
        'lock': lock,
        'keys': keys,
        'last_used': None,
    })

    solver = Solver(1)
    solutions, statistics = solver.traverse(root)
    print ('\n'.join(solutions[0]))

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

    return N, K, lock, keys

class Solver(BreadthFirstTemplate):
    def __init__(self, solutions_count, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.solutions_count = solutions_count

    def check_solution(self, node, *args, **kwargs):
        return sum(node.state['lock'].value) == 0

    def compute_solution(self, node, *args, **kwargs):
        display = lambda x: f"Lock {x.state['lock'].value} using key {x.state['last_used']} (cost {x.cost})"
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
            if new_lock.value in PathIterator(self, mode = lambda x: x.state['lock'].value):
                continue

            new_cost = (self.cost + 
                       self.arc_cost_fn(key.value, self.state['lock'].value, new_lock.value, new_lock.tricks))

            # replace only the used key
            if new_key_i.k > 0:
                new_keys[i] = new_key_i
            else:
                del new_keys[i]

            yield Node({'keys': new_keys, 'lock': new_lock, 'last_used': key.value}, parent=self, cost=new_cost)

    def arc_cost_fn(self, *args, **kwargs):
        key_value, current_state, next_state, tricks = args 
        cost = sum([nv < v for v, nv in zip(current_state, next_state)])

        for i in tricks:
            v, nv, j = current_state[i], next_state[i], tricks[i]

            if nv == 0 and v != nv and (current_state[j] > 0 or key_value[j] != -1) and (key_value[j] == -1):
                cost += 1

        return cost

    def __lt__(self, value):
        return self.cost < value.cost

    def hexdigest_internal(self):
        return md5(''.join(map(str, self.state['lock'].value)).encode('ascii')).hexdigest()

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

            # the trick rule :P
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