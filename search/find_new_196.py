"""
The actual question: can we compute a NEW WS(5)=196 from scratch with the filters?

Blind SAT: never finishes. Filter (seed the small backbone from an independent
WS(4)=66, M=30): find a valid 196 fast, extract it, GATE-verify, and show it is
DISTINCT from the published Eliahou 196 (not a re-discovery, a fresh construction).
Block-and-resolve to pull several distinct ones.
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


def canon_coloring(parts, N, k):
    col = {}
    for c, p in enumerate(parts):
        for v in p:
            col[v] = c
    remap, nxt = {}, 0
    out = []
    for v in range(1, N + 1):
        if col[v] not in remap:
            remap[col[v]] = nxt; nxt += 1
        out.append(remap[col[v]])
    return out


if __name__ == "__main__":
    N, k = 196, 5
    seed = load_canon("out/ws4_N66.txt", 66)   # independent smaller answer
    M = 30
    cl = build(N, k)
    for i in range(1, M + 1):
        cl.append([vid(i, seed[i], k)])

    # reference: canonical Eliahou 196
    eparts = []
    with open("out/eliahou_ws5_N196.txt") as f:
        for line in f:
            if ":" in line:
                eparts.append([int(x) for x in line.split(":", 1)[1].split()])
    eli = canon_coloring(eparts, N, k)

    print(f"BLIND baseline: times out. FILTER (WS(4)-seed M={M}): finding 196 from scratch...", flush=True)
    s = Cadical195(bootstrap_with=cl)
    found = 0
    for attempt in range(3):
        s.conf_budget(8_000_000)
        t0 = time.time()
        res = s.solve_limited(expect_interrupt=True)
        dt = time.time() - t0
        if not res:
            print(f"  attempt {attempt}: {'UNSAT' if res is False else 'budget-out'} ({dt:.1f}s)", flush=True)
            break
        model = set(l for l in s.get_model() if l > 0)
        parts = [[] for _ in range(k)]
        for v in range(1, N + 1):
            for c in range(k):
                if vid(v, c, k) in model:
                    parts[c].append(v); break
        ok, reason = verify_weak_schur(parts, N)
        mine = canon_coloring(parts, N, k)
        diffs = sum(1 for i in range(N) if mine[i] != eli[i])
        found += 1
        print(f"  #{found}: valid 196 in {dt:.1f}s  GATE={'PASS' if ok else 'FAIL '+str(reason)}  "
              f"sizes={[len(p) for p in parts]}  differs from Eliahou in {diffs}/{N} elements "
              f"-> {'NEW construction' if diffs > 0 else 'same as Eliahou'}", flush=True)
        if ok and diffs > 0:
            with open(f"out/new_ws5_196_{found}.txt", "w") as f:
                for c, p in enumerate(parts):
                    f.write(f"part {c}: " + " ".join(map(str, p)) + "\n")
        # block this exact solution, resolve to get a distinct one
        block = [-l for l in model if abs(l) <= N * k]
        s.add_clause(block)
    s.delete()
    print(f"  >>> found {found} valid 196 colouring(s) from scratch via filter", flush=True)
