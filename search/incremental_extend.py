"""
Climb from the best valid construction (seed -> 184) one element at a time,
using direct extension where possible and a small matching-repair where not.

For target T = cur+1: T joins class c iff c has no pair (a,T-a). If some class
is already free, drop T in (gate-checked). Else try to FREE a class by moving a
few of its blocking elements (either endpoint of each blocking pair) elsewhere,
keeping everything valid. Stop when neither works. Report the max reach.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa
from seed_construct import load_saved, build_seed, backtrack_tail  # noqa
from extend_test import matching_test  # noqa


def valid(parts):
    nonempty = [p for p in parts if p]
    N = max(max(p) for p in nonempty)
    return verify_weak_schur(nonempty, N)[0]


def try_direct(parts, T):
    for i, blocks in matching_test(parts, T):
        if not blocks:
            new = [list(p) for p in parts]
            new[i].append(T)
            if valid(new):
                return new
    return None


def try_repair(parts, T, max_moves=3):
    mt = matching_test(parts, T)
    for i, blocks in sorted(mt, key=lambda t: len(t[1])):
        if not blocks or len(blocks) > max_moves:
            continue
        # need to break every blocking pair in class i by moving ONE endpoint out
        new = [list(p) for p in parts]
        ok_all = True
        for (a, b) in blocks:
            moved = False
            for e in (b, a):  # try larger endpoint first (fewer triples)
                if e not in new[i]:
                    moved = True; break  # already gone via earlier move
                trial_src = [list(p) for p in new]
                trial_src[i].remove(e)
                for j in range(len(trial_src)):
                    if j == i:
                        continue
                    cand = [list(p) for p in trial_src]
                    cand[j].append(e)
                    if valid(cand):
                        new = cand; moved = True; break
                if moved:
                    break
            if not moved:
                ok_all = False; break
        if not ok_all:
            continue
        # class i now T-independent; add T
        res = try_direct(new, T)
        if res:
            return res
    return None


if __name__ == "__main__":
    here = os.path.dirname(__file__)
    ws4 = load_saved(os.path.join(here, "out", "ws4_N66.txt"))
    seed = build_seed(ws4, 134)
    base = dict(seed)
    bN, bcol = backtrack_tail(base, 5, 135, 220, time.time() + 30)
    parts = [[n for n in bcol if bcol[n] == c] for c in range(5)]
    cur = bN
    print(f"start from seed construction, valid up to N={cur}, gate={valid(parts)}")
    t0 = time.time()
    while time.time() - t0 < 120:
        T = cur + 1
        res = try_direct(parts, T)
        how = "direct"
        if not res:
            res = try_repair(parts, T, max_moves=4)
            how = "repair"
        if not res:
            print(f"  stuck at {cur} (cannot place {T})")
            break
        parts = res; cur = T
        print(f"  extended to {cur} via {how}", flush=True)
        if cur > 196:
            print(f"  *** N={cur} > 196 CANDIDATE — adversarial re-verify ***")
            break
    print(f"MAX REACH: {cur}  (record 196), gate={valid(parts)}")
    if cur > 184:
        outdir = os.path.join(here, "out"); os.makedirs(outdir, exist_ok=True)
        with open(os.path.join(outdir, f"incr_ws5_N{cur}.txt"), "w") as f:
            for i, p in enumerate(parts):
                f.write(f"part {i}: {' '.join(map(str, sorted(p)))}\n")
        print(f"  saved incr_ws5_N{cur}.txt")
