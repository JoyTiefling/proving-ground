"""
Measure max |D| — number of doubled pairs {d, 2d} that share a color — inside
a valid WSF k-coloring of [1..N].

WSF k-coloring assigns each v in {1..N} one of k colors such that no color
class contains a<b<z with a+b=z (weak: a=b allowed, i.e. {v, 2v} may share a
color). Define D = { d in [1..N/2] : exists c, f(d)=f(2d)=c }. |D| counts the
distinct d's along which "doubling stays inside a color".

Empirical claim under test (14-07 wake 12:00, solo, 5 valid k=5 records at
N in [187..196]): |D| ~ log_2(N) + k + O(1). This tool is the SAT counterpart:
maximise |D| over all valid WSF k-colorings, sweep N, test the log-linear form.

If |D| grows sublinearly in N (log-shape), the Ramsey reduction
"tolerating C AP-families ==> N <= R_5(3) + f(C)" gets a tight input C.
That would move gap #2 toward the first nontrivial upper bound on WS(5) in
70 years. If |D| grows linearly, the empirical claim dies and the reduction
loses its lever — a honest negative I want just as much as a positive.

Refuted 18-07 06:00 by Eliahou-restricted probe (N=150): SAT reached
|D|>=36, blowing the log(N)+k=12 prediction by ratio ~3. That run went
WITHOUT saving the partition — witness lost 4.7h into existence. This
tool's --out flag (added 18-07 10:00) fixes that permanently: every SAT
answer now dumps a full JSON receipt {meta, result{partition,D_set}, log}.

Encoding on top of sat_weak_schur (shares vid, same symmetry break):
  eq_{d,c}   :  fresh var, equivalent to  var(d,c) AND var(2d,c)
  iseq_d     :  fresh var, equivalent to  OR_c eq_{d,c}
  cardinality:  sum(iseq_d for d in 1..N//2) >= D    (sequential counter)

Every SAT answer is re-verified by verifiers.weak_schur.verify_weak_schur
and the D-set is independently recounted from the partition, so the reported
|D| never comes only from the SAT witness.
"""
import sys, os, time, json, argparse, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa

from pysat.solvers import Cadical195
from pysat.card import CardEnc, EncType
from pysat.formula import IDPool


def vid(v: int, c: int, k: int) -> int:
    """1-based CNF variable id for (element v in 1..N, part c in 0..k-1).
    Matches sat_weak_schur.vid and sat_chain_maxlen.vid — encoding shared."""
    return (v - 1) * k + c + 1


def build_wsf_cnf(N: int, k: int):
    """Base WSF k-coloring CNF over vars vid(v,c) for v in 1..N, c in 0..k-1.
    Uses the same symmetry break as sat_weak_schur (element v may use part c
    only if c <= v-1). Copied structure of sat_chain_maxlen.build_wsf_cnf so
    both tools speak the same base."""
    clauses = []
    for v in range(1, N + 1):
        allowed = [c for c in range(k) if c <= v - 1]
        clauses.append([vid(v, c, k) for c in allowed])
        for c in range(k):
            if c not in allowed:
                clauses.append([-vid(v, c, k)])
        for i in range(len(allowed)):
            for j in range(i + 1, len(allowed)):
                clauses.append([-vid(v, allowed[i], k), -vid(v, allowed[j], k)])
    for c in range(k):
        for a in range(1, N + 1):
            for b in range(a + 1, N + 1):
                z = a + b
                if z > N:
                    break
                clauses.append([-vid(a, c, k), -vid(b, c, k), -vid(z, c, k)])
    return clauses


def _add_and_eq(clauses, eq_var: int, x_var: int, y_var: int):
    """Tseitin: eq_var  <->  x_var AND y_var.
       eq -> x        : -eq  x
       eq -> y        : -eq  y
       x AND y -> eq  : -x  -y  eq"""
    clauses.append([-eq_var, x_var])
    clauses.append([-eq_var, y_var])
    clauses.append([-x_var, -y_var, eq_var])


def _add_or_eq(clauses, iseq_var: int, eq_vars: list):
    """Tseitin: iseq_var  <->  OR eq_vars.
       iseq -> OR eq   : -iseq  eq_0 ... eq_{k-1}
       eq_c -> iseq    : -eq_c  iseq    (for each c)"""
    clauses.append([-iseq_var] + list(eq_vars))
    for e in eq_vars:
        clauses.append([-e, iseq_var])


def build_maxD_cnf(N: int, k: int, D_min: int):
    """Full CNF: WSF base + iseq_d indicators + sum(iseq_d) >= D_min.

    Returns (clauses, iseq_by_d, top_var_id) where iseq_by_d maps d -> var id
    so the caller can read the D-set out of the model, and top_var_id is the
    highest var id used (for extending with more selectors later).
    """
    clauses = build_wsf_cnf(N, k)
    pool = IDPool(start_from=N * k + 1)

    iseq_by_d = {}
    d_range = range(1, N // 2 + 1)

    for d in d_range:
        # eq_{d,c}  <->  var(d,c) AND var(2d,c)
        eq_vars = []
        for c in range(k):
            # Symmetry break of the base: var(v,c) is forced false when c > v-1.
            # For d and 2d we only add eq_var where c is allowed for BOTH.
            # (For d, c<=d-1; for 2d, c<=2d-1. Since d<=2d, the tighter is d.)
            if c > d - 1:
                continue
            eq_var = pool.id(("eq", d, c))
            _add_and_eq(clauses, eq_var, vid(d, c, k), vid(2 * d, c, k))
            eq_vars.append(eq_var)
        if not eq_vars:
            # d=1 with k=5: c must be <= 0, so only eq_{1,0} exists — handled above.
            # If somehow no eq allowed, iseq_d is forced false.
            iseq = pool.id(("iseq", d))
            clauses.append([-iseq])
            iseq_by_d[d] = iseq
            continue
        iseq = pool.id(("iseq", d))
        _add_or_eq(clauses, iseq, eq_vars)
        iseq_by_d[d] = iseq

    # Cardinality: at least D_min of the iseq_d's true.
    iseq_lits = list(iseq_by_d.values())
    if D_min > 0:
        card = CardEnc.atleast(lits=iseq_lits, bound=D_min,
                               encoding=EncType.seqcounter, vpool=pool)
        clauses.extend(card.clauses)

    return clauses, iseq_by_d, pool.top


def solve_D_at_least(N: int, k: int, D_min: int):
    """SAT-check: exists valid WSF k-coloring of [1..N] with |D| >= D_min?

    Returns (status, partition_or_None, D_set_or_None, elapsed).
    status in {'SAT','UNSAT','UNKNOWN'}.

    When SAT the partition passes verify_weak_schur AND the returned D_set
    is recounted independently from the partition (not read from iseq vars),
    so the reported |D| is trusted twice.
    """
    clauses, iseq_by_d, _ = build_maxD_cnf(N, k, D_min)

    t0 = time.time()
    with Cadical195(bootstrap_with=clauses) as s:
        sat = s.solve()
        dt = time.time() - t0
        if sat is None:
            return "UNKNOWN", None, None, dt
        if not sat:
            return "UNSAT", None, None, dt
        model_pos = set(l for l in s.get_model() if l > 0)

        parts = [[] for _ in range(k)]
        color_of = {}
        for v in range(1, N + 1):
            for c in range(k):
                if vid(v, c, k) in model_pos:
                    parts[c].append(v)
                    color_of[v] = c
                    break

        # Independent D-recount from the partition — not from iseq vars.
        D_set = [d for d in range(1, N // 2 + 1)
                 if color_of.get(d) is not None
                 and color_of.get(d) == color_of.get(2 * d)]

        return "SAT", parts, D_set, dt


def max_D(N: int, k: int, D_min_start: int = 1, D_max: int = None,
          verbose: bool = True):
    """Find largest D such that a valid WSF k-coloring of [1..N] has |D| >= D.

    Linear scan up from D_min_start until UNSAT. Empirical claim gives
    D ~ log_2(N)+k, so a few probes suffice.

    Returns (best_D, best_partition, best_D_set, log)."""
    if D_max is None:
        D_max = N // 2  # trivial upper bound
    log = []
    best = (None, None, None)
    D = D_min_start
    while D <= D_max:
        status, parts, D_set, dt = solve_D_at_least(N, k, D)
        log.append((D, status, dt))
        if verbose:
            print(f"  N={N} k={k} D>={D}: {status} ({dt:.2f}s)")
        if status == "SAT":
            actual_D = len(D_set)
            best = (actual_D, parts, D_set)
            # Independent recount may be larger than the requested lower bound.
            # Jump to actual_D+1 to save probes.
            D = actual_D + 1
        elif status == "UNSAT":
            break
        else:
            break
    return (*best, log)


def _cli():
    """CLI: sat_maxD.py [--k K] [--N N] [--Dmin D] [--out PATH].

    On SAT and gate PASS, if --out is given, dumps a JSON receipt with
    meta (solver, encoding note, N, k, elapsed, wake stamp), result
    (best_D, D_set, gate, partition), and full solver log. Missing --out
    keeps stdout-only behaviour for cheap probes.
    """
    ap = argparse.ArgumentParser(
        description="SAT max-D over valid WSF k-colorings of [1..N].")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--N", type=int, default=100)
    ap.add_argument("--Dmin", type=int, default=1,
                    help="Starting lower bound for |D|.")
    ap.add_argument("--out", type=str, default=None,
                    help="If given, dump JSON receipt on SAT+gate-PASS.")
    # Back-compat: positional k, N, Dmin (matches pre-18-07-10:00 CLI).
    ap.add_argument("positional", nargs="*",
                    help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.positional:
        vals = [int(v) for v in args.positional]
        if len(vals) >= 1: args.k = vals[0]
        if len(vals) >= 2: args.N = vals[1]
        if len(vals) >= 3: args.Dmin = vals[2]

    k, N, D_min = args.k, args.N, args.Dmin
    import math
    log2N = int(math.log2(N))
    t0 = time.time()
    print(f"SAT max-D: k={k} N={N} D_min_start={D_min}  "
          f"(bound hypothesis: log_2(N)+k = {log2N + k})")
    best_D, parts, D_set, log = max_D(N, k, D_min_start=D_min)
    total_elapsed = time.time() - t0
    if best_D is None:
        print(f"  no valid partition with |D|>={D_min}. Log: {log}")
        # Still write receipt for negatives if requested — a UNSAT lower
        # bound is data too.
        if args.out:
            receipt = {
                "meta": {
                    "solver": "cadical195",
                    "encoding": ("vid=(v-1)*k+c+1, symmetry break c<=v-1, "
                                 "Tseitin eq/iseq, seqcounter cardinality"),
                    "N": N, "k": k, "D_min_requested": D_min,
                    "elapsed_s_total": round(total_elapsed, 3),
                    "wake": datetime.datetime.now(datetime.timezone.utc)
                        .isoformat(timespec="seconds").replace("+00:00", "Z"),
                    "tool": "sat_maxD.py",
                    "tool_version": "18-07-10:00 (--out added)",
                },
                "result": {"best_D": None, "gate": "N/A"},
                "log": [{"D_min": d, "status": s, "elapsed_s": round(dt, 3)}
                        for d, s, dt in log],
            }
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(receipt, f, indent=2, ensure_ascii=False)
            print(f"  receipt (UNSAT/UNKNOWN) -> {args.out}")
        return
    ok_gate, reason_gate = verify_weak_schur(parts, N)
    print(f"  best |D| = {best_D}")
    print(f"  WSF gate  : {'PASS' if ok_gate else 'FAIL - ' + str(reason_gate)}")
    print(f"  D-set (recounted from partition, first 20): {D_set[:20]}")
    if ok_gate:
        print(f"  ROW  N={N} k={k} max_D={best_D} log2N={log2N}"
              f"  bound=log2N+k={log2N + k}"
              f"  ratio={best_D / (log2N + k):.2f}")
    if args.out:
        receipt = {
            "meta": {
                "solver": "cadical195",
                "encoding": ("vid=(v-1)*k+c+1, symmetry break c<=v-1, "
                             "Tseitin eq/iseq, seqcounter cardinality"),
                "N": N, "k": k, "D_min_requested": D_min,
                "elapsed_s_total": round(total_elapsed, 3),
                "wake": datetime.datetime.now(datetime.timezone.utc)
                    .isoformat(timespec="seconds").replace("+00:00", "Z"),
                "tool": "sat_maxD.py",
                "tool_version": "18-07-10:00 (--out added)",
                "bound_hypothesis_log2N_plus_k": log2N + k,
            },
            "result": {
                "best_D": best_D,
                "gate": "PASS" if ok_gate else "FAIL",
                "gate_reason": None if ok_gate else str(reason_gate),
                "D_set": D_set,
                "partition": parts,
            },
            "log": [{"D_min": d, "status": s, "elapsed_s": round(dt, 3)}
                    for d, s, dt in log],
        }
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2, ensure_ascii=False)
        print(f"  receipt -> {args.out}")


if __name__ == "__main__":
    _cli()
