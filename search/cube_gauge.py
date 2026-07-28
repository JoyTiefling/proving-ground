"""
Gauge the cube-count: how many distinct backbones branch out?

For the exact theorem WS(5)=196 via cube-and-conquer we must refute 197 for every
viable backbone. Feasibility = how many cubes. Rough gauge: fix a small core (ws4
M0=30, keeps solving fast), then enumerate DISTINCT {1..L} prefixes of valid 196
colourings by block-prefix-and-resolve. If they flood (thousands fast) the cube
space is Heule-scale; if it saturates quickly, an on-our-hardware proof is real.
(This counts prefixes sharing the fixed core -> a SLICE/lower-feel of the true count.)
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from sat2 import build, vid
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


if __name__ == "__main__":
    N, k = 196, 5
    M0 = 30           # fixed core (fast)
    L = 50            # prefix length we enumerate distinct values of
    seed = load_canon("out/ws4_N66.txt", 66)
    cl = build(N, k)
    for i in range(1, M0 + 1):
        cl.append([vid(i, seed[i], k)])
    s = Cadical195(bootstrap_with=cl)
    seen = set()
    t0 = time.time()
    cap, tbudget = 3000, 200
    while time.time() - t0 < tbudget and len(seen) < cap:
        s.conf_budget(8_000_000)
        res = s.solve_limited(expect_interrupt=True)
        if not res:
            print(f"  EXHAUSTED: all distinct {{1..{L}}} prefixes enumerated", flush=True)
            break
        model = set(l for l in s.get_model() if l > 0)
        col = {}
        for v in range(1, L + 1):
            for c in range(k):
                if vid(v, c, k) in model:
                    col[v] = c; break
        prefix = tuple(col[v] for v in range(1, L + 1))
        seen.add(prefix)
        # block this prefix
        s.add_clause([-vid(v, col[v], k) for v in range(1, L + 1)])
        if len(seen) % 200 == 0:
            print(f"  {len(seen)} distinct {L}-prefixes ({time.time()-t0:.0f}s)", flush=True)
    s.delete()
    dt = time.time() - t0
    print(f">>> distinct {{1..{L}}} prefixes (core {M0} fixed): {len(seen)} in {dt:.0f}s "
          f"({'saturated' if len(seen)<cap else 'still flooding -> large'})", flush=True)
