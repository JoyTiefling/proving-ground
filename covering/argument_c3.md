# The 2-pair cover claim at c=3, written out by hand — head of the argument

Status: **PARTIAL.** The shared prefix, the branch structure, one typical leaf
(§3) and the single exceptional leaf (§4) are written below, together with what
the cover blocks do across the whole tree (§4.1). The remaining 74 leaves are
not. This file is the second instalment of "write the 76 cases out in prose",
not its completion.

Source of every number and every step quoted here:
`search/case_tree_witnesses.py` (wake 20:00, 02-08-2026), payload
`search/out/w76.json`. Gates on that payload at time of writing:
`G1_matches_prior=True` against the 18:00 receipt `sha16=7f094ff660e8b2a3`,
`W1 76/76`, `W2 60/60`, `W3 disjoint`, `M1–M4` all red. `all_gates_pass=True`.

**Carry the caveat with the numbers.** Both the MUS (92 triples) and the width
(76 leaves) are conditional on what I put in the *hard* part of the encoding —
the `7=2` anchor and the rigid assignments. Those were themselves obtained by
SAT, and their cost is not inside these numbers. The honest form of any claim
below is the pair *(magnitude, what was held fixed)*, never the magnitude alone.

---

## 0. What is being argued

Instance: `N=90`, `k=5` colours, cover parameter `c=3`. The MUS over the cover
claim is 92 triples; the case tree over that core has **76 conflict leaves**,
**depth 6**, and branches on **seven roots**: `9, 11, 15, 17, 19, 21, 25`.

Every leaf closes **by unit propagation alone**. That is the falsifiable claim,
and it is the reason the derivations below exist at all. The weaker-sounding
alternative — "assert the path into the CNF, the solver says UNSAT" — is true of
*every* path, including invented ones, because the instance is UNSAT as a whole.
A check that cannot fail certifies nothing. So each step below names the clause
it uses and the pinned roots that make that clause fire; a reader validates a
step without re-running any search.

Two clause families appear, and each of them can either prune or kill:

- **prune** — clause `C` with all-but-one of its roots already pinned to colour
  `x` removes `x` from the domain of the remaining root;
- **conflict** — a clause all of whose roots are pinned to one colour. This is
  where a case dies.

The families are the **92 forbidden triples** of the MUS core, and the **two
cover blocks** `¬(11=3 ∧ 17=3)`, `¬(35=3 ∧ 55=3)` — the negation of the claim
being argued. The blocks are binary and live on colour 3 only, but they are
otherwise ordinary clauses in the derivation, not a goal sitting outside it.

Across all 76 cases the step ledger is:

| kind | count |
|------|-------|
| `mono_prune` (triple prunes) | 2347 |
| `pair_prune` (block prunes) | 49 |
| `pin` (case splits) | 368 |
| `mono_conflict` (dies on a monochromatic triple) | 75 |
| `pair_conflict` (dies on a cover block) | 1 |
| **total, case-by-case** | **2840** |

With shared prefixes written once it is **1116 distinct steps**. 1116 — not 76,
and not 92 — is the number that decides whether this is writable by hand. (Three
different magnitudes for one question, each of which I announced in turn as the
answer; the one that decides is the one a floor below.)

**"Distinct" needs its definition attached, because there are two and they
differ by a factor of four.** Under prefix-tree compression — a step is written
once if every case reaching it has followed the same derivation to that point —
the count is **1116**. Under step *signature* — the same clause firing on the
same root to remove the same colour, counted once no matter where in the tree —
it is **289**. The writable-by-hand number is 1116, and the reason is the
reader, not the tree: someone following case 40 cannot reuse a prune written out
under case 12's prefix, because reaching it requires case 12's pins. 289 is what
the argument costs a machine that can hash; 1116 is what it costs a reader. The
figure was published in the first instalment without this definition and is not
recorded in the receipt at all — it was computed by hand at the time of writing
and has now been recomputed from the payload and reproduced exactly. Same shape
of question as the 92-vs-76-vs-1116 series above, one level in again.

*Correction to the first instalment of this file.* It stated the vocabulary as
two kinds and gave the ledger as `2347 + 368 + 75 + 1`, which is 2791, against a
total of 2840 quoted in the same sentence. The missing 49 are `pair_prune`, a
kind I did not know existed: I read the step vocabulary off the one leaf I had
worked in full (§3), and that leaf happens to contain no block step at all. The
totals were quoted from the payload and the components from my sample, so the
sum was never made to close. It closes now — 2347+49+368+75+1 = 2840 — and the
arithmetic is the check.

---

## 1. The shared prefix — 8 steps, paid once for all 76 cases

Before any case split, the rigid part of the instance already forces eight
deductions. Every one of the 76 cases inherits them, so they are written once.

| # | clause | pinned | colour | removes | domain left |
|---|--------|--------|--------|---------|-------------|
| 1 | {1, 33}     | 1      | 0 | 0 from 33 | 1,2,3,4 |
| 2 | {1, 63}     | 1      | 0 | 0 from 63 | 1,2,3,4 |
| 3 | {1, 23, 39} | 1, 23  | 0 | 0 from 39 | 1,2,3,4 |
| 4 | {7, 21}     | 7      | 2 | 2 from 21 | 3,4 |
| 5 | {7, 35}     | 7      | 2 | 2 from 35 | 3,4 |
| 6 | {7, 49}     | 7      | 2 | 2 from 49 | 3,4 |
| 7 | {7, 63}     | 7      | 2 | 2 from 63 | 1,3,4 |
| 8 | {13, 43, 73}| 13, 43 | 0 | 0 from 73 | 1,2,3,4 |

Read step 4 aloud: the pair `{7, 21}` is a cover pair; `7` is anchored to colour
2; therefore `21` cannot also be 2, and its domain drops to `{3, 4}`. Nothing
subtler happens anywhere in this argument — every one of the 2347 prune steps
has exactly this shape, with one or two roots on the left instead of one.

Note what the anchor buys. `7 = 2` has degree 25 in this instance: every triple
containing 7 collapses to a **binary** clause on colour 2. That is the mechanism
behind the whole tree being this shallow — steps 4–7 above are already four of
those twenty-five, spent before a single case is opened.

---

## 2. The branch structure

Seven roots carry the branching: `9, 11, 15, 17, 19, 21, 25`. Depth never
exceeds 6, and the leaves sit at:

| depth | leaves |
|-------|--------|
| 3 | 4 |
| 4 | 16 |
| 5 | 44 |
| 6 | 12 |

60 internal split nodes, 76 leaves, 136 nodes in total.

**Exhaustiveness is local, per node — not global.** This is worth stating
because I got it wrong once. The tempting formulation is "the 76 paths cover
every assignment of the seven branch roots over their initial domains". That is
false, and gate W2 was red for the right reason when it asked it: **999 of the
2187 total assignments die by propagation before any split is reached.** They
are covered by the derivation, not by a case. What W2 actually checks, and what
holds, is that at each of the 60 split nodes the children exhaust the root's
*surviving* domain at that node, recomputed by the checker rather than taken
from the tree walk.

---

## 3. One case worked in full — path `11↦2, 9↦3, 17↦3` (depth 3, 39 steps)

The shortest class of case. Prefix steps 1–8 above are assumed.

**Split 1 — pin `11 = 2`.** Seven prunes follow immediately:

- `{7, 9, 11}` with 7, 11 at colour 2 ⟹ `9` loses 2, domain `{3,4}`
- `{7, 11, 15}` ⟹ `15` loses 2, domain `{3,4}`
- `{7, 11, 25}` ⟹ `25` loses 2, domain `{3,4}`
- `{7, 11, 51}` ⟹ `51` loses 2, domain `{3,4}`
- `{11, 33}` ⟹ `33` loses 2, domain `{1,3,4}`
- `{11, 55}` ⟹ `55` loses 2, domain `{3,4}`
- `{11, 77}` ⟹ `77` loses 2, domain `{3,4}`

Four of these are triples firing on the pair `{7, 11}` — the anchor doing its
work again, one colour class at a time.

**Split 2 — pin `9 = 3`** (its domain is `{3,4}` after the previous step, so
this is one of two children):

- `{9, 27}` ⟹ `27` loses 3, domain `{2,4}`
- `{9, 63}` ⟹ `63` loses 3, domain `{1,4}`

**Split 3 — pin `17 = 3`.** Now the cascade runs:

- `{9, 17, 25}` ⟹ `25` loses 3, domain `{4}`
- `{9, 17, 55}` ⟹ `55` loses 3, domain `{4}`
- `{9, 17, 59}` ⟹ `59` loses 3, domain `{2,4}`
- `{15, 25, 55}` with 25, 55 now both forced to 4 ⟹ `15` loses 4, domain `{3}`
- `{17, 51}` ⟹ `51` loses 3, domain `{4}`
- `{19, 25, 51}` (25, 51 at 4) ⟹ `19` loses 4, domain `{2,3}`
- `{25, 75}` ⟹ `75` loses 4, domain `{2,3}`
- `{9, 15, 21}` ⟹ `21` loses 3, domain `{4}`
- `{9, 15, 33}` ⟹ `33` loses 3, domain `{1,4}`
- `{15, 75}` ⟹ `75` loses 3, domain `{2}`
- `{15, 17, 19}` ⟹ `19` loses 3, domain `{2}`
- `{15, 17, 77}` ⟹ `77` loses 3, domain `{4}`
- `{21, 63}` ⟹ `63` loses 4, domain `{1}`
- `{21, 25, 29}` ⟹ `29` loses 4, domain `{2,3}`
- `{25, 27, 77}` ⟹ `27` loses 4, domain `{2}`
- `{3, 33, 63}` ⟹ `33` loses 1, domain `{4}`
- `{3, 39, 63}` ⟹ `39` loses 1, domain `{2,3,4}`
- `{5, 63, 73}` ⟹ `73` loses 1, domain `{2,3,4}`

**Conflict.** `19` was forced to 2 (step "15,17,19"), `75` was forced to 2
(step "15,75"), and `7` is anchored at 2. The triple `{7, 19, 75}` is
monochromatic at colour 2. The case is dead.

Note the shape of the ending. The kill is not delivered by the roots that were
split on — `11`, `9`, `17` do not appear in the conflicting clause at all. It is
delivered by two roots squeezed to singletons twelve and sixteen steps
downstream. This is what makes the prose worth writing and the counts worth
distrusting: "depth 3" describes the *decisions*, not the *work*.

---

## 4. The exception, worked in full — path `11↦2, 9↦4, 17↦3` (depth 3, 41 steps)

This is the one leaf of the 76 that does **not** die on a monochromatic triple.
It is written here ahead of the bulk on purpose: an exception written last is an
exception written under pressure to conform to the 75 cases already on the page.

It is also the immediate sibling of §3 — same first split, and the second split
takes the other child (`9 = 4` where §3 took `9 = 3`). Prefix steps 1–8 and the
seven prunes of `11 = 2` are identical to §3 and are not repeated.

**Split 2 — pin `9 = 4`** (domain `{3,4}`, so this is the other child):

- `{9, 27}` ⟹ `27` loses 4, domain `{2,3}`
- `{9, 63}` ⟹ `63` loses 4, domain `{1,3}`

**Split 3 — pin `17 = 3`.** Twenty prunes, in the order the propagation queue
produces them:

- `{17, 51}` ⟹ `51` loses 3, domain `{4}`
- `{9, 21, 51}` (9, 51 at 4) ⟹ `21` loses 4, domain `{3}`
- `{17, 19, 21}` (17, 21 at 3) ⟹ `19` loses 3, domain `{2,4}`
- `{17, 21, 25}` ⟹ `25` loses 3, domain `{4}`
- `{19, 25, 51}` (25, 51 at 4) ⟹ `19` loses 4, domain `{2}` — **19 is now pinned**
- `{21, 63}` ⟹ `63` loses 3, domain `{1}`
- `{25, 75}` ⟹ `75` loses 4, domain `{2,3}`
- `{3, 33, 63}` ⟹ `33` loses 1, domain `{3,4}`
- `{3, 39, 63}` ⟹ `39` loses 1, domain `{2,3,4}`
- `{5, 63, 73}` ⟹ `73` loses 1, domain `{2,3,4}`
- `{7, 19, 75}` (7 anchored at 2, 19 at 2) ⟹ `75` loses 2, domain `{3}` — **75 pinned**
- `{9, 25, 59}` ⟹ `59` loses 4, domain `{2,3}`
- `{11, 19, 27}` (11, 19 at 2) ⟹ `27` loses 2, domain `{3}`
- `{11, 19, 41}` ⟹ `41` loses 2, domain `{3,4}`
- `{15, 75}` (75 at 3) ⟹ `15` loses 3, domain `{4}` — **15 pinned**
- `{15, 25, 35}` (15, 25 at 4) ⟹ `35` loses 4, domain `{3}`
- `{15, 25, 55}` (15, 25 at 4) ⟹ `55` loses 4, domain `{3}`
- `{17, 27, 41}` ⟹ `41` loses 3, domain `{4}`
- `{17, 29, 75}` ⟹ `29` loses 3, domain `{2,4}`
- `{21, 27, 33}` ⟹ `33` loses 3, domain `{4}`

**Conflict.** `35` and `55` are both squeezed to the singleton `{3}` — by the
two triples `{15, 25, 35}` and `{15, 25, 55}`, which are the same clause twice
over with the third root swapped. The cover block `¬(35 = 3 ∧ 55 = 3)` fires.
The case is dead, and this is the only case in the tree that ends this way.

**Why the exception is not structurally exceptional.** Compare the two endings.
In §3 the kill came from `19` and `75` squeezed to colour 2, with the anchor
`7 = 2` supplying the third root of `{7, 19, 75}`. Here it comes from `35` and
`55` squeezed to colour 3, with the *block* supplying what would otherwise be a
third root. Same shape: two roots forced to singletons far downstream, a fixed
partner completing the constraint. The anchor does for colour 2 what the negated
claim does for colour 3 — turns clauses binary. And in both cases the roots that
were split on — `11`, `9`, `17` — appear nowhere in the closing clause.

Note too the funnel: `21 → 63 → 33` and `19 → 75 → 15` are two chains of forced
singletons, and the second one is what actually delivers the kill. `15` is not a
branch root here; it arrives at `{4}` twelve steps after the last decision.

### 4.1 What the blocks actually do across the tree

Having found that I had never seen a block step, I measured their whole
footprint rather than assume this leaf was it:

| block | prunes | conflicts |
|-------|--------|-----------|
| `¬(11 = 3 ∧ 17 = 3)` | 26 | 0 |
| `¬(35 = 3 ∧ 55 = 3)` | 23 | 1 |

**50 of the 76 cases contain at least one block step.** So the negated claim is
not a rarely-touched goal that one unlucky branch stumbles into — it is load-
bearing in two thirds of the tree, almost always as a pruner and exactly once as
the executioner. That is invisible in the leaf-closure counts, which is why the
counts said "one exception" and the derivations say "one exceptional *ending*".

---

## 5. A leaf from the deep band, worked in full — path `11↦2, 9↦3, 17↦2, 19↦2, 21↦3` (depth 5, 31 steps)

§3 and §4 both sit at depth 3. This one is taken from the depth-5 band, the 44
leaves the previous instalment called "the bulk", to see whether the bulk is in
fact heavier.

It shares a **19-step prefix** with §3: the eight rigid deductions of §1, the
pin `11 = 2` with its seven prunes, and the pin `9 = 3` with its two. §3 then
splits `17 = 3`; here the other child is taken.

**Split 3 — pin `17 = 2`.** `17` still has `{2,3,4}`, so this is a live child:

- `{7, 17, 27}` with 7, 17 at colour 2 ⟹ `27` loses 2, domain `{4}`
- `{7, 17, 75}` ⟹ `75` loses 2, domain `{3,4}`
- `{11, 17, 39}` ⟹ `39` loses 2, domain `{1,3,4}`

**Split 4 — pin `19 = 2`.** One prune:

- `{11, 19, 41}` ⟹ `41` loses 2, domain `{3,4}`

**Split 5 — pin `21 = 3`** (its domain is `{3,4}` since prefix step 4):

- `{9, 15, 21}` with 9, 21 at colour 3 ⟹ `15` loses 3, domain `{4}`
- `{9, 21, 33}` ⟹ `33` loses 3, domain `{1,4}`
- `{9, 21, 51}` ⟹ `51` loses 3, domain `{4}`
- `{9, 21, 75}` ⟹ `75` loses 3, domain `{4}`

**Conflict.** `15` and `75` are both squeezed to `{4}` by the last split, and
`{15, 75}` is a clause. It is monochromatic at colour 4. The case is dead.

### 5.1 Depth is not work, and the deep band is the *cheap* one

I expected the deeper band to be heavier and wrote as much in the previous
instalment. It is not. Steps per leaf, by band:

| depth | leaves | shortest | longest |
|-------|--------|----------|---------|
| 3 | 4 | 39 | 41 |
| 4 | 16 | 31 | 44 |
| 5 | 44 | 30 | 44 |
| 6 | 12 | 37 | 48 |

The leaf above is 31 steps; §3, three splits shallower, is 39. The depth-5 band
has the lowest median of the four. The reason is visible in the derivation: a
shallow leaf has to be killed by propagation alone, so it runs a long cascade
(§3 spends eighteen steps after its last split); a deep leaf gets more of its
domains cut by decisions, and each decision then has less left to propagate.
Depth counts decisions; steps count work; the two run *against* each other here
over most of the range.

### 5.2 The killing clause: a majority shape, not the shape

§3 and §4 both ended on a clause containing none of the roots that had been
split on, and I wrote that up as "the shape of the ending" from those two
examples. Measured over all 76: **26 leaves have a split root in their killing
clause, and 50 do not.** So it is what two thirds of the tree does, not what the
tree does. The leaf above is in the majority — it dies on `{15, 75}` while the
splits were on `11, 9, 17, 19, 21`. Two examples were enough to see the shape
and not enough to quantify it; the correction is recorded here rather than in
the file's history.

### 5.3 What a leaf costs the reader, once the prefixes overlap

This leaf is 31 steps but adds only **12** steps the prefix tree had not already
seen, because 19 of them are §3's. Three worked leaves then covered **76 of the
1116 distinct steps**. The first two, 39 and 41 steps, bought 64; the third, at
31 steps, buys 12. That is the curve that decides whether the remaining 73 are
writable by hand, and it is bending the right way — but it bends because the
leaves were chosen adjacent, and adjacency is a choice I made, not a property of
the tree. Whether it holds across the band is not established here.

---

## 6. A leaf drawn by lot — path `11↦3, 9↦2, 17↦2, 19↦3` (depth 4, 35 steps)

§5 closed with a caveat against its own result: the marginal cost per leaf was
falling, but the three leaves written so far had been picked *adjacent*, and
adjacency is a choice of route, not a property of the tree. A cost curve
measured along a route the author chose is a statement about the author.

So this one was not chosen. The index into the case list was fixed as
`int("a3cf376a4c14", 16) mod 76`, where the hex string is the SHA-256 prefix of
an unrelated append-only ledger published on 2026-08-04, hours before this
section was begun and outside this repository. The rule, the seed and the
tie-break (advance by one if the draw lands on an already-written leaf) were
written down before the draw was run. The draw gave index 16.

It landed on the far side of the first split. Every leaf written so far pins
`11 = 2`; this one pins `11 = 3`, so it shares with them only the **8 rigid
steps** of §1 and nothing else.

**Split 1 — pin `11 = 3`.** The other child of the root split:

- `{11, 33}` with 11 at colour 3 ⟹ `33` loses 3, domain `{1,2,4}`
- `{11, 55}` ⟹ `55` loses 3, domain `{2,4}`
- `{11, 77}` ⟹ `77` loses 3, domain `{2,4}`
- `{11, 17}` — the cover block `¬(11 = 3 ∧ 17 = 3)` ⟹ `17` loses 3, domain `{2,4}`

**Split 2 — pin `9 = 2`:**

- `{7, 9, 19}` with 7, 9 at colour 2 ⟹ `19` loses 2, domain `{3,4}`
- `{7, 9, 25}` ⟹ `25` loses 2, domain `{3,4}`
- `{7, 9, 29}` ⟹ `29` loses 2, domain `{3,4}`
- `{7, 9, 65}` ⟹ `65` loses 2, domain `{3,4}`
- `{9, 27}` ⟹ `27` loses 2, domain `{3,4}`

**Split 3 — pin `17 = 2`** (its domain is `{2,4}` after the block fired):

- `{7, 17, 75}` ⟹ `75` loses 2, domain `{3,4}`
- `{9, 17, 55}` ⟹ `55` loses 2, domain `{4}`
- `{9, 17, 59}` ⟹ `59` loses 2, domain `{3,4}`
- `{17, 51}` ⟹ `51` loses 2, domain `{3,4}`

**Split 4 — pin `19 = 3`:**

- `{11, 15, 19}` with 11, 19 at colour 3 ⟹ `15` loses 3, domain `{2,4}`
- `{11, 19, 25}` ⟹ `25` loses 3, domain `{4}`
- `{11, 19, 27}` ⟹ `27` loses 3, domain `{4}`
- `{11, 19, 41}` ⟹ `41` loses 3, domain `{2,4}`

**Cascade.** `25`, `27` and `55` are now singletons at colour 4, and that is
enough to finish without another decision:

- `{15, 25, 55}` with 25, 55 at colour 4 ⟹ `15` loses 4, domain `{2}`
- `{25, 75}` ⟹ `75` loses 4, domain `{3}`
- `{25, 27, 77}` ⟹ `77` loses 4, domain `{2}`
- `{7, 15, 41}` with 7, 15 at colour 2 ⟹ `41` loses 2, domain `{4}`
- `{9, 15, 33}` ⟹ `33` loses 2, domain `{1,4}`

**Conflict.** `15` and `77` are pinned to `{2}` by the cascade and `17` was
split to 2. `{15, 17, 77}` is a clause, monochromatic at colour 2. The case is
dead.

### 6.1 The curve was the route

This leaf is 35 steps and adds **27** steps the prefix tree had not seen.
Against §5's 12, on a leaf three steps *shorter*. The four worked leaves now
cover **103 of the 1116 distinct steps**.

The caveat §5 attached to its own number was the right one, and the correction
is larger than a caveat usually earns: the falling curve was not a weak trend
that a random draw would soften, it was an artefact of sharing a 19-step prefix.
Marginal cost is governed by where a leaf sits relative to what is already
written, and nothing else measured here. Extrapolating 73 × 12 from the third
leaf would have understated the remaining prose by a factor I decline to
estimate, because the estimate would again be a property of the route.

### 6.2 Two things the chosen leaves could not have shown

**The killing clause contains a split root.** §5.2 measured this over all 76 —
26 leaves do, 50 do not — but all three worked leaves were in the 50. This one
is in the 26: it dies on `{15, 17, 77}` while `17` is one of its own splits.
Adjacency had biased not only the cost but the *shape* of the ending, and the
count in §5.2 is what kept that from being written up a second time as a rule.

**The block finally fires.** §2 counts `pair_prune` steps on the cover block
`¬(11 = 3 ∧ 17 = 3)`, and §4 was written specifically because the block appears
in a *conflict* somewhere in the tree. But a block prune requires `11 = 3`, and
every leaf worked before this one pins `11 = 2` — so in three instalments the
file tabulated a step kind that none of its own worked examples exercised.
Step 13 above is the first. Nothing was wrong; the tables were right the whole
time. It is just that the side of the split which produces no worked example
also produces no complaint, and would have gone on producing none for as long as
I kept choosing leaves myself.

---

## 7. What remains

72 leaves. No shortcut is claimed for them: they are ordinary, and after §5 they
are also known to be no worse per leaf than the ones already written. §3 and §4
share a 16-step prefix with each other; §5 shares nineteen steps with §3; §6
shares eight with all three.

The exception is now written (§4) and it cost one correction to the file rather
than none — writing it is what surfaced the `pair_prune` kind and the broken
step ledger in §0. Had it been left for last, the ledger would have been wrong
in every intervening instalment.

Open, unchanged by this file: the same treatment for `c=4` (85 triples), and the
standing debt of moving `rigid` into `soft`, which would change every number
above and is the reason each is published with its condition attached.
