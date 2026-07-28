"""
Side-quest C: do the FILTERS speed up finding WS(5)=196?

The blind SAT timed out. Hypothesis: the boundary is rigid (forced backbone in the
small numbers). Test: fix the prefix {1..M} to a canonically-relabelled valid
colouring (Eliahou 196), then SAT-solve N=196. Sweep M. If a modest M makes the
solver finish in seconds (vs timeout at M=0), the rigid backbone IS the key pruning
the blind solver lacked -> filters validated as search accelerators.

Caveat (CL-04): fixing to Eliahou's prefix hands the solver part of a known solution,
so this measures "is the tail easy GIVEN the backbone", i.e. rigidity-as-pruning, not
a fully blind speedup. Honest framing.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from sat2 import build, vid          # noqa
from pysat.solvers import Cadical195


def load_canon(path, N, k):
    col = {}
    parts = []
    with open(path) as f:
        for line in f:
            if ":" in line:
                parts.append([int(x) for x in line.split(":", 1)[1].split()])
    for c, p in enumerate(parts):
        for v in p:
            col[v] = c
    # first-occurrence canonical relabel
    remap = {}
    nxt = 0
    canon = {}
    for v in range(1, N + 1):
        oc = col[v]
        if oc not in remap:
            remap[oc] = nxt; nxt += 1
        canon[v] = remap[oc]
    return canon


def solve_with_backbone(N, k, canon, M, conf_budget=3_000_000):
    cl = build(N, k)
    for i in range(1, M + 1):
        cl.append([vid(i, canon[i], k)])      # fix f(i)=canon[i]
    t0 = time.time()
    s = Cadical195(bootstrap_with=cl)
    s.conf_budget(conf_budget)
    res = s.solve_limited(expect_interrupt=True)
    dt = time.time() - t0
    s.delete()
    status = "SAT" if res else ("UNSAT" if res is False else "BUDGET-OUT")
    return status, dt


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 196
    k = 5
    canon = load_canon("out/eliahou_ws5_N196.txt", 196, k)   # canon defined on 1..196
    print(f"backbone-fix SAT sweep, N={N} k={k}, conf_budget=3M per solve", flush=True)
    Ms = [int(x) for x in sys.argv[2:]] or [0, 10, 20, 30, 40, 50, 66, 80]
    for M in Ms:
        status, dt = solve_with_backbone(N, k, canon, M)
        print(f"  M={M:3d} fixed: {status:11s} {dt:7.1f}s", flush=True)
