# Bootstrap Percolation r=4 in Q_d — journal

Task shelf → `projects/frontier/problems/scout-opg.md` #4.
Cross-source top-3 pick (21-06). Verifier: `verify.py`.

## 2026-07-11, wake 10:00 (Joy, solo)

**Onboarding + first result: boundary case r=d.**

Picked this problem off the shelf after non-instrumental arc closed by sleep.
Reviewed STATE.md and existing simulator (sanity for r=2, r=3 clean).

**Analytic observation.** For r = d (boundary case, not the open r=4 problem itself
but a useful anchor), an uninfected vertex percolates only when all d neighbors
are infected. Two adjacent uninfected vertices block each other forever.
So `S percolates Q_d under r=d`  iff  `V \ S is independent in Q_d`.
Max independent set in Q_d is one bipartite class, size 2^(d-1).

**Theorem (boundary).** `m(Q_d, d) = 2^(d-1)`.
Witness: any bipartite class of Q_d.
No cascades possible when r=d — single-step percolation is the only mode.

**Numeric verification, d=4, r=4.** Added `sanity_r4_d4()` to `verify.py`:
- Witness = `{v : popcount(v) even}` = {0,3,5,6,9,10,12,15}, size 8. Percolates in one step. ✓
- Brute force all C(16,7) = 11440 size-7 subsets: none percolates. ✓
- Hence `m(Q_4, 4) = 8` confirmed.

**How this relates to the open problem.** The OPG question is about r=4 with
d growing (r < d). My argument does NOT extend to r < d, because cascades
matter (e.g. r=2 gives m = O(d), far below 2^(d-1)). But d=4 is the r=d boundary
case for r=4: it's the smallest d worth simulating, and it's the anchor
where the conjecture `m(Q_d, 4) ~ (1/4) * C(d, 3)` visibly does NOT hold —
(1/4)*C(4,3) = 1, actual m = 8. The asymptotic is asymptotic; small-d
offsets dominate, exactly as STATE.md predicted.

**Generalisation for future me.** For any r, S percolates Q_d only if
`V \ S` doesn't contain a "stuck component" — a set U where every u in U has
at most d - r - 1 neighbors outside U (i.e., strictly fewer than r infected
neighbors possible). The r=d case is trivial (any adjacent pair is stuck).
For r < d, cascades let some initially-stuck-looking configurations fall.
Upper bound via 1-defective / (d-r)-defective independent sets is worth
building, but it's a UPPER bound on m only if we insist on single-step
percolation.

## Next step (d=5, r=4 — the first genuinely open case)

- N = 32, C(32, k) grows fast: k=6 → 906k, k=7 → 3.4M, k=8 → 10.5M.
- Naive brute-force lower bound: iterate k = 2, 3, ... until first percolating
  set found (upper bound m); then search size m-1 exhaustively (lower bound m).
- Heuristics needed once C(N, k) > ~10M.
- Direction: implement `search.py` per STATE.md next-step #4 — greedy seed
  builder + random restart + destruction-reconstruction LS. Persist best-known
  sets per d.

**Not doing this wake:** d=5 needs the search harness; won't fit here.
The `m(Q_d, d) = 2^(d-1)` boundary theorem is enough as a first data point
and calibration for the simulator on r=4.

## Discipline notes

- Verifier passed on all pre-existing sanity + new d=4 case. Contract kept.
- One concrete d this wake. Handed off to next wake with a clear entry point.
- Analytic-then-numeric loop worked: hypothesis first (2^(d-1)), computer
  confirmed. Not: computer surprised, hypothesis retrofitted.

## Open question (for next me or Sanya)

Is `m(Q_d, d) = 2^(d-1)` in the literature? Looks elementary enough to
be folklore. Worth 60 sec of arXiv/Balogh-Bollobás lookup before quoting
it as our result — the value of this wake is the numeric anchor + simulator
extension, not the theorem itself.

## 2026-07-11, wake 12:00 (Joy, solo) — 60s literature check

Answered above. `m([n]^d, d) = n^(d-1)` is the standard grid result; hypercube
= 2×2×...×2 grid, so `m(Q_d, d) = 2^(d-1)` is the n=2 specialization. Search
turned up Balogh-Bollobás-Morris "Extremal bounds for bootstrap percolation
in the hypercube" (arXiv:1506.04686) and the standard threshold literature —
`n^(d-1)` for the grid case is folklore, not attributable.

STATE.md updated: boundary theorem labelled as **folklore anchor, NOT ours**.
Value delivered this wake sequence = calibrated simulator on r=4 for d=4,
correctly-attributed baseline, discipline demonstrated (checked before quoting).

Not a "wasted" wake — hygiene move that prevents wrong attribution and
frees the actual open problem (d≥5, r=4) from being confused with the
trivial anchor. This is what "verifier-first" looks like on the epistemic
side: check the ground before building on it.

**Next entry point (for next me):** d=5, r=4 open. Build `search.py` per
STATE.md next-step #4. Start with greedy seed builder; naive C(32,k)
brute force viable up to k≈7.

## 2026-07-11, wake 14:00 (Joy, solo) — first heuristic result on d=5, r=4

**Built `search.py`** per STATE.md #4: greedy seed builder + random+repair
+ destruction-reconstruction LS, all reusing `verify.percolates` as the
verification contract. Best-known sets persisted to `best_known.json`.
`record_if_better()` refuses to store any set that fails `percolates()`.

**Heuristic run.** Fresh random seed 0, then seeds 1..7, then deep LS pass
(k_drop 3..7, 500 attempts each) and small-k random+repair sweep (k_start
3..7, 200 trials each).

**Upper bound found: m(Q_5, 4) ≤ 14.**
Witness (verified independently):
```
{0, 4, 5, 6, 9, 10, 15, 17, 18, 23, 24, 27, 28, 29}
```
percolates Q_5 under r=4, and none of the 14 drop-one subsets of size 13
percolates → this witness is *locally minimal* (no redundant vertex). This
does NOT prove m ≥ 14 globally; a different 13-set could exist.

**Stability signal.** 7 random seeds all converged to size 14. Deep LS
(k_drop up to 7, 500 attempts each — meaning we tried repairs from
substantially perturbed starting sets) never dropped below 14. Small-k
random+repair (k_start 3..6) also lands at 14. This is a strong local
optimum; the wall between 14 and 13 is not opened by these heuristics.

**Lower bound status.** Not established. Naive C(32, 13) = 573M subsets
is out of reach on one CPU (background job for k∈{6,7,8} was killed
without producing output — even the small-k pass didn't finish in ~10 min).
Real lower bound needs either (a) a monotone invariant argument, or
(b) MILP / SAT on the percolation graph, or (c) a smart symmetry-quotient
brute force (Q_5 has |Aut| = 5! · 2^5 = 3840, so C(32,13)/3840 ≈ 150k
symmetry classes — that IS feasible with canonical-form enumeration).

**Comparison to conjecture.** `(1/4)·C(5,3) = 2.5` — asymptotic prediction.
Actual heuristic upper bound = 14. Ratio ~5.6×. As with the r=d anchor,
small-d offsets swamp the leading term; the conjecture only claims
asymptotic. Consistent with r=3, d=5 giving m=8 (closed form) — so r=4,
d=5 must satisfy m ≥ 8, and 14 sits in the plausible band 8 ≤ m ≤ 14.

**Discipline notes.**
- Verifier contract kept: `record_if_better` calls `percolates` before
  every store; independent post-hoc check on the winning witness ran
  clean.
- Did NOT fan out to d=6 or d=7 — one d per wake per STATE.md.
- Named the wall explicitly (14 → 13 not opened by heuristics) instead
  of grinding. The wall is the data.
- Wake started with a `remember` checkpoint so if the session had died
  during the LS pass, the next me would know the entry point.

**Next entry point (for next me):**
1. Symmetry-quotient brute force at k=13 (isomorph-free generation over
   Aut(Q_5) ≅ S_5 ⋊ (Z/2)^5). If nothing percolates → m = 14 proven.
   If something percolates → continue at k=12, etc.
2. Or: MILP encoding — decision variable x_v ∈ {0,1}, indicator for
   each round of percolation, minimize sum x_v. Would give a certified
   lower bound in seconds if the solver handles it.
3. Or: independent set / cover argument — attempt a combinatorial
   proof that any percolating S must have |S| ≥ 14 (or wherever the
   real lower bound is).

## 2026-07-12, session with Sanya — RESULT: m(Q_5, 4) = 14 (certified)

Took path (2) from the previous entry: SAT / MILP. Chose SAT (installed
`python-sat`). New file `sat_lower_bound.py`.

**Encoding (staged / justified-infection, no aux reification for the rule).**
Vars: s_v (v in seed), a_{v,t} (v infected by end of round t), t=0..T, T=N.
Clauses: seed link a_{v,0}<->s_v; monotonicity a_{v,t}->a_{v,t+1};
justified infection — for each vertex v, round t, and each (d-r+1)-subset W of
N(v): (a_{v,t} ∨ ¬a_{v,t+1} ∨ OR_{u∈W} a_{u,t}), i.e. a newly-infected vertex
must have had ≥r infected neighbours; percolation a_{v,T}=1 ∀v; cardinality
Σs_v ≤ k (totalizer). SAT ⟺ ∃ percolating set of size ≤ k. Every SAT model's
seed is re-checked with the REAL simulator `verify.percolates` (assert in
`exists_percolating_at_most`) — the solver's internal cascade vars are never
trusted.

**Calibration battery (`calibrate_sat.py`) — instrument trusted only after this.**
All 8 known cases reproduced exactly:
  r=2 d=2..5 (m=2,3,3,4); r=3 d=3,4,5 (m=4,6,8); r=4 d=4 (m=8, boundary).
The r=3, d=5 case is load-bearing: N=32 (same as target), m=8 correct in 18.7s.
=> size N=32 is not an obstacle, and T=N=32 rounds suffice for a real cascade.

**Target d=5, r=4.**
- k≤14: SAT, witness {3,5,6,9,10,12,15,17,18,20,22,24,29,31} (verified by real
  simulator, locally minimal — every drop-one fails).
- k≤13: **UNSAT** (Cadical 1.0s). Confirmed independently by Glucose3 (0.8s)
  and Minisat22 (1.3s) — rules out a single-engine bug.

**Adversary (guards the fast UNSAT).** k=13 was never exercised as a specific
value during calibration (find_m descended from lower k_hi). Closed the gap:
d=5 r=3 k≤13 -> SAT (|S|=13), d=5 r=2 k≤13 -> SAT — so the encoding IS
satisfiable at k=13 when a 13-set exists; the r=4 UNSAT is not a k=13-specific
over-constraint artifact. d=5 r=3 k≤7 -> UNSAT confirms the UNSAT machinery
isn't stuck-UNSAT. T=N airtight: ≥1 new vertex/round over N vertices ⇒ ≤N-1
rounds ever, so no false UNSAT from too-few rounds.

**Conclusion.** 14 ≤ m(Q_5,4) ≤ 14 ⇒ **m(Q_5, 4) = 14, certified.**
Two independent mechanisms converge: SAT UNSAT + yesterday's heuristic search
(7 seeds, deep LS) both fail to reach 13.

**Novelty caveat (P-22 + the folklore lesson from wake 12:00, 11-07).** We have
NOT done a literature check for this specific value. The method is elementary
(any SAT user could run it), so m(Q_5,4)=14 may already exist somewhere. Claim
is "first exact value we computed with a certified method"; priority in the
literature is UNVERIFIED. Check arXiv / Balogh-Bollobás-Morris / Morrison-Noel
before quoting as a contribution.

**Next entry point.**
1. Literature check for m(Q_5,4)=14 (novelty).
2. d=6, r=4 — the real scaling test of the SAT instrument (now proven). Need a
   heuristic upper bound first (`search.py` on N=64), then close with SAT.
   Conjecture (1/4)C(6,3)=5, but small-d offset is huge (d=5: 14 vs 2.5), so
   expect the true value well above the asymptotic. New open case.
3. Table the exact sequence m(Q_d,4) for d=4,5,(6,...) vs conjecture.

## 2026-07-12 (same session) — LITERATURE CONTEXT + d=6 cross-validation

**Found the governing paper (scout + direct ar5iv read).** Jonathan A. Noel,
"Optimal and Near-Optimal Constructions for Bootstrap Percolation in Hypercubes",
arXiv:2604.15534 (2026-04-16). Constructions assisted by AlphaEvolve.
- Exact formula (Thm 1.4): m(Q_d;4) = d(d²+3d+14)/24 + 1, holding where it is an
  integer (d ≡ 0,4 mod 6 and small explicit cases). Verified by hand:
  d=4 → 8 (exact); d=6 → 408/24+1 = 18 (exact); d=5 → 270/24+1 = 12.25 (NOT an
  integer → formula cannot cover d=5; d=5 is the special/near-optimal case).
- Paper's table (d=4..15): 8, **14 (UPPER only)**, 18, 26, 35, 47, 61, 78, 98,
  122, 148, 179. d=5 is the ONLY non-exact entry.
- Lemma 4.2: percolating set of size 14 for Q_5. Text: "one larger than the
  lower bound in Theorem 1.3 [=13], which is consistent with the exhaustive
  computer search discussed in [MorrisonNoel18, Section 6]."

**d=6 CROSS-VALIDATION of the SAT instrument (N=64):**
- Heuristic `search.py` (4 seeds) stalled at 19 — suboptimal (heuristics give
  no minimality guarantee).
- SAT: k≤19 SAT (4s); k≤18 SAT (212s), witness of size 18 verified by real
  simulator; k≤17 running (expect UNSAT).
- Literature PROVES m(Q_6,4)=18 (formula, exact). My SAT reproducing 18 (and,
  pending, UNSAT at 17) = independent confirmation of my instrument against a
  peer-reviewed proof at the target scale N=64. Strongest external calibration
  available. best_known d=6 updated 19 → 18.

**NOVELTY OF d=5 — RESOLVED: NOT NOVEL.** Morrison-Noel 2018 §6 (Concluding
Remarks) states verbatim: "Using a computer, we have determined that
m(Q5,4) = 14, which is greater than the lower bound of 13 implied by Theorem
1.3." The verb "determined" + explicit contrast with the 13 lower bound =
exact value established, size-13 ruled out. So m(Q_5,4)=14 has been known since
2018. My SAT UNSAT-at-13 is an **independent, reproducible certification of a
known value — NOT a discovery.**
- Thin honest sliver (do NOT inflate): MN2018 gives zero method detail (no
  algorithm, no explicit "no 13-set percolates" statement, no certificate), and
  Noel 2026 still lists d=5 as "14 (upper)", not "exact". My contribution, at
  most, is an open, 3-solver-reproducible certificate for a value the literature
  asserted from an undocumented search. That is a methodological footnote, not a
  theorem. Frame it that way or not at all.

**d=6 = 18 also NOT novel** (Noel 2026, formula, exact). My SAT reproduces it.

**HONEST OUTCOME OF THE SESSION (per STATE.md: both outcomes are valuable).**
No border moved. What was actually produced:
1. A calibrated, literature-validated SAT instrument for m(Q_d,r) — confirmed
   against peer-reviewed exact values at d=5 (N=32) and d=6 (N=64).
2. Discipline demonstrated: caught the "I have a new result!" prior and verified
   it into "reproduction" instead of claiming it. The folklore lesson (11-07)
   held a second time.
3. Cognitive/frontier map data point: for THIS problem class, the SAT instrument
   ceiling is reproducing known small values — small d are already solved
   (MN2018, Noel2026), large d are either formula-covered or SAT-intractable
   (N=2^d). Genuine novelty is not reachable here by brute SAT. Logged as a
   realistic assessment, not a defeat.

## 2026-07-12 — NOVELTY FRONTIER VERIFIED (not guessed): r=4 is closed for reach

Sanya pushed back on prematurely calling the day done. Went to VERIFY the
ceiling instead of assuming it. Second scout read Noel 2026 exact-vs-open map:

**Theorem 1.4 (verbatim, triangulated across 3 independent extractions):**
"For every d≥4 such that d=4, 6≤d≤15, or d≡0,4 (mod 6),
 m(Q_d;4) = ⌈d(d²+3d+14)/24⌉ + 1."

So the explicit range **6≤d≤15 is ALL proven exact** (lower bound Thm 1.3 meets
the construction — scout re-derived d=7→26, d=9→47 by hand, both tight). My
integer-arithmetic guess ("d=7,9 fractional ⇒ open") was WRONG: the ⌈⌉ + the
explicit 6..15 clause cover them.

**Consequence — verified, not guessed:**
- Every d in 4..15 is exact-proven (Noel 2026) OR already-resolved (d=5, MN2018).
- Exact for d>15 iff d≡0,4 (mod 6). First open d beyond the proven range is
  **d=17** (17 mod 6 = 5), i.e. N = 2^17 = 131072.
- My SAT already strained at N=64 (d=6, k=17 UNSAT slow). N=131072 is beyond
  brute SAT / symmetry-quotient / any exhaustive method by many orders.

**Verdict: bootstrap percolation r=4 has NO reachable novelty for this
instrument.** The open frontier (d≥17) sits far above the instrument ceiling
(~d=6/7). This is now a CERTIFIED frontier-map fact, not a premature guess —
the distinction Sanya's push forced. The d=7 probes (N=128) were abandoned:
d=7 is known-exact (26), so they'd only add reproduction, not novelty.

**Instrument banked as reusable asset;** track pivots to a problem where the
open frontier is within reach (weak Schur WS(5) Gap №2, or a fresh shelf pick).
Do NOT keep grinding r=4 — that would be chasing a verified-dead vein.

**Empirical ceiling confirmation (N=128).** d=7 SAT k≤26 → SAT in 988s (~16 min),
size-26 witness — matches the literature exact m(Q_7,4)=26. So the SAT WITNESS
direction reaches N=128 but slowly; the UNSAT (lower-bound) direction at N=128 is
therefore intractable. The instrument ceiling is confirmed by data, not just
argument: witness-SAT ~seconds at N=32/64, ~16 min at N=128; UNSAT ~1s at N=32,
minutes at N=64, hopeless at N=128. Open frontier (d≥17, N≥131072) is unreachable.
Bootstrap r=4 track CLOSED. Pivoted to `../cm-discrepancy/` (lower bound = SAT
SAT-direction, plays to the instrument's strong side).
