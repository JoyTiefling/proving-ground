"""
Angle #1: search the GENERATING STRUCTURE, not arbitrary colorings.

Hypothesis: record weak-Schur partitions are (near) interval-structured — each
color class is a union of a few intervals, i.e. the coloring of {1..N} has few
"runs" (positions where the color changes). If true, the real search space is
the handful of cut-points, not k^N.

Method: simulated annealing with MIN-CONFLICTS focused moves (WalkSAT-style):
most moves target an element inside a currently-violated triple and recolor it
to minimise conflicts, instead of poking random elements. Energy rewards both
zero conflicts and few runs:  energy = conflicts + lam * runs.
- conf == 0 with small runs at N=196 -> records ARE low-description interval.
- conf stuck > 0 unless runs ~ N      -> records need scattered structure.

Any conf==0 result is re-checked by the gate. No claim without a runnable gate.
"""
import sys, os, time, math, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa


def build_triples(N):
    t = []
    for a in range(1, N + 1):
        for b in range(a + 1, N + 1):
            z = a + b
            if z > N:
                break
            t.append((a, b, z))
    return t


class State:
    def __init__(self, N, k, color):
        self.N, self.k = N, k
        self.color = color[:]
        self.triples = build_triples(N)
        self.tof = [[] for _ in range(N + 1)]
        for idx, (a, b, z) in enumerate(self.triples):
            self.tof[a].append(idx); self.tof[b].append(idx); self.tof[z].append(idx)
        self.bad = [False] * len(self.triples)
        self.badset = set()
        for idx, (a, b, z) in enumerate(self.triples):
            if self.color[a] == self.color[b] == self.color[z]:
                self.bad[idx] = True; self.badset.add(idx)
        self.conf = len(self.badset)
        self.runs = sum(1 for n in range(2, N + 1) if self.color[n] != self.color[n - 1])

    def delta_if(self, e, nc):
        """Conflict delta if we set color[e]=nc, WITHOUT applying."""
        old = self.color[e]
        if nc == old:
            return 0
        d = 0
        self.color[e] = nc
        for idx in self.tof[e]:
            a, b, z = self.triples[idx]
            nb = self.color[a] == self.color[b] == self.color[z]
            if nb and not self.bad[idx]:
                d += 1
            elif not nb and self.bad[idx]:
                d -= 1
        self.color[e] = old
        return d

    def run_delta_if(self, e, nc):
        N = self.N
        old = self.color[e]
        before = after = 0
        if e > 1:
            before += (old != self.color[e - 1]); after += (nc != self.color[e - 1])
        if e < N:
            before += (old != self.color[e + 1]); after += (nc != self.color[e + 1])
        return after - before

    def flip(self, e, nc):
        if self.color[e] == nc:
            return
        self.runs += self.run_delta_if(e, nc)
        self.color[e] = nc
        for idx in self.tof[e]:
            a, b, z = self.triples[idx]
            nb = self.color[a] == self.color[b] == self.color[z]
            if nb and not self.bad[idx]:
                self.bad[idx] = True; self.badset.add(idx); self.conf += 1
            elif not nb and self.bad[idx]:
                self.bad[idx] = False; self.badset.discard(idx); self.conf -= 1


def geometric_init(N, k):
    color = [0] * (N + 1)
    bnds = [int(round(N ** (i / k))) for i in range(k + 1)]
    for n in range(1, N + 1):
        c = 0
        for i in range(k):
            if n > bnds[i]:
                c = i
        color[n] = min(c, k - 1)
    return color


def anneal(N, k, lam=0.3, iters=2000000, seed=1, t0=3.0, t1=0.02, p_focus=0.85):
    rnd = random.Random(seed)
    st = State(N, k, geometric_init(N, k))
    best_conf, best_runs, best_color = st.conf, st.runs, st.color[:]
    for it in range(iters):
        T = t0 * (t1 / t0) ** (it / iters)
        # choose target element
        if st.badset and rnd.random() < p_focus:
            idx = rnd.choice(tuple(st.badset))
            e = rnd.choice(self_triple := st.triples[idx])
        else:
            e = rnd.randint(1, N)
        old = st.color[e]
        # choose new color: min-conflicts (greedy) most of the time
        if rnd.random() < 0.8:
            best_nc, best_d = old, 10 ** 9
            order = list(range(k)); rnd.shuffle(order)
            for nc in order:
                if nc == old:
                    continue
                d = st.delta_if(e, nc) + lam * st.run_delta_if(e, nc)
                if d < best_d:
                    best_d, best_nc = d, nc
            nc = best_nc
        else:
            nc = rnd.randint(0, k - 1)
        if nc == old:
            continue
        dE = st.delta_if(e, nc) + lam * st.run_delta_if(e, nc)
        if dE <= 0 or rnd.random() < math.exp(-dE / T):
            st.flip(e, nc)
            if st.conf < best_conf or (st.conf == best_conf and st.runs < best_runs):
                best_conf, best_runs, best_color = st.conf, st.runs, st.color[:]
                if best_conf == 0:
                    break
    return best_conf, best_runs, best_color


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 196
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    lam = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3
    iters = int(sys.argv[4]) if len(sys.argv) > 4 else 2000000
    best = None
    t0 = time.time()
    for seed in range(1, 6):  # a few restarts
        conf, runs, color = anneal(N, k, lam=lam, iters=iters, seed=seed)
        if best is None or conf < best[0] or (conf == best[0] and runs < best[1]):
            best = (conf, runs, color)
        print(f"  seed={seed}: conf={conf} runs={runs}  (elapsed {time.time()-t0:.1f}s)")
        if best[0] == 0:
            break
    conf, runs, color = best
    dt = time.time() - t0
    print(f"BEST N={N} k={k}: conf={conf} runs={runs} ({dt:.1f}s)")
    # always persist the best near-solution (for targeted repair) + locate conflicts
    outdir = os.path.join(os.path.dirname(__file__), "out")
    os.makedirs(outdir, exist_ok=True)
    nearfn = os.path.join(outdir, f"near_ws{k}_N{N}_conf{conf}.txt")
    parts_all = [[] for _ in range(k)]
    for n in range(1, N + 1):
        parts_all[color[n]].append(n)
    with open(nearfn, "w") as f:
        for i, p in enumerate(parts_all):
            f.write(f"part {i}: {' '.join(map(str, p))}\n")
    if conf > 0:
        bad = []
        for i, p in enumerate(parts_all):
            ps = set(p)
            for x in sorted(ps):
                for y in sorted(ps):
                    if x < y and x + y in ps:
                        bad.append((i, x, y, x + y))
        print(f"  saved near-solution -> {nearfn}")
        print(f"  conflicts ({len(bad)}): {bad[:6]}")
    if conf == 0:
        parts = [[] for _ in range(k)]
        for n in range(1, N + 1):
            parts[color[n]].append(n)
        ok, reason = verify_weak_schur(parts, N)
        print(f"  GATE: {'PASS' if ok else 'FAIL — ' + str(reason)}  runs={runs}")
        if ok:
            outdir = os.path.join(os.path.dirname(__file__), "out")
            os.makedirs(outdir, exist_ok=True)
            fn = os.path.join(outdir, f"structured_ws{k}_N{N}_runs{runs}.txt")
            with open(fn, "w") as f:
                for i, p in enumerate(parts):
                    f.write(f"part {i}: {' '.join(map(str, p))}\n")
            print(f"  saved -> {fn}")
