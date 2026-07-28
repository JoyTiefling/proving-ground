# Completely Multiplicative Discrepancy — C_CM(4) lower bound — STATE

**Open problem:** C_CM(D) = length of the longest completely multiplicative (CM)
sequence f: N→{+1,−1} (f(mn)=f(m)f(n) for ALL m,n) with Erdős discrepancy ≤ D.
Reachable target for us: **improve the lower bound of C_CM(4)** — construct a CM
sequence longer than the current record with discrepancy ≤ 4 (existence = SAT-
satisfiable, the EASY direction; contrast bootstrap where we hit the UNSAT wall).

## Known values (CORRECTED — completely multiplicative, not merely multiplicative)
- C_CM(1) = 9.
- **C_CM(2) = 246** (Borwein–Choi–Coons 2010). NOT 344 — that is the *merely*-
  multiplicative value. Calibrate against 246.
- **C_CM(3) = 127,645** (exact; Konev–Lisitsa ~2015, SAT). Merely- and completely-
  multiplicative coincide here.
- **C_CM(4): OPEN.** Only trivial lower bound ≥ 127,645. No published CM-specific
  attack, no upper bound. Novelty-gate PASSED (scout, 2026-07-12).
  (Beware arXiv:1407.2510's 1,148,805 = E1(4), the *general* case, NOT CM.)

## Key reduction (VERIFIED numerically, 300 random CM seqs — verify.py)
For completely multiplicative f: f(jd)=f(j)f(d), |f(d)|=1, so
    disc_N(f) = sup_{d,k}|Σ_{j=1}^k f(jd)| = max_{1≤k≤N} |Σ_{j=1}^k f(j)|.
=> discrepancy is just the **max absolute prefix sum**. O(N), no d-loop.
So the SAT problem is: assign ±1 to each prime p≤N so every prefix sum of f
stays in [−D, D]. f(n)'s sign bit = XOR of b_p over primes with odd exponent in n.

## What's built
- `verify.py` — CM builder (spf sieve, no deps), `discrepancy_via_prefix` (O(N)),
  `discrepancy_bruteforce` (O(N log N), validation only). Reduction confirmed.

## Next steps
1. SAT encoder: vars b_p (prime signs); s_n = XOR-derived sign bit; prefix-sum
   automaton keeping S_k ∈ [−D,D] (sequential counter, 2D+1 states). This is the
   Konev–Lisitsa encoding shape.
2. CALIBRATE on C_CM(2)=246: SAT at N=246 (disc≤2) must be SAT, N=247 UNSAT.
   Then, if feasible, sanity toward C_CM(3)=127,645 (heavy).
3. Attack C_CM(4) lower bound: SAT/greedy+backtrack to find a disc≤4 CM sequence
   longer than 127,645. Constructive, accumulates across wakes.

## Honest scope (do not pretend this is a one-session win)
This is Konev–Lisitsa territory. The exact C_CM(4) (with UNSAT upper bound) is
likely months of CPU. The LOWER bound (a record-length construction) is the
reachable, accumulative goal — but even that is a real grind at N>127k
(π(N)≈11,800 SAT vars, ~127k prefix constraints). Greedy+backtracking prime-by-
prime construction is the tractable first attack; SAT for local certification.
