# CM discrepancy C_CM(4) — journal

Task shelf → `projects/frontier/problems/scout-arxiv.md` #3.
Pivot from bootstrap-perc-r4 (closed: no reachable novelty). Verifier: `verify.py`.

## 2026-07-12, session with Sanya — onboarding + instrument calibrated

**Pivot rationale.** Bootstrap r=4 verified-closed for novelty (open frontier
d≥17, N≥131072, beyond brute SAT). Chose CM discrepancy D=4 because the reachable
target is a LOWER bound — "does a length-N CM sequence with disc≤D exist?" =
SAT-satisfiability, the EASY direction (contrast bootstrap's UNSAT wall).

**Novelty gate (scout) PASSED.** No published CM-specific attack on D=4; only the
trivial C_CM(4) ≥ C_CM(3) = 127645. Upper bound fully open. Also corrected the
calibration target: C_CM(2) = **246** (completely multiplicative; Borwein-Choi-
Coons 2010), NOT 344 (that's merely-multiplicative). C_CM(1)=9, C_CM(3)=127645.

**Reduction (verify.py) confirmed numerically (300 random CM seqs).** For CM f,
disc = max |prefix sum|; the d-loop collapses because f(jd)=f(j)f(d). SAT problem
= keep prefix sums in [-D,D].

**SAT encoder built (`cm_sat.py`).** Prime-sign vars b_p; sign bits sb_n = XOR
chain over spf factorization; prefix-sum automaton (one-hot states v∈[-D..D],
transition + exactly-one + overflow-forbidding). Contract: every SAT model's
prime signs are re-checked by the real `discrepancy_via_prefix` (assert).

**CALIBRATION — instrument trusted only after this:**
- C_CM(1) = 9: SAT at 9, UNSAT at 10. ✓ (matches known)
- C_CM(2) = 246: SAT at 246, UNSAT at 247, found in 0.2s. ✓ (matches corrected
  known value — validates the encoding on a real Borwein-Choi-Coons number)
Two known endpoints reproduced exactly ⇒ automaton + XOR sign bits + boundary
all correct. D=3,4 reuse the same D-parametric code.

## Next
- Scaling probe (running): D=4 SAT build+solve time at N=1k,5k,20k,60k — is
  reaching/exceeding N=127645 feasible with vanilla CaDiCaL?
- If feasible: SAT at N=127646 with D=4 → if SAT, C_CM(4) ≥ 127646 (first
  improvement past trivial). Then push N up to map how far D=4 reaches.
- If the naive automaton doesn't scale: greedy+backtracking prime-by-prime
  constructor (lower bound only, but scales), or incremental SAT.

## Honest scope
Konev-Lisitsa territory. Exact C_CM(4) likely months of CPU (UNSAT upper bound).
Reachable = lower-bound record via construction. Even that is a real grind at
N>127k (π(N)≈11800 prime vars, ~N·9 state vars). Multi-session.

## 2026-07-12 — PARKED. Compute-wall, not novelty-wall. (Sanya: stop for today)

Scaling probe (D=4 SAT, clean, no competition):
```
N=1000: build 0.1s  solve 0.2s   (58k clauses)
N=5000: build 0.3s  solve 13.6s  (292k clauses)
```
Diagnosis corrected by DATA (I had guessed "build is the bottleneck" — wrong):
the SOLVE is the wall. 0.2s→13.6s for N ×5 ⇒ empirical exponent ≈2.6. Extrapolated
to target N≈127646: hours-to-tens-of-hours per single solve, and SAT solve time on
satisfiable instances is erratic/unpredictable. Monolithic one-hot SAT does NOT
reach the target on our hardware.

**Verdict: this problem hits our hardware compute wall** (verifier is O(N) cheap,
but the reachable target's SEARCH is not). Per Sanya's repeated calibration
(12-07), such problems should not be taken — filter at SELECTION via an early
cost-curve probe, not after investing. Frontier criteria updated
(`projects/frontier/problems/README.md` #4).

**What's banked (reusable, correct):** verify.py (CM builder + O(N) discrepancy,
reduction proven), cm_sat.py (SAT encoder, calibrated exact on C_CM(1)=9 and
C_CM(2)=246). If ever revisited: (a) greedy+backtracking prime-by-prime
constructor (lower bound only, scales far past SAT), or (b) order-encode the
prefix-sum counter (one-hot is likely why solve is slow) — but only if the target
becomes hardware-reachable. Not a priority; parked.
