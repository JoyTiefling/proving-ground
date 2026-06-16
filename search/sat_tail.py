"""
Hybrid: fix the bulk [1..K] from our best construction, then COMPLETELY solve
the tail [K+1..197] with SAT. Unlike ejection-from-195 (which froze [1..195] and
nudged one element), this lets the solver recolor [K+1..195] freely and search
the whole tail exhaustively. If a valid [1..197] exists with this fixed prefix,
Cadical finds it (-> candidate 197); if not, UNSAT for this base. The fixed
prefix collapses the search via unit propagation, so it should be fast.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa
from seed_construct import load_saved  # noqa
from sat_weak_schur import build_cnf, vid  # noqa
from pysat.solvers import Cadical195


def run(infile, K, N=197, k=5, budget=120):
    parts = load_saved(infile)
    color = {}
    for c, p in enumerate(parts):
        for n in p:
            color[n] = c
    # CANONICAL RELABEL (first-occurrence order) so fixed colors are compatible
    # with build_cnf's symmetry-breaking (element v may use color <= v-1).
    relabel, nxt = {}, 0
    for n in range(1, N + 1):
        oc = color.get(n)
        if oc is not None and oc not in relabel:
            relabel[oc] = nxt
            nxt += 1
    color = {n: relabel[c] for n, c in color.items()}
    clauses = build_cnf(N, k)
    # fix [1..K] to the construction's colors (unit clauses)
    fixed = 0
    for n in range(1, K + 1):
        if n in color:
            clauses.append([vid(n, color[n], k)])
            fixed += 1
    print(f"  fixed {fixed} elements [1..{K}], solving tail [{K+1}..{N}]...", flush=True)
    t0 = time.time()
    with Cadical195(bootstrap_with=clauses) as s:
        sat = s.solve()
        dt = time.time() - t0
        if sat is None:
            print(f"  UNKNOWN ({dt:.1f}s)")
            return
        if not sat:
            print(f"  UNSAT: this base+prefix cannot reach {N}  ({dt:.1f}s)")
            return
        model = set(l for l in s.get_model() if l > 0)
        out = [[] for _ in range(k)]
        for n in range(1, N + 1):
            for c in range(k):
                if vid(n, c, k) in model:
                    out[c].append(n)
                    break
        ok, reason = verify_weak_schur(out, N)
        print(f"  SAT! gate@{N}: {'PASS' if ok else 'FAIL ' + str(reason)}  ({dt:.1f}s)")
        if ok:
            with open(os.path.join(os.path.dirname(infile), f"sattail_ws5_N{N}.txt"), "w") as f:
                for i, p in enumerate(out):
                    f.write(f"part {i}: {' '.join(map(str, p))}\n")
            print(f"  *** N={N} REACHED via SAT-tail — CANDIDATE, adversarial re-verify ***")


if __name__ == "__main__":
    here = os.path.dirname(__file__)
    infile = os.path.join(here, "out", sys.argv[1] if len(sys.argv) > 1 else "eject_ws5_N195.txt")
    K = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    N = int(sys.argv[3]) if len(sys.argv) > 3 else 197
    run(infile, K, N)
