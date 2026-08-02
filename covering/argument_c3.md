# The 2-pair cover claim at c=3, written out by hand — head of the argument

Status: **PARTIAL.** The shared prefix, the branch structure and one fully worked
leaf are written below. The remaining 75 leaves are not. This file is the first
instalment of "write the 76 cases out in prose", not its completion.

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

Two step kinds appear:

- **prune** — clause `C` with all-but-one of its roots already pinned to colour
  `x` removes `x` from the domain of the remaining root;
- **conflict** — a clause all of whose roots are pinned to one colour. This is
  where a case dies.

Across all 76 cases there are 2347 prune steps, 368 pins, **75 leaves closing on
a monochromatic triple and exactly one on a cover pair**. Written case-by-case
that is 2840 steps; with shared prefixes written once it is **1116 distinct
steps**. 1116 — not 76, and not 92 — is the number that decides whether this is
writable by hand. (Three different magnitudes for one question, each of which I
announced in turn as the answer; the one that decides is the one a floor below.)

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

## 4. What remains

75 leaves. By the step counts above, roughly 1080 further distinct steps, of
which the depth-5 band (44 leaves) is the bulk. One leaf — the single
`pair_conflict` — closes differently from the other 75 and should be written
next, ahead of the bulk: an exception written last is an exception written
under pressure to conform.

Open, unchanged by this file: the same treatment for `c=4` (85 triples), and the
standing debt of moving `rigid` into `soft`, which would change every number
above and is the reason each is published with its condition attached.
