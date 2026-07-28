"""
Probe C — belief propagation / backbone on the weak-Schur triple factor graph.

Variables v=1..N, k=5 colour states. One factor per triple (a,b,a+b): forbids
all three taking the SAME colour. Plain BP on a fully colour-symmetric problem
sits at the trivial uniform fixed point, so we break symmetry: clamp element 1
to colour 0 and seed messages with small noise. Then iterate sum-product and read
off per-variable marginals.

Reported: convergence, # near-frozen variables (max marginal > 0.9), avg entropy.
Compare N=196 vs N=197 -> does the backbone differ / does BP stop converging at
197? Near threshold, a contradiction (if any) concentrates in the frozen backbone.
NOT a proof -- a structural lens on where the rigidity lives.
"""
import sys, time, math, random
import collections


def triples(N):
    T = []
    for a in range(1, N + 1):
        for b in range(a + 1, N + 1):
            z = a + b
            if z > N:
                break
            T.append((a, b, z))
    return T


def bp(N, k=5, iters=400, damp=0.5, tol=1e-4, seed=7):
    rng = random.Random(seed)
    T = triples(N)
    inc = collections.defaultdict(list)            # var -> [(factor_idx, slot)]
    for fi, (a, b, z) in enumerate(T):
        inc[a].append((fi, 0)); inc[b].append((fi, 1)); inc[z].append((fi, 2))

    def norm(x):
        s = sum(x) or 1.0
        return [xi / s for xi in x]

    mvf = {(fi, s): norm([1.0 + 0.1 * rng.random() for _ in range(k)])
           for fi in range(len(T)) for s in range(3)}
    mfv = {(fi, s): [1.0] * k for fi in range(len(T)) for s in range(3)}

    def clamp1():                                   # element 1 -> colour 0
        for (fi, s) in inc[1]:
            mvf[(fi, s)] = [1.0] + [0.0] * (k - 1)

    clamp1()
    conv = False
    for it in range(iters):
        # factor -> var : forbid all-three-equal
        for fi, (a, b, z) in enumerate(T):
            inn = (mvf[(fi, 0)], mvf[(fi, 1)], mvf[(fi, 2)])
            for s in range(3):
                o1, o2 = (j for j in range(3) if j != s), None
                others = [j for j in range(3) if j != s]
                m = [0.0] * k
                A, B = inn[others[0]], inn[others[1]]
                total_all = sum(A) * sum(B)
                for x in range(k):
                    # sum over y,w of A[y]B[w] minus the y==w==x forbidden term
                    m[x] = total_all - A[x] * B[x]
                mm = norm(m)
                old = mfv[(fi, s)]
                mfv[(fi, s)] = [damp * old[i] + (1 - damp) * mm[i] for i in range(k)]
        # var -> factor
        maxdiff = 0.0
        for v in range(1, N + 1):
            for (fi, slot) in inc[v]:
                prod = [1.0] * k
                for (gj, gs) in inc[v]:
                    if gj == fi and gs == slot:
                        continue
                    mg = mfv[(gj, gs)]
                    for i in range(k):
                        prod[i] *= mg[i]
                nm = norm(prod)
                old = mvf[(fi, slot)]
                d = max(abs(nm[i] - old[i]) for i in range(k))
                if d > maxdiff:
                    maxdiff = d
                mvf[(fi, slot)] = nm
        clamp1()
        if it % 25 == 0:
            print(f"  N={N} iter {it} maxdiff={maxdiff:.5f}", flush=True)
        if maxdiff < tol:
            conv = True
            print(f"  N={N} converged at iter {it}", flush=True)
            break

    frozen = 0
    ent = 0.0
    for v in range(1, N + 1):
        prod = [1.0] * k
        for (gj, gs) in inc[v]:
            mg = mfv[(gj, gs)]
            for i in range(k):
                prod[i] *= mg[i]
        marg = norm(prod)
        ent += -sum(p * math.log(p + 1e-12) for p in marg)
        if max(marg) > 0.9:
            frozen += 1
    print(f"N={N}: converged={conv} frozen(>0.9)={frozen}/{N} avg_entropy={ent / N:.4f}", flush=True)
    return conv, frozen


if __name__ == "__main__":
    targets = [int(x) for x in sys.argv[1:]] or [196, 197]
    for N in targets:
        t0 = time.time()
        bp(N)
        print(f"  ({time.time() - t0:.1f}s)\n", flush=True)
