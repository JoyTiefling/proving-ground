"""
SAT for completely multiplicative (CM) sequences of bounded discrepancy.

Question: does there exist a CM sequence f: [1..N] -> {+1,-1} with
Erdős discrepancy <= D?
  SAT   -> yes; the prime-sign assignment is extracted and INDEPENDENTLY
           re-checked with verify.discrepancy_via_prefix (never trust the
           solver's internal automaton).
  UNSAT -> no CM sequence of length N stays within [-D, D], so C_CM(D) < N.

Encoding
--------
Recall the reduction (verify.py, numerically confirmed): for CM f,
    disc_N(f) = max_{1<=k<=N} | sum_{j=1}^k f(j) |.
So we bound the PREFIX SUMS. f(n)'s sign bit sb_n in {0,1} (0=+1, 1=-1):
    sb_1 = 0;  sb_p = b_p (free, per prime p);
    sb_n = sb_{spf(n)} XOR sb_{n/spf(n)}   (complete multiplicativity).

Prefix-sum automaton. State q_{k,v} means "partial sum S_k = v", v in [-D..D].
    q_{0,0} = 1, others 0.
    exactly-one over v at each layer k.
    step: from S_{k-1}=v, f(k)=+1 (sb_k=0) -> S_k=v+1; f(k)=-1 (sb_k=1) -> v-1.
      (¬q_{k-1,v} ∨ sb_k ∨ q_{k,v+1})     [+1 step; if v+1>D the last literal
                                            drops -> forbids overflow]
      (¬q_{k-1,v} ∨ ¬sb_k ∨ q_{k,v-1})    [-1 step; if v-1<-D -> forbids underflow]
    Together with exactly-one per layer this is a faithful bounded counter.

Contract: SAT model -> extract prime signs -> verify.build_cm +
discrepancy_via_prefix MUST be <= D. That independent check is the gate.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from verify import build_cm, discrepancy_via_prefix, primes_up_to, _smallest_prime_factor  # noqa: E402

from pysat.formula import CNF, IDPool       # noqa: E402
from pysat.card import CardEnc, EncType      # noqa: E402
from pysat.solvers import Cadical153         # noqa: E402


def build_cnf(N: int, D: int):
    """CNF for 'exists CM sequence on [1..N] with discrepancy <= D'.

    Returns (cnf, pool, prime_bit) where prime_bit[p] is the SAT var whose
    truth means f(p) = -1.
    """
    spf = _smallest_prime_factor(N)
    pool = IDPool()
    cnf = CNF()

    # sign bits sb_n for n in [1..N]
    sb = {n: pool.id(("sb", n)) for n in range(1, N + 1)}

    # sb_1 = 0 (f(1)=+1)
    cnf.append([-sb[1]])

    prime_bit = {}
    for n in range(2, N + 1):
        p = spf[n]
        if p == n:  # prime: free variable
            prime_bit[p] = sb[n]
        else:       # composite: sb_n = sb_p XOR sb_{n/p}
            a, b, c = sb[n], sb[p], sb[n // p]
            # a <-> b XOR c
            cnf.append([-a, -b, -c])
            cnf.append([-a, b, c])
            cnf.append([a, -b, c])
            cnf.append([a, b, -c])

    # prefix-sum automaton. states v in [-D..D]; index by offset v+D in [0..2D].
    def q(k, v):
        return pool.id(("q", k, v))

    # layer 0: S_0 = 0
    cnf.append([q(0, 0)])
    for v in range(-D, D + 1):
        if v != 0:
            cnf.append([-q(0, v)])

    for k in range(1, N + 1):
        # exactly-one state at layer k
        lits = [q(k, v) for v in range(-D, D + 1)]
        cnf.append(lits[:])  # at-least-one
        for i in range(len(lits)):
            for j in range(i + 1, len(lits)):
                cnf.append([-lits[i], -lits[j]])  # at-most-one
        # transitions from layer k-1
        for v in range(-D, D + 1):
            # +1 step (sb_k = 0)
            up = [-q(k - 1, v), sb[k]]
            if v + 1 <= D:
                up.append(q(k, v + 1))
            cnf.append(up)  # if v+1>D: (¬q_{k-1,v} ∨ sb_k) forbids overflow
            # -1 step (sb_k = 1)
            dn = [-q(k - 1, v), -sb[k]]
            if v - 1 >= -D:
                dn.append(q(k, v - 1))
            cnf.append(dn)

    return cnf, pool, prime_bit


def exists_cm_bounded(N: int, D: int):
    """(result, prime_signs). result in {'SAT','UNSAT'}. On SAT, prime_signs is
    {p: ±1} already re-verified by the real discrepancy checker."""
    cnf, pool, prime_bit = build_cnf(N, D)
    with Cadical153(bootstrap_with=cnf.clauses) as solver:
        if not solver.solve():
            return "UNSAT", None
        model = set(solver.get_model())
        prime_signs = {p: (-1 if prime_bit[p] in model else 1) for p in prime_bit}
        # CONTRACT: independent verification with the real simulator.
        f = build_cm(prime_signs, N)
        disc = discrepancy_via_prefix(f, N)
        assert disc <= D, (
            f"SAT model claims disc<= {D} on [1..{N}] but real checker says "
            f"disc={disc} — ENCODING BUG."
        )
        return "SAT", prime_signs


def find_C_CM(D: int, lo: int = 1, hi: int = 512, verbose: bool = True):
    """Largest N with a CM sequence of discrepancy <= D, by exponential search
    then binary search. Assumes monotonic: if length N is UNSAT, so is N+1
    (a bounded prefix on [1..N+1] restricts to one on [1..N]).

    Returns (C_CM, witness_prime_signs_at_C_CM).
    """
    # exponential growth until UNSAT
    last_sat, last_signs = None, None
    n = lo
    while True:
        res, signs = exists_cm_bounded(n, D)
        if verbose:
            print(f"  D={D} N={n}: {res}", flush=True)
        if res == "SAT":
            last_sat, last_signs = n, signs
            if n >= hi:
                if verbose:
                    print(f"  hit hi={hi} still SAT — raise hi")
                return n, signs
            n = min(n * 2, hi) if n * 2 > n else n + 1
        else:
            break
    # binary search between last_sat and first UNSAT (n)
    lo_s, hi_u = last_sat, n
    while hi_u - lo_s > 1:
        mid = (lo_s + hi_u) // 2
        res, signs = exists_cm_bounded(mid, D)
        if verbose:
            print(f"  D={D} N={mid}: {res}  [bisect {lo_s}..{hi_u}]", flush=True)
        if res == "SAT":
            lo_s, last_signs = mid, signs
        else:
            hi_u = mid
    return lo_s, last_signs


if __name__ == "__main__":
    print("CM discrepancy SAT — self-test on D=1 (known C_CM(1)=9)")
    c, signs = find_C_CM(1, hi=64)
    print(f"  => C_CM(1) = {c}  (known: 9)")
