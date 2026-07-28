"""
Measure max power-of-2 chain length inside a valid WSF k-coloring of [1..N].

WSF k-coloring assigns each v in {1..N} one of k colors such that no color class
contains a<b<z with a+b=z (weak: a=b, i.e. 2a=z, is allowed). A "power-of-2 chain"
inside a color class c is a set {m, 2m, 4m, ..., 2^(L-1)*m} all colored c
(equivalently, L-1 consecutive doublings f(v)=f(2v) along the 2-adic chain of
odd-part m). We can restrict m to odd without loss (any longer chain in a 2-adic
tower is a suffix of the odd-rooted one).

Empirical claim under test (14-07 wake 12:00, solo): for all 5 valid k=5 WSF
records at N in [187..196], the profile of max-chain-length per color is
[4-5, 2, 2, 2, 2]. Refined empirical bound: |D| ~ log_2(N) + k + O(1), where
the top chain length is the dominant term.

This tool: given N, k, ask SAT "does there exist a valid WSF k-coloring of
[1..N] with some monochromatic power-of-2 chain of length >= L?". Binary
search on L gives max_chain(N, k). Sweep N to test log_2(N)+k form.

Encoding on top of sat_weak_schur:
  s_{m,c}       = fresh selector "chain rooted at odd m in color c has length >= L"
  s_{m,c} -> var(v,c) for every v in {m, 2m, ..., 2^(L-1)*m}
  clause        = OR_{m,c} s_{m,c}   (at least one such chain exists)

Every SAT answer is re-verified by verifiers/weak_schur.verify_weak_schur
before it is trusted, and the chain is separately checked to actually sit in
one color class of length >= L.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa

from pysat.solvers import Cadical195


def vid(v: int, c: int, k: int) -> int:
    """1-based CNF variable id for (element v in 1..N, part c in 0..k-1).
    Matches sat_weak_schur.vid so shared encoding stays compatible."""
    return (v - 1) * k + c + 1


def build_wsf_cnf(N: int, k: int):
    """Base WSF k-coloring CNF over vars vid(v,c) for v in 1..N, c in 0..k-1.
    Uses the same symmetry break as sat_weak_schur (element v may use part c
    only if c <= v-1)."""
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


def chain_from(m: int, L: int, N: int):
    """Return power-of-2 chain [m, 2m, ..., 2^(L-1)*m] if it fits in [1..N],
    else None. m does not need to be odd for correctness — restricting to odd
    is a search-space reduction (see module docstring)."""
    chain = [m * (1 << i) for i in range(L)]
    return chain if chain[-1] <= N else None


def solve_chain_at_least(N: int, k: int, L: int, time_limit=None):
    """SAT-check: exists valid WSF k-coloring of [1..N] with some monochromatic
    power-of-2 chain of length >= L?

    Returns (status, partition_or_None, chain_or_None, elapsed).
    status in {'SAT','UNSAT','UNKNOWN'}. When SAT, partition passes the WSF
    gate and chain is one witnessed [m, 2m, ..., 2^(L-1)*m] all in one color."""
    clauses = build_wsf_cnf(N, k)

    # Reserve fresh IDs for selectors above the vid range.
    next_id = N * k + 1
    selectors = []
    # (m, c) -> (selector_id, chain_vals) for post-hoc witness extraction.
    sel_meta = {}

    # Restrict m to odd; any chain rooted at even m is a suffix of an odd-rooted one.
    m = 1
    max_m = N // (1 << (L - 1))
    while m <= max_m:
        chain = chain_from(m, L, N)
        if chain is None:
            m += 2
            continue
        for c in range(k):
            # Symmetry break: color c requires c <= v-1 for every v in chain.
            # Since m >= 1, the tightest bound is c <= m-1; if violated, s is unsat.
            if c > m - 1:
                continue
            sid = next_id
            next_id += 1
            selectors.append(sid)
            sel_meta[sid] = (m, c, chain)
            # s -> var(v,c) for every v in chain. L clauses per selector.
            for v in chain:
                clauses.append([-sid, vid(v, c, k)])
        m += 2

    if not selectors:
        # No odd m at all -> L too big for this N. UNSAT by construction.
        return "UNSAT", None, None, 0.0
    # At least one chain must exist.
    clauses.append(selectors[:])

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
        for v in range(1, N + 1):
            for c in range(k):
                if vid(v, c, k) in model_pos:
                    parts[c].append(v)
                    break
        # Witness: any selector that came out true.
        witness = None
        for sid in selectors:
            if sid in model_pos:
                witness = sel_meta[sid]
                break
        return "SAT", parts, witness, dt


def max_chain_length(N: int, k: int, L_min: int = 2, L_max: int = None,
                     verbose: bool = True):
    """Find largest L such that a valid WSF k-coloring of [1..N] admits a
    monochromatic power-of-2 chain of length L. Linear scan up from L_min
    until UNSAT (chains are short: ~log_2 N, so a few probes suffice).

    Returns (best_L, best_partition, best_chain, log)."""
    if L_max is None:
        L_max = N.bit_length()  # floor(log_2 N)+1 is a safe ceiling
    log = []
    best = (None, None, None)
    L = L_min
    while L <= L_max:
        status, parts, witness, dt = solve_chain_at_least(N, k, L)
        log.append((L, status, dt))
        if verbose:
            print(f"  N={N} k={k} L>={L}: {status} ({dt:.2f}s)")
        if status == "SAT":
            best = (L, parts, witness)
            L += 1
        elif status == "UNSAT":
            break
        else:
            # UNKNOWN under time_limit — stop conservatively at last confirmed.
            break
    return (*best, log)


def _sanity_witness(parts, witness, k):
    """Independent check: the witness chain is monochromatic in `parts`
    and matches its declared color. Returns (ok, reason)."""
    if witness is None:
        return False, "no witness"
    m, c, chain = witness
    color_of = {}
    for i, p in enumerate(parts):
        for v in p:
            color_of[v] = i
    for v in chain:
        if color_of.get(v) != c:
            return False, f"chain member {v} not in color {c} (got {color_of.get(v)})"
    return True, f"chain {chain} monochrome in color {c}"


def _cli():
    """CLI: sat_chain_maxlen.py [k [N [L_min]]]. Default k=5, N=196, L_min=2."""
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    N = int(sys.argv[2]) if len(sys.argv) > 2 else 196
    L_min = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    print(f"SAT max-chain: k={k} N={N} L_min={L_min}")
    best_L, parts, witness, log = max_chain_length(N, k, L_min=L_min)
    if best_L is None:
        print(f"  no valid chain found at L>={L_min}. Log: {log}")
        return
    ok_gate, reason_gate = verify_weak_schur(parts, N)
    ok_wit, reason_wit = _sanity_witness(parts, witness, k)
    print(f"  best L = {best_L}")
    print(f"  WSF gate: {'PASS' if ok_gate else 'FAIL — ' + str(reason_gate)}")
    print(f"  witness : {'PASS' if ok_wit else 'FAIL — ' + str(reason_wit)}")
    if ok_gate and ok_wit:
        m, c, chain = witness
        print(f"  witness chain: odd root m={m} in color {c}, length {len(chain)}: {chain}")
        # Log line for the sweep table.
        print(f"  ROW  N={N} k={k} max_chain={best_L} log2N={N.bit_length()-1}"
              f" bound=log2N+k={N.bit_length()-1+k}")


if __name__ == "__main__":
    _cli()
