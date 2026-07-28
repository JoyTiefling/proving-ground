"""
Probe D -- fractional chromatic number of the weak-Schur sum-hypergraph, as an
UPPER-BOUND engine for WS(k), via dual column generation.

Vertices {1..N}, hyperedges {x,y,x+y} (x<y, x+y<=N). A proper colouring = no
monochromatic edge = every colour class weakly sum-free. chi_f <= chi, so:
        chi_f(H_N) > k   =>   chi(H_N) > k   =>   not k-colourable   =>   WS(k) < N.

chi_f = max  sum_v w_v   s.t.  sum_{v in S} w_v <= 1  for every weakly-sum-free set S,  w>=0.
A feasible w with sum_w > k is an ELEMENTARY, verifiable certificate that WS(k) < N
("5 classes carry weight <= 5 < sum_w, can't cover all vertices").

Dual column generation: master over current sets -> dual weights w -> pricer finds
the max-weight weakly-sum-free set; if its weight > 1 add it, else w is feasible
and sum_w is a valid lower bound on chi_f.

DISCIPLINE (CL-01): the pricer here is HEURISTIC, so sum_w is an OPTIMISTIC estimate
(overestimate) of chi_f -- a missed violating set keeps sum_w too high. Therefore:
  - if even this optimistic chi_f canNOT exceed k at the KNOWN boundaries
    (N=9 vs 2, N=24 vs 3, N=67 vs 4) -> LP is reliably TOOTHLESS, stop.
  - if it DOES exceed -> promising, but needs an EXACT pricer to certify (next build).
Litmus on known answers FIRST; only then k=5.
"""
import sys, time, random
import numpy as np

try:
    from scipy.optimize import linprog
except Exception as e:
    print("scipy required:", e); sys.exit(1)


def wsf_can_add(S, v):
    """Can v join weakly-sum-free set S and keep it weakly sum-free?"""
    for a in S:
        if a < v and (a + v) in S:      # pair (a,v), sum a+v already in S
            return False
        b = v - a                        # pair (a,b) summing to v
        if a < b and b in S:
            return False
    return True


def price(w, N, restarts=60, rng=None):
    """Heuristic max-weight weakly-sum-free set under weights w (1-indexed array)."""
    base = sorted(range(1, N + 1), key=lambda v: -w[v - 1])
    best_set, best_val = frozenset(), 0.0
    mx = max(w) if len(w) else 0.0
    for r in range(restarts):
        if r == 0:
            order = base
        else:
            order = sorted(range(1, N + 1),
                           key=lambda v: -(w[v - 1] + rng.random() * 0.4 * mx))
        S, val = set(), 0.0
        for v in order:
            if w[v - 1] <= 1e-12:
                continue
            if wsf_can_add(S, v):
                S.add(v); val += w[v - 1]
        if val > best_val:
            best_val, best_set = val, frozenset(S)
    return best_set, best_val


def chi_f(N, k, max_iter=300, verbose=True):
    rng = random.Random(12345)
    sets = [frozenset([v]) for v in range(1, N + 1)]
    sets.append(frozenset(range(N // 2 + 1, N + 1)))      # top-half wsf seed
    c = -np.ones(N)
    obj = float(N)
    for it in range(max_iter):
        A = np.zeros((len(sets), N))
        for i, S in enumerate(sets):
            for v in S:
                A[i, v - 1] = 1.0
        res = linprog(c, A_ub=A, b_ub=np.ones(len(sets)),
                      bounds=[(0, None)] * N, method="highs")
        if not res.success:
            print(f"  N={N} LP failed: {res.message}"); return None
        w = res.x
        obj = -res.fun
        S, val = price(w, N, rng=rng)
        if verbose and (it < 5 or it % 10 == 0):
            print(f"    N={N} it={it:3d} sum_w={obj:7.4f} pricer={val:6.4f} sets={len(sets)}", flush=True)
        if val <= 1 + 1e-6:
            if verbose:
                print(f"  N={N}: chi_f≈{obj:.4f}  (heuristic-converged, {len(sets)} sets)", flush=True)
            return obj
        sets.append(S)
    print(f"  N={N}: chi_f≈{obj:.4f}  (iter cap)", flush=True)
    return obj


if __name__ == "__main__":
    print("== LITMUS on known boundaries (does chi_f detect WS(k)?) ==", flush=True)
    litmus = [(9, 2), (24, 3), (67, 4)]      # N = WS(k)+1 ; need chi_f > k
    passed = True
    for N, k in litmus:
        t0 = time.time()
        v = chi_f(N, k, verbose=False)
        ok = v is not None and v > k + 1e-6
        print(f"  WS({k})={N-1}:  chi_f(H_{N})={v:.4f}  vs k={k}  ->  "
              f"{'DETECTS (>k)' if ok else 'MISSES (<=k) toothless'}  ({time.time()-t0:.1f}s)", flush=True)
        if not ok:
            passed = False
    if not passed:
        print("\nLP is toothless on known boundaries -> chi_f relaxation too weak. Pivot.", flush=True)
        sys.exit(0)

    print("\n== chi_f has teeth -> climb k=5 from N=197 ==", flush=True)
    for N in [197, 220, 250, 280, 320, 360, 400]:
        t0 = time.time()
        v = chi_f(N, 5, verbose=True)
        print(f"  >>> N={N}: chi_f={v:.4f}  {'*** >5: WS(5)<'+str(N)+' (heuristic, verify exact) ***' if v and v>5+1e-6 else '(<=5)'}  ({time.time()-t0:.1f}s)\n", flush=True)
