"""
Strengthen the between-rows finding: generate DIVERSE valid 196 colourings from
several different seed sources (different constructions/regions), then recompute
the cross-colouring forced skeleton and its multiplicative closure on the big set.
More & more diverse colourings -> tighter (truer) forced skeleton -> honest test
of whether the rigid core really is a multiplicative object.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from sat2 import build, vid
from weak_schur import verify_weak_schur
from pysat.solvers import Cadical195

N, k = 196, 5


def canon_of(parts, upto):
    col = {}
    for c, p in enumerate(parts):
        for v in p:
            col[v] = c
    remap, nxt, out = {}, 0, {}
    for v in range(1, upto + 1):
        if col[v] not in remap:
            remap[col[v]] = nxt; nxt += 1
        out[v] = remap[col[v]]
    return out


def read_parts(path):
    parts = []
    with open(path) as f:
        for line in f:
            if ":" in line:
                parts.append([int(x) for x in line.split(":", 1)[1].split()])
    return parts


def gen_from(seed_path, M, want):
    seed = canon_of(read_parts(seed_path), max(max(p) for p in read_parts(seed_path)))
    cl = build(N, k)
    for i in range(1, M + 1):
        cl.append([vid(i, seed[i], k)])
    s = Cadical195(bootstrap_with=cl)
    out = []
    for _ in range(want):
        s.conf_budget(6_000_000)
        if not s.solve_limited(expect_interrupt=True):
            break
        model = set(l for l in s.get_model() if l > 0)
        parts = [[] for _ in range(k)]
        for v in range(1, N + 1):
            for c in range(k):
                if vid(v, c, k) in model:
                    parts[c].append(v); break
        ok, _ = verify_weak_schur(parts, N)
        if ok:
            out.append(canon_of(parts, N))
        s.add_clause([-vid(v, [c for c in range(k) if vid(v, c, k) in model][0], k) for v in range(1, N + 1)])
    s.delete()
    return out


if __name__ == "__main__":
    sources = [("out/ws4_N66.txt", 30), ("out/eliahou_ws5_N196.txt", 30),
               ("out/eject_ws5_N195.txt", 30), ("out/sattail_ws5_N160.txt", 30)]
    cols = []
    t0 = time.time()
    for path, M in sources:
        if not os.path.exists(path):
            continue
        got = gen_from(path, M, 8)
        print(f"  {os.path.basename(path)} (M={M}): {len(got)} colourings ({time.time()-t0:.0f}s)", flush=True)
        cols.extend(got)
    # include Eliahou directly
    cols.append(canon_of(read_parts("out/eliahou_ws5_N196.txt"), N))
    print(f"  TOTAL colourings: {len(cols)}", flush=True)

    forced = [v for v in range(1, N + 1) if len(set(c[v] for c in cols)) == 1]
    lo = [v for v in forced if v <= 30]
    hi = [v for v in forced if v > 30]
    c2 = sum(1 for v in forced if 2 * v <= N and 2 * v in set(forced))
    n2 = sum(1 for v in forced if 2 * v <= N)
    c3 = sum(1 for v in forced if 3 * v <= N and 3 * v in set(forced))
    n3 = sum(1 for v in forced if 3 * v <= N)
    print(f"  forced (same across all {len(cols)}): {len(forced)}/{N}  (<=30: {len(lo)}, >30: {len(hi)})", flush=True)
    print(f"  forced closed under x2: {c2}/{n2} ({c2/max(n2,1):.0%})   x3: {c3}/{n3} ({c3/max(n3,1):.0%})", flush=True)
    # closure specifically on the genuine (>30) part vs random baseline
    print(f"  forced >30 skeleton: {sorted(hi)}", flush=True)
