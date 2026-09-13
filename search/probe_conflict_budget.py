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
import sys
import time
from pathlib import Path
from typing import List

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))
sys.path.insert(0, str(_HERE))

from chain_lift import clauses_for_element, var  # noqa: E402  ТОТ ЖЕ энкодер
# Смерть / таймаут / след — у предмета, не здесь (NEED-090 (б)).
from probe_common import DIED, NO_VERDICT, SURVIVED, hard_crash  # noqa: E402
from probe_common import run_cell as common_run_cell, write_live as _write_live  # noqa: E402

OUT_DIR = _HERE.parent / "out" / "conflict_budget"


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
            # ЖЁСТКАЯ смерть, а не питоновское исключение (#3734) — через общий носитель.
            hard_crash()

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


def _k(n: int) -> str:
    return f"{n // 1_000_000}M" if n % 1_000_000 == 0 else f"{n // 1000}k"


def cell_labels(args) -> tuple:
    """Имена ячеек — ИЗ АРГУМЕНТОВ. Зашитые под C-005 «5M/2M/10x» подписали
    прогон C-010 (1M/500k/2x) чужими числами прямо в отчёте (#3937)."""
    return (f"A_single_{_k(args.budget)}", f"B_single_{_k(args.low_budget)}",
            f"C_split_{args.splits}x{_k(max(1, args.budget // args.splits))}")


def run_cell(label: str, argv: List[str], timeout: float) -> dict:
    c = common_run_cell(_HERE / "probe_conflict_budget.py", label, argv, timeout, OUT_DIR)
    st = c.pop("live")
    return {**c, "reached_N": st.get("reached_N"), "last_sat": st.get("last_sat"),
            "why": st.get("why"), "child_done": bool(st.get("done"))}


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

    print(f"=== {args.tag or '(без тега)'}: длина одного solve против трудности шага ===\n")
    print("0. Положительный контроль (ребёнок обязан умереть на N=50):")
    c = run_cell("poscontrol", base + ["--mode", "single", "--budget", "200000",
                                       "--crash-now", "50"], 300.0)
    cells.append(c)
    sees_death = c["verdict"] == DIED and (c["reached_N"] or 0) >= 40
    print(f"   rc={c['rc']} reached={c['reached_N']}  -> "
          f"{'драйвер ВИДИТ смерть ребёнка' if sees_death else 'ПРИБОР СЛЕП: матрица ниже недействительна'}")
    if not sees_death:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        json.dump({"driver_sees_death": False, "cells": cells},
                  open(OUT_DIR / f"report{args.tag}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        return 1

    plan = [
        (cell_labels(args)[0], ["--mode", "single", "--budget", str(args.budget)]),
        (cell_labels(args)[1], ["--mode", "single", "--budget", str(args.low_budget)]),
        (cell_labels(args)[2], ["--mode", "split", "--budget", str(args.budget)]),
    ]
    print("\n1. Один и тот же N, три способа потратить бюджет:")
    for label, extra in plan:
        c = run_cell(label, base + extra, args.cell_timeout)
        cells.append(c)
        rcs = "УБИТА ДРАЙВЕРОМ" if c["killed_by_driver"] else str(c["rc"])
        print(f"   {label:<13} rc={rcs:<16} reached={str(c['reached_N']):<5} "
              f"last_sat={str(c['last_sat']):<5} [{c['s']}s] {c['why'] or c['stderr_tail'][:60]}")

    # ЗНАМЕНАТЕЛЬ: что НЕ доехало до предмета — поимённо, не «все зелёные».
    # 13-09 10:00: до переезда на probe_common здесь было `rc not in (0,)`, и
    # "timeout" попадал в УПАВШИЕ — тот же фантом, что починен в probe_segfault
    # и probe_fresh_solver и сюда сам не доехал (#4297). Третья графа — отдельно.
    body = [c for c in cells if c["label"] != "poscontrol"]
    crashed = [c for c in body if c["verdict"] == DIED]
    no_verdict = [c for c in body if c["verdict"] == NO_VERDICT]
    not_reached = [c for c in body if c["verdict"] == SURVIVED
                   and (c["why"] or "").startswith(("UNKNOWN", "wall"))]
    print("\n2. ИТОГ")
    print(f"   упало:              {[c['label'] for c in crashed] or '—'}")
    print(f"   БЕЗ ВЕРДИКТА (убиты драйвером): {[c['label'] for c in no_verdict] or '—'}")
    print(f"   НЕ доехало до участка (не «прошло»): {[(c['label'], c['why']) for c in not_reached] or '—'}")
    a = next((c for c in body if c["label"] == cell_labels(args)[0]), None)
    cc = next((c for c in body if c["label"] == cell_labels(args)[2]), None)
    if a and cc:
        if NO_VERDICT in (a["verdict"], cc["verdict"]):
            print("   ЧТЕНИЕ: ключевая ячейка без вердикта — (V)/(T) этим прогоном не различены.")
        elif a["verdict"] == DIED and cc["verdict"] == SURVIVED and (cc["reached_N"] or 0) > (a["reached_N"] or 0):
            print("   ЧТЕНИЕ: (V) дефект ДЛИНЫ ОДНОГО ВЫЗОВА — нарезка проходит дальше.")
        elif a["verdict"] == DIED and cc["verdict"] == DIED:
            print("   ЧТЕНИЕ: (T) дефект ТРУДНОСТИ/накопления — нарезка не спасает.")
        elif a["verdict"] == SURVIVED:
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
