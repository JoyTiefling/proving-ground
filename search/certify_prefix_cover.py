"""C-015 сертификат: для каждого из 41 класса P=12 — DRUP-доказательство UNSAT
(кодировка B, куб юнит-клаузами, Glucose4) и проверка своим drup_check.
Проверщик и солвер — разные кодовые базы; проверщик прошёл контроли силы."""
import sys, json, time, pathlib
from multiprocessing import Pool
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import probe_prefix_cover as ppc, probe_prefix_cover_odd as po
from drup_check import check, full_proof

def cert(a):
    i, prefix, N = a
    f, var = po.cnf_odd(6, N)
    f = f + [[x] for x in sorted({var(v, c) for v, c in enumerate(prefix, 1)})]
    t0 = time.time(); p = full_proof(f); t1 = time.time()
    ok, info = check(f, p, 6 * len(range(1, N + 1, 2)))
    return {"class": i, "prefix": "".join(map(str, prefix)), "N": N, "accepted": ok,
            "proof_lines": len(p), "solve_s": round(t1 - t0, 1),
            "check_s": round(time.time() - t1, 1), **info}

if __name__ == "__main__":
    only = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else None
    classes, _ = ppc.enumerate_classes(6, 12)
    jobs = [(i, c, 146) for i, c in enumerate(classes) if only is None or i in only]
    out = ppc.OUT / ("c015_drup_certs.json" if only is None else "c015_drup_trial.json")
    res = []
    with Pool(int(__import__("os").environ.get("CERT_WORKERS", "3"))) as pool:
        for r in pool.imap_unordered(cert, jobs):
            res.append(r); out.write_text(json.dumps(res, indent=1), encoding="utf-8")
            print(r, flush=True)
    print("ACCEPTED", sum(r["accepted"] for r in res), "of", len(res), flush=True)
