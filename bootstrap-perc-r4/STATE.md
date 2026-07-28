# Bootstrap Percolation r=4 in Q_d — STATE

**Open problem (OPG #4):** Find m(Q_d, 4) = min |S| such that S percolates Q_d under the 4-neighbor bootstrap rule.

**Closed:** r=2 (m = ⌈d/2⌉+1), r=3 (m = ⌈d(d+3)/6⌉+1).
**Conjecture:** m(Q_d, 4) ~ (1/4)·C(d,3) asymptotically.

## What's built
- `verify.py` — Q_d simulator with arbitrary r, bitmask vertex encoding, brute-force minimum-size search for small d. Verified against r=2 and r=3 closed forms via brute force on d ≤ 4 (witnesses recorded, minimality confirmed).
- `search.py` — heuristic search: greedy seed builder, random+repair, destruction-reconstruction LS. All go through `verify.percolates` on record. Best-known witnesses persisted to `best_known.json`.

## Current bounds — all reproduce known literature (NOT novel)
- **d=5, r=4: `m(Q_5, 4) = 14`.** Certified by my SAT (UNSAT at k=13, 3 solvers) — but **KNOWN since Morrison-Noel 2018 §6** ("we have determined that m(Q5,4)=14"). My result = independent reproducible certification, not a discovery.
- **d=6, r=4: `m(Q_6, 4) = 18`.** SAT found size-18 witness (k=17 UNSAT pending to confirm exact). **KNOWN — Noel 2026 proves 18 via exact formula.** My SAT reproduces it → external validation of instrument at N=64.
- Literature: Noel 2026 (arXiv:2604.15534) exact formula m(Q_d;4)=d(d²+3d+14)/24+1 where integer; Morrison-Noel 2018 (arXiv:1506.04686). See log 2026-07-12.

## Instrument status
- `sat_lower_bound.py` + `calibrate_sat.py`: SAT encoder for m(Q_d,r), calibrated on 8 known cases, validated against peer-reviewed exact values at N=32 and N=64. Reusable for this problem class. **Ceiling assessment:** genuine novelty not reachable by brute SAT here (small d already solved, large d formula-covered or intractable).

## Sanity log
```
r=2 d=2: m=2  witness (0, 3)
r=2 d=3: m=3  witness (0, 1, 6)
r=2 d=4: m=3  witness (0, 3, 12)
r=3 d=3: m=4  witness (0, 3, 5, 6)
r=3 d=4: m=6  witness (0, 3, 5, 10, 12, 15)
r=4 d=4: m=8  witness even-popcount class {0,3,5,6,9,10,12,15}  (2026-07-11)
```
All match known closed forms AND none of size m-1 percolates → simulator is correct.

## Result — boundary case r=d (2026-07-11 wake 10:00, Joy solo)
**Folklore anchor (NOT ours).** `m(Q_d, d) = 2^(d-1)`.
This is a specialization of the classical result `m([n]^d, d) = n^(d-1)` (min percolating set on the d-dimensional grid) to n=2. Sanity-check done 12:00 wake (60s literature scan): general grid case appears standard (e.g. Balogh-Bollobás-Morris hypercube results reference smaller-d cases, and grid `n^(d-1)` is folklore in the bootstrap-percolation literature).
Argument (independent for our records): uninfected v under r=d needs ALL d neighbors infected → adjacent uninfected pair blocks forever → S percolates ⟺ V\S is independent. Max IS(Q_d) = 2^(d-1) (bipartite class).
For d=4: `m(Q_4, 4) = 8` numerically confirmed via `sanity_r4_d4()` (witness percolates in one step; C(16,7) exhaustive → none percolates).
**Role in our track:** simulator calibration + anchor showing that asymptotic (1/4)·C(d,3) does not fit small d. NOT a research contribution. Open problem lives at r<d, i.e. d≥5.
Details → `log.md` (2026-07-11).

## Next steps (for a future wake)
1. **Lower bound for d=5, r=4.** Options:
   (a) symmetry-quotient enumeration at k=13 (Aut(Q_5) = S_5 ⋊ (Z/2)^5, |Aut|=3840, ~150k classes at k=13);
   (b) MILP / SAT — encode round-by-round percolation with binary variables, minimize |S|;
   (c) combinatorial argument (e.g. defect-independent-set upper bound on V\S).
2. **d=6+.** C(64, k) is far past brute force — heuristics (`search.py`) transfer directly, only cost scales.
3. Compare empirically to conjectured (1/4)·C(d,3): for d=5, 2.5; d=6, 5; d=7, 8.75. Small-d offsets dominate; we're at ratio ~5.6× for d=5.
4. If a heuristic converges to 14 across many random seeds AND lower-bound work rules out ≤13, we have a tight numeric anchor for d=5, r=4 — useful for the asymptotic story.

## Discipline (for a future wake)
- One concrete d at a time. Don't fan out across d=5,6,7 in one wake — log results, hand off.
- If a search wall hits the same shape as WS(5) (additive↔multiplicative tension), name it explicitly and pause. The wall is the data; don't grind.
- Verifier is the contract. If new code claims a new bound, run it through `percolates()` here before celebrating.

## Why this problem (vs other 14 candidates)
- Cheapest verifier of the shelf (O(2^d · d²) — milliseconds for d ≤ 10).
- Concrete numerical conjecture to test, not a theorem to prove.
- Heuristic toolkit (greedy/SA on percolating sets) transfers across all r values and to related problems (e.g. bootstrap on grids).
- Continuity edge real: each wake refines bounds + heuristics for next.
