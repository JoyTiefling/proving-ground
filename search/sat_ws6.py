"""
Launch the method fresh on WS(6) (record >=646): self-similar seed + 6th colour.

WS(6) construction contains a WS(5) one as a prefix. So fix {1..196} to our
gate-verified Eliahou 196 (5 colours 0-4), allow a 6th colour (5) for 197..N, and
SAT-solve {1..N} for growing N. Largest SAT N = our WS(6) lower bound via the method.
If the full-196 seed is a dead-end (UNSAT), fall back to a partial backbone seed.
Every SAT model is gate-checked before it counts.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from sat2 import build, vid
from weak_schur import verify_weak_schur
from pysat.solvers import Cadical195


def load_canon(path, upto):
    parts = []
    with open(path) as f:
        for line in f:
            if ":" in line:
                parts.append([int(x) for x in line.split(":", 1)[1].split()])
    col = {}
    for c, p in enumerate(parts):
        for v in p:
            col[v] = c
    remap, nxt, canon = {}, 0, {}
    for v in range(1, upto + 1):
        if col[v] not in remap:
            remap[col[v]] = nxt; nxt += 1
        canon[v] = remap[col[v]]
    return canon


def solve(N, k, canon, M, conf_budget=6_000_000):
    cl = build(N, k)
    for i in range(1, M + 1):
        cl.append([vid(i, canon[i], k)])
    t0 = time.time()
    s = Cadical195(bootstrap_with=cl)
    s.conf_budget(conf_budget)
    res = s.solve_limited(expect_interrupt=True)
    dt = time.time() - t0
    parts = None
    if res:
        model = set(l for l in s.get_model() if l > 0)
        parts = [[] for _ in range(k)]
        for v in range(1, N + 1):
            for c in range(k):
                if vid(v, c, k) in model:
                    parts[c].append(v); break
    s.delete()
    return ("SAT" if res else "UNSAT" if res is False else "BUDGET-OUT"), dt, parts


if __name__ == "__main__":
    k = 6
    canon = load_canon("out/eliahou_ws5_N196.txt", 196)
    M = int(sys.argv[1]) if len(sys.argv) > 1 else 196
    print(f"WS(6) via self-similar seed: fix {{1..{M}}} = Eliahou196, 6th colour free", flush=True)
    best = 0
    sweep = [int(x) for x in sys.argv[2:]] or [250, 350, 450, 550, 646]
    for N in sweep:
        status, dt, parts = solve(N, k, canon, M)
        gate = ""
        if status == "SAT":
            ok, reason = verify_weak_schur(parts, N)
            gate = f" GATE={'PASS' if ok else 'FAIL:'+str(reason)}"
            if ok:
                best = max(best, N)
                with open(f"out/ws6_seed_N{N}.txt", "w") as f:
                    for c, p in enumerate(parts):
                        f.write(f"part {c}: " + " ".join(map(str, p)) + "\n")
        print(f"  N={N:3d}: {status:11s} {dt:7.1f}s{gate}", flush=True)
    print(f"  >>> WS(6) lower bound reached via method (M={M} seed): {best}", flush=True)
