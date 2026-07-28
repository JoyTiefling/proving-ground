"""
NON-circular construction test: do the filters find WS(5)=196 from the SMALLER
known answer WS(4)=66 (not from a known 196)?

Seed the prefix {1..M} with OUR independent ws4_N66 colouring (4 colours), add a
5th colour, SAT-solve {1..196}. Sweep M. If it solves fast at M~30-50 (like the
circular C test that fixed Eliahou's prefix), the speed-up comes from the generic
backbone structure -- demonstrated WITHOUT knowing 196 => non-circular.

(Eliahou's 196 uses colour 4 only from 67 on, so its {1..66} IS a 4-colouring --
seeding by WS(4) is the honest, non-circular version of fixing the backbone.)
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from sat2 import build, vid
from pysat.solvers import Cadical195


def load_canon(path):
    parts = []
    with open(path) as f:
        for line in f:
            if ":" in line:
                parts.append([int(x) for x in line.split(":", 1)[1].split()])
    col = {}
    for c, p in enumerate(parts):
        for v in p:
            col[v] = c
    M = max(col)
    remap = {}
    nxt = 0
    canon = {}
    for v in range(1, M + 1):
        if col[v] not in remap:
            remap[col[v]] = nxt; nxt += 1
        canon[v] = remap[col[v]]
    return canon, M


def solve(N, k, canon, M, conf_budget=3_000_000):
    cl = build(N, k)
    for i in range(1, M + 1):
        cl.append([vid(i, canon[i], k)])
    t0 = time.time()
    s = Cadical195(bootstrap_with=cl)
    s.conf_budget(conf_budget)
    res = s.solve_limited(expect_interrupt=True)
    dt = time.time() - t0
    s.delete()
    return ("SAT" if res else "UNSAT" if res is False else "BUDGET-OUT"), dt


if __name__ == "__main__":
    N, k = 196, 5
    canon, seedlen = load_canon("out/ws4_N66.txt")
    print(f"NON-circular: seed = ws4_N66 (independent), solve N={N} k={k}", flush=True)
    for M in [0, 20, 30, 40, 50, 66]:
        if M > seedlen:
            continue
        status, dt = solve(N, k, canon, M)
        print(f"  M={M:3d} (ws4 prefix fixed): {status:11s} {dt:7.1f}s", flush=True)
