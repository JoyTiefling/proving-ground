"""
Certified bounds for r-neighbor bootstrap percolation on Q_d via SAT.

Question: does there exist a percolating set S of size <= k?
  SAT   -> yes; the model gives an explicit S (independently re-checked with
           verify.percolates -- we NEVER trust the solver's internal cascade vars).
  UNSAT -> no set of size <= k percolates, so m(Q_d, r) >= k+1. Certified.

Encoding (staged / timed, justified-infection form)
---------------------------------------------------
Vertices 0..N-1, N = 2^d. Rounds t = 0..T, T = N (a safe upper bound on the
number of cascade rounds: at least one new vertex per round, so any percolating
set finishes within N rounds).

Variables:
  s_v          : v is in the seed set S (infected at round 0)
  a_{v,t}      : v is infected by the end of round t

Clauses:
  (1) seed link      a_{v,0} <-> s_v
  (2) monotonicity   a_{v,t} -> a_{v,t+1}
  (3) justified      a vertex may only become newly infected if it truly had
                     >= r infected neighbours in the previous round.
                     "at least r of d neighbours infected" == "at most (d-r)
                     uninfected" == every (d-r+1)-subset W of N(v) contains an
                     infected vertex.  So for each such subset W:
                        (a_{v,t}) OR (NOT a_{v,t+1}) OR (OR_{u in W} a_{u,t})
                     Read: if v was uninfected at t and infected at t+1, then
                     W is not all-uninfected. Holding for every (d-r+1)-subset
                     forces >= r infected neighbours. No auxiliary reification
                     variables -- the rule is encoded directly.
  (4) percolation    a_{v,T} = 1 for all v (everything ends infected)
  (5) cardinality    sum_v s_v <= k  (PySAT totalizer)

This encoding is intentionally minimal: it forbids UNjustified infections and
requires full coverage. It does NOT force an infection to happen the instant it
becomes possible -- that is fine, monotonicity + T=N let any real cascade fit.
Correctness rests on: SAT model => extract S from s_v => the *real* simulator
verify.percolates(S) must return True. That independent check is the contract.
"""

from itertools import combinations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from verify import percolates, neighbors  # noqa: E402

from pysat.formula import CNF, IDPool       # noqa: E402
from pysat.card import CardEnc, EncType      # noqa: E402
from pysat.solvers import Cadical153         # noqa: E402


def build_cnf(d: int, r: int, k: int, T: int | None = None):
    """Build the CNF for 'exists percolating set of size <= k in Q_d under r'.

    Returns (cnf, pool, s_vars) where s_vars[v] is the SAT var id for s_v.
    """
    N = 1 << d
    if T is None:
        T = N  # safe upper bound on cascade rounds

    pool = IDPool()
    s = {v: pool.id(("s", v)) for v in range(N)}
    a = {(v, t): pool.id(("a", v, t)) for v in range(N) for t in range(T + 1)}

    cnf = CNF()

    # (1) seed link: a_{v,0} <-> s_v
    for v in range(N):
        cnf.append([-a[(v, 0)], s[v]])
        cnf.append([a[(v, 0)], -s[v]])

    # (2) monotonicity: a_{v,t} -> a_{v,t+1}
    for v in range(N):
        for t in range(T):
            cnf.append([-a[(v, t)], a[(v, t + 1)]])

    # (3) justified infection
    subset_size = d - r + 1  # every W of this size must contain an infected nb
    for v in range(N):
        nbrs = list(neighbors(v, d))
        for t in range(T):
            for W in combinations(nbrs, subset_size):
                clause = [a[(v, t)], -a[(v, t + 1)]] + [a[(u, t)] for u in W]
                cnf.append(clause)

    # (4) percolation: everything infected at the final round
    for v in range(N):
        cnf.append([a[(v, T)]])

    # (5) cardinality: sum s_v <= k
    card = CardEnc.atmost(
        lits=[s[v] for v in range(N)], bound=k,
        vpool=pool, encoding=EncType.totalizer,
    )
    cnf.extend(card.clauses)

    return cnf, pool, s


def exists_percolating_at_most(d: int, r: int, k: int, T: int | None = None):
    """Return (result, witness).

    result: 'SAT' or 'UNSAT'.
    witness: sorted tuple of seed vertices if SAT (already re-checked with the
             real simulator), else None. Raises AssertionError if the SAT model
             fails the independent verify.percolates check (would signal an
             encoding bug -- the whole point of the contract).
    """
    N = 1 << d
    cnf, pool, s = build_cnf(d, r, k, T)
    with Cadical153(bootstrap_with=cnf.clauses) as solver:
        sat = solver.solve()
        if not sat:
            return "UNSAT", None
        model = set(solver.get_model())
        seed = frozenset(v for v in range(N) if s[v] in model)
        # CONTRACT: independently verify with the real simulator.
        assert percolates(seed, d, r), (
            f"SAT model claims size-{len(seed)} seed percolates but "
            f"verify.percolates disagrees -- ENCODING BUG. seed={sorted(seed)}"
        )
        assert len(seed) <= k, f"seed size {len(seed)} > k={k} -- cardinality bug"
        return "SAT", tuple(sorted(seed))


def find_m(d: int, r: int, k_hi: int, k_lo: int = 1, verbose: bool = True):
    """Find exact m(Q_d, r) by descending from a known upper bound k_hi.

    Assumes a percolating set of size k_hi exists (or will be found). Descends
    k until UNSAT, so m = (last SAT k) ... actually m = first k where size-k is
    SAT and size-(k-1) is UNSAT. Returns (m, witness_at_m).
    """
    best_k, best_w = None, None
    k = k_hi
    while k >= k_lo:
        res, w = exists_percolating_at_most(d, r, k)
        if verbose:
            print(f"  d={d} r={r} k<={k}: {res}"
                  + (f"  witness={w}" if w else ""))
        if res == "SAT":
            best_k, best_w = len(w), w  # actual size may be < k
            k = len(w) - 1              # try to beat the true size
        else:
            # size-k UNSAT => m = k+1
            return (k + 1, best_w) if best_k is not None else (None, None)
    return (best_k, best_w) if best_k is not None else (None, None)


if __name__ == "__main__":
    print("SAT bootstrap-percolation bound finder — self-test on d=3, r=3")
    m, w = find_m(3, 3, k_hi=5)
    print(f"  => m(Q_3, 3) = {m}, witness {w}  (known: 4)")
