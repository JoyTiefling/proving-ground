"""C-005: падение minisat22 приходит от ДЛИНЫ ОДНОГО вызова solve или от трудности шага?

ЗАЧЕМ.  Инкрементальный подъём `chain_lift.py` умирает ACCESS_VIOLATION на
участке N~142-145 при бюджете 5M конфликтов на шаг. Замер 12-09 снял с обвинения
память (пик RSS 44.8 МиБ на 32 ГБ) и снял привязку к самому N (смерть после 143
против 142 в другом прогоне). Осталась неразличённая пара:

  (V) ДЕФЕКТ ВЫЗОВА — умирает ДЛИННЫЙ одиночный solve: внутреннее состояние
      minisat (база выученных клауз, restarts, heap) переполняет что-то за один
      заход. Тогда ТОТ ЖЕ суммарный бюджет, нарезанный на короткие вызовы,
      проходит дальше.
  (T) ДЕФЕКТ ТРУДНОСТИ — умирает сам шаг N: сколько ни режь, к тому же N
      приходим с тем же накопленным состоянием и падаем. Тогда нарезка не
      спасает, и искать надо в том, что накапливается МЕЖДУ вызовами.

ЧЕГО ПРИБОР НЕ УМЕЕТ (знаменатель, #4101).  Ячейка, вставшая в UNKNOWN раньше
участка падения, НЕ является «прошла» — она до предмета не доехала. Такие
ячейки печатаются отдельным списком поимённо, а не растворяются в «все зелёные».

ПОЛОЖИТЕЛЬНЫЙ КОНТРОЛЬ.  `--crash-now` роняет ребёнка на N=50. Без красного
состояния матрица «никто не упал» неотличима от слепого драйвера (#3734).

КАК ЧИТАТЬ ИСХОД.
  A (5M одним) падает, C (10x500k) доходит дальше  -> (V), дефект вызова.
  A и C падают примерно там же                     -> (T), дефект трудности.
  A не упал вовсе                                  -> падение не воспроизведено
                                                      этим прибором; ничего не
                                                      установлено (не «починено»).

Run:  python search/probe_conflict_budget.py
      python search/probe_conflict_budget.py --worker --mode single --budget 5000000
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import List

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))
sys.path.insert(0, str(_HERE))

from chain_lift import clauses_for_element, var  # noqa: E402  ТОТ ЖЕ энкодер

OUT_DIR = _HERE.parent / "out" / "conflict_budget"


def _write_live(path, payload):
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
    except OSError:
        pass


def worker(solver_name: str, k: int, hi: int, budget: int, mode: str, splits: int,
           wall: float, live_path: str, crash_now: int) -> int:
    from pysat.solvers import Solver

    s = Solver(name=solver_name.lower())
    s.add_clause([var(1, 0, k)])
    t0 = time.time()
    reached, last_sat, stop_why = 0, None, "hi reached"
    chunk = max(1, budget // splits) if mode == "split" else budget

    for n in range(1, hi + 1):
        for cl in clauses_for_element(n, k, chain=True, conflicts=True):
            s.add_clause(cl)
        if time.time() - t0 > wall:
            stop_why = "wall guard (НЕ вердикт: до участка падения не дошли)"
            break
        if crash_now and n == crash_now:
            _write_live(live_path, {"solver": solver_name, "mode": mode,
                                    "reached_N": n, "last_sat": last_sat,
                                    "why": "crash-now armed", "done": False})
            # ЖЁСТКАЯ смерть, а не питоновское исключение: `ctypes.string_at(0)`
            # на Windows перехватывается как OSError и даёт rc=1 — то есть
            # контроль был бы зелёным и у драйвера, который видит только
            # traceback, и ослеп бы ровно на предмете (реальный ACCESS_VIOLATION
            # убивает процесс, rc=3221225477). Контроль обязан воспроизводить
            # ТУ смерть, которую ловит (#3734).
            import faulthandler
            faulthandler._sigsegv()

        if mode == "split":
            # ТОТ ЖЕ суммарный бюджет, но короткими вызовами: различаем длину
            # одного solve от трудности шага. Ранний выход — как только вердикт.
            res, calls = None, 0
            for _ in range(splits):
                s.conf_budget(int(chunk))
                res = s.solve_limited()
                calls += 1
                if res is not None:
                    break
        else:
            s.conf_budget(int(budget))
            res = s.solve_limited()
            calls = 1

        reached = n
        if res is True:
            last_sat = n
            s.get_model()          # как в падавшем прогоне: модель на каждой ступени
        elif res is False:
            stop_why = f"UNSAT at {n}"
            break
        else:
            stop_why = f"UNKNOWN at {n} (суммарный бюджет {budget}, вызовов {calls})"
            break
        _write_live(live_path, {"solver": solver_name, "mode": mode, "reached_N": reached,
                                "last_sat": last_sat, "why": "running", "done": False,
                                "elapsed_s": round(time.time() - t0, 1)})

    _write_live(live_path, {"solver": solver_name, "mode": mode, "reached_N": reached,
                            "last_sat": last_sat, "why": stop_why, "done": True,
                            "elapsed_s": round(time.time() - t0, 2)})
    s.delete()
    print(f"DONE {solver_name}/{mode} reached={reached} last_sat={last_sat} why={stop_why}")
    return 0


def run_cell(label: str, argv: List[str], timeout: float) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    live = OUT_DIR / f"{label}.live.json"
    if live.exists():
        live.unlink()
    cmd = [sys.executable, str(_HERE / "probe_conflict_budget.py"), "--worker",
           "--live", str(live)] + argv
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        rc, err = p.returncode, (p.stderr or "").strip().splitlines()
    except subprocess.TimeoutExpired:
        rc, err = "timeout", []
    dt = round(time.time() - t0, 1)
    state = {}
    if live.exists():
        try:
            state = json.loads(live.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            state = {}
    return {"label": label, "rc": rc, "s": dt,
            "reached_N": state.get("reached_N"), "last_sat": state.get("last_sat"),
            "why": state.get("why"), "child_done": bool(state.get("done")),
            "stderr_tail": err[-1] if err else ""}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--hi", type=int, default=150)
    ap.add_argument("--budget", type=int, default=5_000_000)
    ap.add_argument("--low-budget", type=int, default=2_000_000)
    ap.add_argument("--splits", type=int, default=10)
    ap.add_argument("--wall", type=float, default=600.0)
    ap.add_argument("--cell-timeout", type=float, default=900.0)
    ap.add_argument("--solver", default="Minisat22")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    base = ["--k", str(args.k), "--hi", str(args.hi), "--wall", str(args.wall),
            "--solver", args.solver, "--splits", str(args.splits)]
    cells = []

    print("=== C-005: длина одного solve против трудности шага ===\n")
    print("0. Положительный контроль (ребёнок обязан умереть на N=50):")
    c = run_cell("poscontrol", base + ["--mode", "single", "--budget", "200000",
                                       "--crash-now", "50"], 300.0)
    cells.append(c)
    sees_death = (c["rc"] not in (0, "timeout")) and (c["reached_N"] or 0) >= 40
    print(f"   rc={c['rc']} reached={c['reached_N']}  -> "
          f"{'драйвер ВИДИТ смерть ребёнка' if sees_death else 'ПРИБОР СЛЕП: матрица ниже недействительна'}")
    if not sees_death:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        json.dump({"driver_sees_death": False, "cells": cells},
                  open(OUT_DIR / f"report{args.tag}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        return 1

    plan = [
        ("A_single_5M", ["--mode", "single", "--budget", str(args.budget)]),
        ("B_single_2M", ["--mode", "single", "--budget", str(args.low_budget)]),
        ("C_split_10x", ["--mode", "split", "--budget", str(args.budget)]),
    ]
    print("\n1. Один и тот же N, три способа потратить бюджет:")
    for label, extra in plan:
        c = run_cell(label, base + extra, args.cell_timeout)
        cells.append(c)
        print(f"   {label:<13} rc={str(c['rc']):<12} reached={str(c['reached_N']):<5} "
              f"last_sat={str(c['last_sat']):<5} [{c['s']}s] {c['why'] or c['stderr_tail'][:60]}")

    # ЗНАМЕНАТЕЛЬ: что НЕ доехало до предмета — поимённо, не «все зелёные».
    body = [c for c in cells if c["label"] != "poscontrol"]
    crashed = [c for c in body if c["rc"] not in (0,)]
    not_reached = [c for c in body if c["rc"] == 0 and (c["why"] or "").startswith(("UNKNOWN", "wall"))]
    print("\n2. ИТОГ")
    print(f"   упало:              {[c['label'] for c in crashed] or '—'}")
    print(f"   НЕ доехало до участка (не «прошло»): {[(c['label'], c['why']) for c in not_reached] or '—'}")
    a = next((c for c in body if c["label"] == "A_single_5M"), None)
    cc = next((c for c in body if c["label"] == "C_split_10x"), None)
    if a and cc:
        if a["rc"] != 0 and cc["rc"] == 0 and (cc["reached_N"] or 0) > (a["reached_N"] or 0):
            print("   ЧТЕНИЕ: (V) дефект ДЛИНЫ ОДНОГО ВЫЗОВА — нарезка проходит дальше.")
        elif a["rc"] != 0 and cc["rc"] != 0:
            print("   ЧТЕНИЕ: (T) дефект ТРУДНОСТИ/накопления — нарезка не спасает.")
        elif a["rc"] == 0:
            print("   ЧТЕНИЕ: падение НЕ воспроизведено этим прогоном — ничего не установлено.")
        else:
            print("   ЧТЕНИЕ: смешанный исход, читать ячейки руками.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json.dump({"driver_sees_death": True, "args": vars(args), "cells": cells},
              open(OUT_DIR / f"report{args.tag}.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n   отчёт: out/conflict_budget/report{args.tag}.json")
    return 0


if __name__ == "__main__":
    if "--worker" in sys.argv:
        wp = argparse.ArgumentParser()
        wp.add_argument("--worker", action="store_true")
        wp.add_argument("--solver", default="Minisat22")
        wp.add_argument("--k", type=int, default=6)
        wp.add_argument("--hi", type=int, default=150)
        wp.add_argument("--budget", type=int, default=5_000_000)
        wp.add_argument("--mode", choices=["single", "split"], default="single")
        wp.add_argument("--splits", type=int, default=10)
        wp.add_argument("--wall", type=float, default=600.0)
        wp.add_argument("--live", default="")
        wp.add_argument("--crash-now", type=int, default=0)
        wa = wp.parse_args()
        sys.exit(worker(wa.solver, wa.k, wa.hi, wa.budget, wa.mode, wa.splits,
                        wa.wall, wa.live, wa.crash_now))
    sys.exit(main())
