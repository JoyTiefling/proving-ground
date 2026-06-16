"""
Push past the 184 wall by RELAXING the rigid block.

seed_construct fixed [1..134] (WS(4) prefix + a monolithic new-color block) and
backtracked only [135..N], reaching 184. The monolithic block over-constrains.
Here we fix ONLY [1..66] = WS(4) record and let backtracking choose everything
from 67 upward (5 colors free) — more freedom, bigger but still bounded search.
Greedy color order dives fast; we keep the deepest valid reach within a budget.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa
from seed_construct import load_saved, greedy_tail, backtrack_tail  # noqa

here = os.path.dirname(__file__)
ws4 = load_saved(os.path.join(here, "out", "ws4_N66.txt"))
base = {n: c for c, part in enumerate(ws4) for n in part}  # [1..66] fixed

gN, _ = greedy_tail(base, 5, 67, 300)
print(f"fix [1..66], greedy from 67 -> {gN}", flush=True)

for budget in (60, 120):
    t = time.time()
    bN, bcol = backtrack_tail(base, 5, 67, 300, time.time() + budget)
    parts = [[n for n in bcol if bcol[n] == c] for c in range(5)]
    ok, reason = verify_weak_schur([p for p in parts if p], bN)
    print(f"fix [1..66], backtrack from 67 ({budget}s) -> {bN}  "
          f"gate={'PASS' if ok else 'FAIL ' + str(reason)}  ({time.time()-t:.0f}s)", flush=True)
    if bN >= 185:
        outdir = os.path.join(here, "out"); os.makedirs(outdir, exist_ok=True)
        with open(os.path.join(outdir, f"deeptail_ws5_N{bN}.txt"), "w") as f:
            for i, p in enumerate(parts):
                f.write(f"part {i}: {' '.join(map(str, sorted(p)))}\n")
        print(f"  saved deeptail_ws5_N{bN}.txt", flush=True)
    if bN > 196:
        print(f"  *** N={bN} > 196 CANDIDATE — adversarial re-verify required ***", flush=True)
