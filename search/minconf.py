"""
Min-conflicts attack on weak Schur (WalkSAT-style + tabu + perturbation kicks).

The structured annealer reached conf=1 at N=196 but stalled on the last
conflict (single-element focus can't tunnel a coordinated barrier). This adds
the standard cures: tabu tenure (no immediate reversal), occasional random
walk, and a perturbation kick on stagnation. Goal: drive conflicts to 0.

Discipline: reaching conf=0 only *claims* a valid coloring — it is the GATE
(verify_weak_schur) that decides truth. A conf=0 at N=197 that passes the gate
is a genuine new lower bound WS(5) >= 197, independently checkable by anyone.
"""
import sys, os, time, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa
from structured_search import State, geometric_init  # noqa


def min_conflicts(N, k, max_steps, seed, tabu_tenure=12, stall_limit=40000,
                  p_walk=0.03, init="geo"):
    rnd = random.Random(seed)
    if init == "geo":
        color = geometric_init(N, k)
    else:
        color = [0] + [rnd.randrange(k) for _ in range(N)]
    st = State(N, k, color)
    best, best_color = st.conf, st.color[:]
    tabu = [0] * (N + 1)
    stall = 0
    for step in range(1, max_steps + 1):
        if st.conf == 0:
            break
        idx = rnd.choice(tuple(st.badset))
        a, b, z = st.triples[idx]
        cands = [a, b, z]
        rnd.shuffle(cands)
        e = cands[0]
        for c in cands:
            if tabu[c] <= step:
                e = c
                break
        old = st.color[e]
        if rnd.random() < p_walk:
            nc = rnd.randrange(k)
        else:
            bnc, bd = old, 10 ** 9
            order = list(range(k)); rnd.shuffle(order)
            for c in order:
                if c == old:
                    continue
                d = st.delta_if(e, c)
                if d < bd:
                    bd, bnc = d, c
            nc = bnc
        if nc != old:
            st.flip(e, nc)
            tabu[e] = step + tabu_tenure
        if st.conf < best:
            best, best_color = st.conf, st.color[:]
            stall = 0
        else:
            stall += 1
            if stall >= stall_limit:
                for _ in range(max(3, N // 12)):
                    st.flip(rnd.randint(1, N), rnd.randrange(k))
                stall = 0
    runs = sum(1 for n in range(2, N + 1) if best_color[n] != best_color[n - 1])
    return best, best_color, runs


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 197
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    steps = int(sys.argv[3]) if len(sys.argv) > 3 else 3_000_000
    seeds = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    t0 = time.time()
    overall = None
    for seed in range(1, seeds + 1):
        init = "geo" if seed % 2 else "rand"
        conf, color, runs = min_conflicts(N, k, steps, seed, init=init)
        tag = f"seed={seed}({init}): conf={conf} runs={runs}  [{time.time()-t0:.0f}s]"
        print(tag, flush=True)
        if overall is None or conf < overall[0]:
            overall = (conf, color, runs)
        if conf == 0:
            break
    conf, color, runs = overall
    print(f"BEST N={N} k={k}: conf={conf} runs={runs} ({time.time()-t0:.0f}s)", flush=True)
    if conf == 0:
        parts = [[] for _ in range(k)]
        for n in range(1, N + 1):
            parts[color[n]].append(n)
        ok, reason = verify_weak_schur(parts, N)
        print(f"  GATE: {'PASS' if ok else 'FAIL — ' + str(reason)}")
        if ok:
            outdir = os.path.join(os.path.dirname(__file__), "out")
            os.makedirs(outdir, exist_ok=True)
            fn = os.path.join(outdir, f"minconf_ws{k}_N{N}.txt")
            with open(fn, "w") as f:
                for i, p in enumerate(parts):
                    f.write(f"part {i}: {' '.join(map(str, p))}\n")
            print(f"  saved -> {fn}")
            if N > 196:
                print(f"  *** conf=0 at N={N} > 196 — CANDIDATE NEW LOWER BOUND, needs adversarial re-verify ***")
