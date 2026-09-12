"""C-008: смерть от НАКОПЛЕННОГО состояния инкрементального солвера или от экземпляра N=144?

ОТКУДА.  C-007 (13-09) сузил место: rc=3221225477 приходит на N=144 в фазе
`solve` (мой энкодер, add_clause и get_model сняты). Осталась пара:
  (N) ЭКЗЕМПЛЯР — набор клауз до 144 сам по себе роняет minisat. Тогда свежий
      солвер, получивший ТОТ ЖЕ набор разом, тоже умрёт.
  (A) НАКОПЛЕНИЕ — умирает солвер, переживший 143 инкрементальных solve
      (выученные клаузы, restarts, внутренние структуры). Тогда свежий пройдёт.

ПОЛОЖИТЕЛЬНЫЙ КОНТРОЛЬ.  Ячейка `--crash` роняет ребёнка жёстко прямо перед
solve на том же наборе. Без неё «свежий не упал» неотличимо от «драйвер не
умеет видеть эту смерть» (#3734).

ЗНАМЕНАТЕЛЬ.  Если свежий вернул UNKNOWN по бюджету — это НЕ «прошёл»: он не
досидел до того места, где инкрементальный умирал. Печатается отдельно.

Run:  python search/probe_fresh_solver.py --n 144
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))
sys.path.insert(0, str(_HERE))

from chain_lift import clauses_for_element, var  # noqa: E402  ТОТ ЖЕ энкодер

OUT_DIR = _HERE.parent / "out" / "fresh_solver"


def _mark(path, payload):
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
    except OSError:
        pass


def worker(n, k, budget, live, crash):
    from pysat.solvers import Solver
    t0 = time.time()
    s = Solver(name="minisat22")
    s.add_clause([var(1, 0, k)])
    total = 0
    for i in range(1, n + 1):
        for cl in clauses_for_element(i, k, chain=True, conflicts=True):
            s.add_clause(cl)
            total += 1
    _mark(live, {"n": n, "phase": "loaded", "clauses": total,
                 "elapsed_s": round(time.time() - t0, 2)})
    if crash:
        import faulthandler
        faulthandler._sigsegv()
    s.conf_budget(int(budget))
    res = s.solve_limited()
    _mark(live, {"n": n, "phase": "solved", "clauses": total, "res": str(res),
                 "elapsed_s": round(time.time() - t0, 2)})
    s.delete()
    print(f"DONE n={n} res={res}")
    return 0


def run_cell(label, argv, timeout):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    live = OUT_DIR / f"{label}.live.json"
    if live.exists():
        live.unlink()
    cmd = [sys.executable, str(_HERE / "probe_fresh_solver.py"), "--worker",
           "--live", str(live)] + argv
    t0 = time.time()
    try:
        rc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        rc = "timeout"
    st = {}
    if live.exists():
        try:
            st = json.loads(live.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            st = {}
    return {"label": label, "rc": rc, "s": round(time.time() - t0, 1), **st}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=144)
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--budget", type=int, default=5_000_000)
    ap.add_argument("--cell-timeout", type=float, default=600.0)
    # Отдельное имя на прогон: C-009 на 100M затёр бы отчёт C-008 (так и было 13-09 04:00).
    ap.add_argument("--report", default="report.json")
    args = ap.parse_args()
    base = ["--n", str(args.n), "--k", str(args.k), "--budget", str(args.budget)]

    # Номер кандидата сюда не зашивать: прогон C-009 печатал «C-008» (13-09 06:00).
    print(f"=== свежий солвер на том же наборе (отчёт {args.report}) ===\n")
    c0 = run_cell("poscontrol", base + ["--crash"], 300.0)
    sees = c0["rc"] not in (0, "timeout") and c0.get("phase") == "loaded"
    print(f"0. контроль: rc={c0['rc']} phase={c0.get('phase')} -> "
          f"{'драйвер ВИДИТ смерть на этом наборе' if sees else 'ПРИБОР СЛЕП'}")
    if not sees:
        return 1

    c = run_cell("fresh", base, args.cell_timeout)
    print(f"1. свежий:   rc={c['rc']} phase={c.get('phase')} res={c.get('res')} "
          f"clauses={c.get('clauses')} [{c['s']}s]")
    if c["rc"] == "timeout":
        # Третья графа. Раньше "timeout" != 0 читался как смерть => фантомное (N):
        # показано живьём 13-09 04:00 на --cell-timeout 5 (тот же дефект, что
        # probe_segfault чинил в 5975fa0 и который сам сюда не доехал, #4238).
        print("   ЧТЕНИЕ: БЕЗ ВЕРДИКТА — ячейку убил предохранитель драйвера; ни (N), ни (A).")
    elif c["rc"] != 0:
        print("   ЧТЕНИЕ: (N) умирает и свежий — дело в ЭКЗЕМПЛЯРЕ набора, не в накоплении.")
    elif str(c.get("res")) == "None":
        print("   ЧТЕНИЕ: свежий вернул UNKNOWN по бюджету — НЕ «прошёл», до места не досидел.")
    else:
        # Один прогон, один сид: «накопленные клаузы» против «конкретного пути поиска»
        # этим НЕ различены — печатать только то, что снято (формула сама не убивает).
        print("   ЧТЕНИЕ: (A) свежий прошёл — экземпляр набора сам солвер НЕ убивает; нужна история "
              "инкрементальных вызовов (клаузы или путь поиска — этим прогоном не различены).")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json.dump({"args": vars(args), "poscontrol": c0, "fresh": c},
              open(OUT_DIR / args.report, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    if "--worker" in sys.argv:
        wp = argparse.ArgumentParser()
        wp.add_argument("--worker", action="store_true")
        wp.add_argument("--n", type=int, default=144)
        wp.add_argument("--k", type=int, default=6)
        wp.add_argument("--budget", type=int, default=5_000_000)
        wp.add_argument("--live", default="")
        wp.add_argument("--crash", action="store_true")
        wa = wp.parse_args()
        sys.exit(worker(wa.n, wa.k, wa.budget, wa.live, wa.crash))
    sys.exit(main())
