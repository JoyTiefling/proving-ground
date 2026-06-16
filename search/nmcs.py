"""
Nested Monte Carlo Search (NMCS, Cazenave) for weak Schur lower bounds.

A genuinely different family from the local-search/ejection methods (which
stalled at 195): MONTE CARLO with LOOKAHEAD. Build the coloring sequentially
(assign 1,2,3,...). At each element, evaluate each candidate color by a random
playout (level 1) or a nested NMCS (level>=2) to the end, then commit the move
that leads furthest. This is the method family Bouzy used for weak Schur.

Construction is in increasing order, so element e only ever appears as a SUM:
e may take color c iff c holds no pair (a, e-a). Reaching N means a valid
5-coloring of {1..N}. Gate-checked; > 196 = candidate new bound, re-verify.
"""
import sys, os, time, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa


def valid_colors(parts, e, k):
    out = []
    for c in range(k):
        s = parts[c]
        ok = True
        a = 1
        while 2 * a < e:
            if a in s and (e - a) in s:
                ok = False
                break
            a += 1
        if ok:
            out.append(c)
    return out


def rollout(parts, e, k, rnd, Nmax):
    parts = [set(p) for p in parts]
    seq = []
    while e <= Nmax:
        vc = valid_colors(parts, e, k)
        if not vc:
            break
        c = rnd.choice(vc)
        parts[c].add(e)
        seq.append(c)
        e += 1
    return e - 1, seq


def nmcs(parts, e, k, level, rnd, Nmax, deadline):
    parts = [set(p) for p in parts]
    seq = []
    best_reach, best_seq = e - 1, []
    while e <= Nmax and time.time() < deadline:
        vc = valid_colors(parts, e, k)
        if not vc:
            break
        best_c, best_r, best_sub = None, -1, []
        for c in vc:
            trial = [set(p) for p in parts]
            trial[c].add(e)
            if level <= 1:
                r, sub = rollout(trial, e + 1, k, rnd, Nmax)
            else:
                r, sub = nmcs(trial, e + 1, k, level - 1, rnd, Nmax, deadline)
            if r > best_r:
                best_r, best_c, best_sub = r, c, sub
            if r > best_reach:
                best_reach, best_seq = r, seq + [c] + sub
        parts[best_c].add(e)
        seq.append(best_c)
        e += 1
    if e - 1 > best_reach:
        best_reach, best_seq = e - 1, seq
    return best_reach, best_seq


if __name__ == "__main__":
    k = 5
    level = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    budget = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    seeds = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    Nmax = 210
    t0 = time.time()
    deadline = t0 + budget
    best = (0, [])
    for s in range(seeds):
        if time.time() > deadline:
            break
        rnd = random.Random(1000 + s)
        parts = [set() for _ in range(k)]
        reach, seq = nmcs(parts, 1, k, level, rnd, Nmax, deadline)
        if reach > best[0]:
            best = (reach, seq)
            print(f"  seed {s}: reach {reach}  [{time.time()-t0:.0f}s]", flush=True)
    reach, seq = best
    print(f"NMCS level={level}: BEST reach {reach} (record 196, {time.time()-t0:.0f}s)")
    # rebuild + gate
    parts = [[] for _ in range(k)]
    for i, c in enumerate(seq, start=1):
        parts[c].append(i)
    ok, reason = verify_weak_schur([p for p in parts if p], reach)
    print(f"  gate@{reach}: {'PASS' if ok else 'FAIL ' + str(reason)}")
    if ok and reach > 180:
        with open(os.path.join(os.path.dirname(__file__), "out", f"nmcs_ws5_N{reach}.txt"), "w") as f:
            for i, p in enumerate(parts):
                f.write(f"part {i}: {' '.join(map(str, p))}\n")
        print(f"  saved nmcs_ws5_N{reach}.txt")
    if reach > 196:
        print(f"  *** N={reach} > 196 — CANDIDATE NEW BOUND, adversarial re-verify required ***")
