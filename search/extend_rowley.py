"""
Use the REAL record structure as a seed.

Rowley's WS(6)=642 construction introduces its 6th color only at element 175.
So its restriction to {1..M}, where M = (first position of color 6) - 1, is a
valid 5-coloring of {1..M} with the genuine record structure (sparse absorbing
color + length-3 interleaved blocks). That is a far better seed than an ad-hoc
monolithic block. We take it and extend toward 196 / 197.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa
from seed_construct import greedy_tail, backtrack_tail  # noqa
from extend_test import matching_test  # noqa

here = os.path.dirname(__file__)
vals = [int(x) for x in open(os.path.join(here, "out", "rowley_ws6_642_raw.txt")).read().split()]

# largest prefix using <= 5 colors
M = 0
seen = set()
for i, v in enumerate(vals, start=1):
    seen.add(v)
    if len(seen | {v}) > 5 and v not in (seen - {v}):
        pass
    if v == 6:
        M = i - 1
        break
if M == 0:
    M = len(vals)
print(f"Rowley uses <=5 colors on prefix 1..{M} (color 6 first appears at {M+1})")

base = {n: vals[n - 1] - 1 for n in range(1, M + 1)}  # 0-indexed colors 0..4
parts = [[n for n in base if base[n] == c] for c in range(5)]
ok, reason = verify_weak_schur([p for p in parts if p], M)
print(f"seed 5-coloring of 1..{M}: gate={'PASS' if ok else 'FAIL ' + str(reason)}")
print(f"  part sizes: {[len(p) for p in parts]}")

# extend
gN, _ = greedy_tail(base, 5, M + 1, 220)
print(f"greedy extend from {M+1} -> {gN}")

for budget in (30, 90):
    t = time.time()
    bN, bcol = backtrack_tail(base, 5, M + 1, 220, time.time() + budget)
    bparts = [[n for n in bcol if bcol[n] == c] for c in range(5)]
    okb, rb = verify_weak_schur([p for p in bparts if p], bN)
    print(f"backtrack extend from {M+1} ({budget}s) -> {bN}  gate={'PASS' if okb else 'FAIL ' + str(rb)}")
    if bN >= 185:
        # matching test for bN+1 on the reached construction
        mt = matching_test(bparts, bN + 1)
        free = [i for i, bl in mt if not bl]
        print(f"   reached {bN}; classes free for {bN+1}: {free if free else 'none'} "
              f"(min blocks {min(len(bl) for _, bl in mt)})")
        outdir = os.path.join(here, "out"); os.makedirs(outdir, exist_ok=True)
        with open(os.path.join(outdir, f"rowleyseed_ws5_N{bN}.txt"), "w") as f:
            for i, p in enumerate(bparts):
                f.write(f"part {i}: {' '.join(map(str, sorted(p)))}\n")
    if bN > 196:
        print(f"   *** N={bN} > 196 CANDIDATE — adversarial re-verify ***")
