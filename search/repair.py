"""
Targeted repair: take a near-solution (few conflicts) and search a SHORT
sequence of element-recolorings that drives conflicts to 0.

The annealer stalls on the last conflict because single random flips can't
execute the coordinated multi-move "chain" that resolves it. A bounded DFS that
always attacks a currently-conflicting triple and recolors one of its elements
CAN find such a chain — and the tree is small because each level branches only
over the 3 elements of one bad triple x (k-1) colors.

This is minimal perturbation, not brute force: depth-bounded, conflict-focused.
A conf=0 result is gate-verified.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa
from structured_search import State  # noqa


def load_saved(path):
    parts = []
    with open(path) as f:
        for line in f:
            if ":" in line:
                parts.append([int(x) for x in line.split(":", 1)[1].split()])
    return parts


def repair(st, max_depth, deadline):
    if st.conf == 0:
        return True
    if max_depth == 0 or time.time() > deadline:
        return False
    idx = min(st.badset)  # deterministic: attack a fixed bad triple
    a, b, z = st.triples[idx]
    # order moves by resulting conflict delta (greedy-best-first)
    moves = []
    for e in (a, b, z):
        old = st.color[e]
        for c in range(st.k):
            if c != old:
                moves.append((st.delta_if(e, c), e, c, old))
    moves.sort()
    for _, e, c, old in moves:
        st.flip(e, c)
        if repair(st, max_depth - 1, deadline):
            return True
        st.flip(e, old)
    return False


def run(path, N, k, max_depth=8, budget=60):
    parts = load_saved(path)
    color = [0] * (N + 1)
    for c, p in enumerate(parts):
        for n in p:
            color[n] = c
    st = State(N, k, color)
    print(f"loaded {path}: conf={st.conf}")
    ok = repair(st, max_depth, time.time() + budget)
    if ok and st.conf == 0:
        out = [[] for _ in range(k)]
        for n in range(1, N + 1):
            out[st.color[n]].append(n)
        g, reason = verify_weak_schur(out, N)
        print(f"REPAIRED to conf=0  gate={'PASS' if g else 'FAIL ' + str(reason)}")
        if g:
            fn = os.path.join(os.path.dirname(path), f"ws{k}_N{N}.txt")
            with open(fn, "w") as f:
                for i, p in enumerate(out):
                    f.write(f"part {i}: {' '.join(map(str, p))}\n")
            print(f"  saved valid construction -> {fn}")
            return True
    else:
        print(f"no repair within depth={max_depth}, budget={budget}s (conf now {st.conf})")
    return False


if __name__ == "__main__":
    path = sys.argv[1]
    N = int(sys.argv[2]) if len(sys.argv) > 2 else 196
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    run(path, N, k,
        max_depth=int(sys.argv[4]) if len(sys.argv) > 4 else 8,
        budget=int(sys.argv[5]) if len(sys.argv) > 5 else 60)
