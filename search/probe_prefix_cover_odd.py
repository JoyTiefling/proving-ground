"""C-015 второй носитель КОДИРОВКИ: переменные только на нечётных (chain подставлен
через odd-part, а не выражен клаузами), конфликты x<y, x+y=z пишутся заново, не
через sat_chain_mono.build_cnf. Общий с первым носителем только перечислитель
классов (у него свои три носителя полноты)."""
import sys, json, time, pathlib
from multiprocessing import Pool
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import probe_prefix_cover as ppc

def odd(v):
    while v % 2 == 0: v //= 2
    return v

def cnf_odd(k, N):
    idx = {m: i for i, m in enumerate(range(1, N + 1, 2))}
    var = lambda v, c: idx[odd(v)] * k + c + 1
    cl = set()
    for m in idx:
        cl.add(tuple(var(m, c) for c in range(k)))
        for a in range(k):
            for b in range(a + 1, k):
                cl.add((-var(m, a), -var(m, b)))
    for x in range(1, N + 1):
        for y in range(x + 1, N + 1 - x):
            z = x + y
            for c in range(k):
                cl.add(tuple(sorted({-var(x, c), -var(y, c), -var(z, c)})))
    return [list(c) for c in cl], var

def cell(a):
    label, k, N, prefix = a
    from pysat.solvers import Cadical153
    cls, var = cnf_odd(k, N)
    ass = sorted({var(v, c) for v, c in enumerate(prefix, 1)})
    t0 = time.time()
    with Cadical153(bootstrap_with=cls) as s:
        r = s.solve(assumptions=ass)
        model = set(l for l in s.get_model() if l > 0) if r else None
    out = {"label": label, "N": N, "prefix": "".join(map(str, prefix)), "s": round(time.time() - t0, 2)}
    if not r:
        out["v"] = "UNSAT"; return out
    col = [0] * (N + 1)
    for v in range(1, N + 1):
        col[v] = next(c for c in range(k) if var(v, c) in model)
    ok = ppc.scm.gate(col, k, N)[0] and ppc.scm.is_chain_mono(col, N)
    out["v"] = "SAT" if ok else "SAT_GATE_FAIL"; return out

if __name__ == "__main__":
    k, P = 6, 12
    classes, st = ppc.enumerate_classes(k, P)
    res = {}
    for N in (145, 146):
        with Pool(5) as p:
            cells = list(p.imap_unordered(cell, [(f"class{i}", k, N, c) for i, c in enumerate(classes)]))
        tally = {}
        for c in cells: tally[c["v"]] = tally.get(c["v"], 0) + 1
        sat = [c["prefix"] for c in cells if c["v"] == "SAT"]
        print(N, tally, "SAT classes:", sat, "max s:", max(c["s"] for c in cells), flush=True)
        res[N] = {"tally": tally, "sat": sat, "cells": cells}
    w = json.load(open(ppc.WITNESS, encoding="utf-8"))
    print("witness class:", "".join(map(str, ppc.canon([0] + w["witness"][:P], P))))
    (ppc.OUT / "c015_odd_encoding_P12.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
