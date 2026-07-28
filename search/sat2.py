"""
Weak-Schur SAT with STRONG symmetry breaking — give the solver a real chance.

Earlier conclusion "brute force is intractable" was measured only at 200s with a
weak encoding. That is not "needs a supercomputer" — it is "the solver was never
given proper pruning." The colour-permutation symmetry (k! = 120 for k=5) is the
big lever: with first-occurrence breaking, colour c may appear at element v only
if colour c-1 already appeared earlier. That alone can cut the search ~120x.

Sanity first (CL-04): does strong symmetry breaking make N=196 (known SAT) solve
fast? If yes, the encoding was the bottleneck and N=197 gets a real long run.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa
from pysat.solvers import Cadical195


def vid(v, c, k):
    return (v - 1) * k + c + 1


def build(N, k):
    cl = []
    for v in range(1, N + 1):
        cl.append([vid(v, c, k) for c in range(k)])              # at-least-one
        for c1 in range(k):
            for c2 in range(c1 + 1, k):
                cl.append([-vid(v, c1, k), -vid(v, c2, k)])      # at-most-one
    # STRONG symmetry break: colour c used at v => colour c-1 used at some u<v
    for v in range(1, N + 1):
        for c in range(1, k):
            cl.append([-vid(v, c, k)] + [vid(u, c - 1, k) for u in range(1, v)])
    # weak Schur: no monochromatic a<b, a+b=z
    for c in range(k):
        for a in range(1, N + 1):
            for b in range(a + 1, N + 1):
                z = a + b
                if z > N:
                    break
                cl.append([-vid(a, c, k), -vid(b, c, k), -vid(z, c, k)])
    return cl


def solve(N, k, budget):
    cl = build(N, k)
    t0 = time.time()
    with Cadical195(bootstrap_with=cl) as s:
        # pysat has no native timeout; rely on outer process timeout for long runs
        sat = s.solve()
        dt = time.time() - t0
        if sat is None:
            return "UNKNOWN", None, dt
        if not sat:
            return "UNSAT", None, dt
        model = set(l for l in s.get_model() if l > 0)
        parts = [[] for _ in range(k)]
        for v in range(1, N + 1):
            for c in range(k):
                if vid(v, c, k) in model:
                    parts[c].append(v); break
        return "SAT", parts, dt


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 196
    k = 5
    budget = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    print(f"SAT2 (strong symmetry) k={k} N={N}", flush=True)
    status, parts, dt = solve(N, k, budget)
    print(f"  status={status}  ({dt:.1f}s)", flush=True)
    if status == "SAT":
        ok, reason = verify_weak_schur(parts, N)
        print(f"  GATE: {'PASS' if ok else 'FAIL ' + str(reason)}  sizes={[len(p) for p in parts]}")
        if ok:
            with open(os.path.join(os.path.dirname(__file__), "out", f"sat2_ws5_N{N}.txt"), "w") as f:
                for c, p in enumerate(parts):
                    f.write(f"part {c}: " + " ".join(map(str, p)) + "\n")
            print(f"  saved -> out/sat2_ws5_N{N}.txt")
        if ok and N > 196:
            print(f"  *** N={N} > 196 SAT — CANDIDATE NEW BOUND, adversarial re-verify ***")
    elif status == "UNSAT" and N == 197:
        print("  *** UNSAT at 197 => WS(5)=196 PROVEN (Walker confirmed) — verify independently ***")
