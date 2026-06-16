"""
SAT attack on weak Schur lower bounds.

Find a k-partition of {1..N} with every part weakly sum-free, by encoding to
CNF and solving with a modern SAT solver (CaDiCaL via pysat). Modern solvers
are vastly stronger than the 2012 ones that first nailed WS(5)=196, so this is
the primary lane for trying to push the bound.

Encoding:
  var(v,c) = "element v is in part c",  v in 1..N, c in 0..k-1.
  - at-least-one  : OR_c var(v,c)                      (every element placed)
  - at-most-one   : pairwise !var(v,c1) | !var(v,c2)   (one part per element)
  - weak Schur    : for each c, each a<b with a+b<=N:
                    !var(a,c) | !var(b,c) | !var(a+b,c)  (no mono weak triple)
  - symmetry break: element v may use part c only if c <= v-1 (capped k-1).
                    Breaks the k! color-permutation symmetry.

Every SAT result is independently re-checked by the verifier gate before it is
trusted. No claim without a runnable gate.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa

from pysat.solvers import Cadical195
from pysat.card import CardEnc  # noqa (kept for future at-most-one variants)


def vid(v: int, c: int, k: int) -> int:
    """1-based CNF variable id for (element v in 1..N, part c in 0..k-1)."""
    return (v - 1) * k + c + 1


def build_cnf(N: int, k: int):
    clauses = []
    for v in range(1, N + 1):
        allowed = [c for c in range(k) if c <= v - 1]  # symmetry break
        # at-least-one (over allowed parts)
        clauses.append([vid(v, c, k) for c in allowed])
        # forbid disallowed parts explicitly (unit clauses)
        for c in range(k):
            if c not in allowed:
                clauses.append([-vid(v, c, k)])
        # at-most-one over allowed parts (pairwise)
        for i in range(len(allowed)):
            for j in range(i + 1, len(allowed)):
                clauses.append([-vid(v, allowed[i], k), -vid(v, allowed[j], k)])
    # weak Schur: no monochromatic a<b, a+b=z
    for c in range(k):
        for a in range(1, N + 1):
            for b in range(a + 1, N + 1):  # a<b strict (weak: 2a allowed)
                z = a + b
                if z > N:
                    break
                clauses.append([-vid(a, c, k), -vid(b, c, k), -vid(z, c, k)])
    return clauses


def solve(N: int, k: int, time_limit=None):
    """Returns (status, partition_or_None, elapsed).
    status in {'SAT','UNSAT','UNKNOWN'}."""
    clauses = build_cnf(N, k)
    t0 = time.time()
    with Cadical195(bootstrap_with=clauses) as s:
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
                    parts[c].append(v)
                    break
        return "SAT", parts, dt


if __name__ == "__main__":
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    N = int(sys.argv[2]) if len(sys.argv) > 2 else 196
    print(f"SAT weak Schur: k={k}, N={N}")
    status, parts, dt = solve(N, k)
    print(f"  status={status}  ({dt:.2f}s)")
    if status == "SAT":
        ok, reason = verify_weak_schur(parts, N)
        print(f"  GATE: {'PASS' if ok else 'FAIL — ' + str(reason)}")
        if ok:
            sizes = [len(p) for p in parts]
            print(f"  part sizes: {sizes} (sum={sum(sizes)})")
            # persist construction for study (not a claim unless N>known best)
            outdir = os.path.join(os.path.dirname(__file__), "out")
            os.makedirs(outdir, exist_ok=True)
            fn = os.path.join(outdir, f"ws{k}_N{N}.txt")
            with open(fn, "w") as f:
                for i, p in enumerate(parts):
                    f.write(f"part {i}: {' '.join(map(str, p))}\n")
            print(f"  saved -> {fn}")
