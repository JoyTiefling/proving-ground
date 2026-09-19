"""C-016: витнесс M_chain(7) >= N разбором на классы префиксов (P=12, 41 класс), а не в лоб.
Каждый класс — отдельный процесс CaDiCaL с кубом юнит-клаузами и бюджетом по стене.
Первый SAT с прямой проверкой weak-Schur -> запись и стоп. Процессы Idle.
Запуск: python scout_k7_classes.py N BUDGET_S [WORKERS]"""
import ctypes, sys, json, time, pathlib, multiprocessing as mp
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
K = 7; P = 12
OUT = pathlib.Path(__file__).resolve().parent / "out" / "k7_classes.jsonl"

def idle():
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x40)

def valid(col, N):
    return not any(col[x] == col[y] == col[x+y] for x in range(1, N+1) for y in range(x+1, N+1-x))

def job(i, prefix, N, q):
    idle()
    import probe_prefix_cover_odd as po
    from pysat.solvers import Cadical153
    f, var = po.cnf_odd(K, N)
    f = f + [[x] for x in sorted({var(v, c) for v, c in enumerate(prefix, 1)})]
    t0 = time.time()
    with Cadical153(bootstrap_with=f) as s:
        r = s.solve(); m = set(l for l in (s.get_model() or []) if l > 0) if r else None
    rec = {"class": i, "sat": r, "s": round(time.time() - t0, 1)}
    if r:
        col = {}
        for v in range(1, N+1):
            o = v
            while o % 2 == 0: o //= 2
            col[v] = next(c for c in range(K) if var(o, c) in m)
        rec["gate_own"] = valid(col, N); rec["witness"] = [col[v] for v in range(1, N+1)]
    q.put(rec)

if __name__ == "__main__":
    idle()
    import probe_prefix_cover as ppc
    N, budget = int(sys.argv[1]), float(sys.argv[2])
    W = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    classes, _ = ppc.enumerate_classes(K, P)
    print("classes", len(classes), "N", N, "budget", budget, flush=True)
    q = mp.Queue(); todo = list(enumerate(classes)); run = {}; done = []; t_all = time.time(); found = None
    while (todo or run) and not found:
        while todo and len(run) < W:
            i, pr = todo.pop(0); p = mp.Process(target=job, args=(i, pr, N, q)); p.start(); run[i] = (p, time.time())
        time.sleep(0.5)
        while not q.empty():
            rec = q.get(); run.pop(rec["class"])[0].join(); done.append(rec)
            print({k: v for k, v in rec.items() if k != "witness"}, flush=True)
            if rec["sat"] and rec.get("gate_own"): found = rec
        for i, (p, t) in list(run.items()):
            if time.time() - t > budget:
                p.terminate(); p.join(); run.pop(i); done.append({"class": i, "sat": None, "s": budget})
                print({"class": i, "sat": "timeout"}, flush=True)
    for p, _ in run.values(): p.terminate()
    summ = {"N": N, "budget": budget, "tried": len(done), "of": len(classes),
            "unsat": sum(r["sat"] is False for r in done), "timeout": sum(r["sat"] is None for r in done),
            "wall_s": round(time.time() - t_all, 1), "found_class": found and found["class"],
            "witness": found and found["witness"]}
    with open(OUT, "a") as fh: fh.write(json.dumps(summ) + "\n")
    print({k: v for k, v in summ.items() if k != "witness"}, flush=True)
