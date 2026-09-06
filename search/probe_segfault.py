"""РАЗЛИЧИТЕЛЬ падения chain_lift: дефект СВЯЗКИ или дефект ИДЕИ подъёма?

ЗАЧЕМ.  06-09 20:00 инкрементальный подъём (`search/chain_lift.py`) дважды упал
на участке N~143-145 с ненулевым кодом, печатая перед смертью правдоподобную
полную лестницу. Я объяснила падение гонкой потока-таймера с солвером —
объяснение было связным, механизм назван поимённо — и мутант его опроверг:
таймер убран, поток исчез, упало снова. Причина осталась НЕ УСТАНОВЛЕННОЙ, а
диагноз всё это время звучал как знание (#3996: внутренняя связность объяснения
засчитывается за его связь с предметом).

ЧТО ЭТОТ ПРИБОР РАЗЛИЧАЕТ.  Ровно две вещи, и он обязан уметь показать обе:
  (S) ДЕФЕКТ СВЯЗКИ — падает конкретная реализация солвера/обёртки. Тогда
      другой солвер на ТЕХ ЖЕ клаузах поднимается выше точки падения.
  (I) ДЕФЕКТ ИДЕИ — падает сам способ (инкрементальное дописывание клауз после
      бюджетного solve, снятие модели каждой ступени). Тогда падают ВСЕ
      солверы примерно на одном участке, и различие надо искать в способе
      вызова, а не в имени библиотеки.
Третий исход тоже возможен и его нельзя выдавить в первые два: НИКТО не упал —
значит падение зависит от чего-то, что этот прибор не воспроизводит, и оно
остаётся неустановленным (а не «исправленным»).

КАК УСТРОЕН.  Каждая ячейка матрицы — ОТДЕЛЬНЫЙ процесс: падение ребёнка обязано
быть данными, а не смертью замера. Ребёнок пишет живой след после каждой ступени
(#3961 на себе: собственный ноль от падения и нормальный конец дают один экран,
поэтому «докуда дошёл» читается с диска, а не из stdout умершего).

ПОЛОЖИТЕЛЬНЫЙ КОНТРОЛЬ.  Ячейка `--crash-now` намеренно роняет ребёнка на N=50.
Без неё «никто не упал» неотличимо от «драйвер не умеет видеть падение»: у
матрицы, где ни одна ячейка не красная, нет доказанного красного состояния.

ЗНАМЕНАТЕЛЬ.  Печатается число ячеек, дошедших до `--hi` без вердикта по
падению (истёк настенный предохранитель): такая ячейка НЕ является «прошла» —
она не дошла до участка, где падало (#4101: списочная выдача не умеет показать
собственный пропуск, поэтому остаток называется поимённо).

Run:  python search/probe_segfault.py                     (полная матрица)
      python search/probe_segfault.py --worker --solver Glucose3 --method limited
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))
sys.path.insert(0, str(_HERE))

from chain_lift import clauses_for_element, var  # noqa: E402  ТОТ ЖЕ энкодер

OUT_DIR = _HERE.parent / "out" / "segfault_probe"

# Имя -> класс берём по строке, чтобы отсутствие солвера в сборке было ДАННЫМИ
# (ячейка "не собран"), а не падением драйвера.
SOLVERS = ["Minisat22", "MinisatGH", "Glucose3", "Glucose42",
           "Cadical153", "Mergesat3", "Maplesat"]


def worker(solver_name: str, k: int, hi: int, budget: int, method: str,
           model_every: bool, wall: float, live_path: str, crash_now: int) -> int:
    from pysat.solvers import Solver

    s = Solver(name=solver_name.lower())
    s.add_clause([var(1, 0, k)])
    t0 = time.time()
    reached, last_sat, stop_why = 0, None, "hi reached"

    for n in range(1, hi + 1):
        for cl in clauses_for_element(n, k, chain=True, conflicts=True):
            s.add_clause(cl)
        if time.time() - t0 > wall:
            stop_why = "wall guard (НЕ вердикт: до участка падения не дошли)"
            break
        if crash_now and n == crash_now:
            # ПОЛОЖИТЕЛЬНЫЙ КОНТРОЛЬ: доказать, что драйвер видит смерть ребёнка.
            _write_live(live_path, solver_name, method, n, last_sat, "crash-now armed")
            import ctypes
            ctypes.string_at(0)
        if method == "limited":
            s.conf_budget(int(budget))
            res = s.solve_limited()
        else:
            res = s.solve()
        reached = n
        if res is True:
            last_sat = n
            if model_every or n == hi:
                s.get_model()
        elif res is False:
            stop_why = f"UNSAT at {n}"
            break
        else:
            stop_why = f"UNKNOWN at {n} (бюджет {budget})"
            break
        _write_live(live_path, solver_name, method, reached, last_sat, "running")

    _write_live(live_path, solver_name, method, reached, last_sat, stop_why,
                done=True, elapsed=round(time.time() - t0, 2))
    s.delete()
    print(f"DONE {solver_name}/{method} reached={reached} last_sat={last_sat} why={stop_why}")
    return 0


def _write_live(path, solver, method, reached, last_sat, why, done=False, elapsed=None):
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"solver": solver, "method": method, "reached_N": reached,
                       "last_sat": last_sat, "why": why, "done": done,
                       "elapsed_s": elapsed}, fh, ensure_ascii=False)
    except OSError:
        pass


def run_cell(label: str, argv: List[str], hi: int) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    live = OUT_DIR / f"{label}.live.json"
    if live.exists():
        live.unlink()
    cmd = [sys.executable, str(_HERE / "probe_segfault.py"), "--worker",
           "--live", str(live)] + argv
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    dt = round(time.time() - t0, 1)
    state = {}
    if live.exists():
        try:
            state = json.loads(live.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            state = {}
    tail = (p.stderr or "").strip().splitlines()
    return {"label": label, "rc": p.returncode, "s": dt,
            "reached_N": state.get("reached_N"), "last_sat": state.get("last_sat"),
            "why": state.get("why"), "child_done": bool(state.get("done")),
            "stderr_tail": tail[-1] if tail else "",
            "hi": hi}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--hi", type=int, default=160)
    ap.add_argument("--budget", type=int, default=200000)
    ap.add_argument("--wall", type=float, default=120.0)
    # ЗАМЕРЕНО 06-09 22:00, первым же прогоном. Ось СОЛВЕР в режиме `limited`
    # НИЧЕГО НЕ РАЗЛИЧИЛА: все шесть ячеек честно вернули rc=0, но встали на
    # N=135..144 по исчерпании бюджета, то есть НЕ ДОШЛИ до участка падения
    # (N~143-145). Зелёная строка означала «не проверялось», и отличить это от
    # «прошло» можно было ровно по одному месту — по знаменателю в ИТОГЕ
    # (#4101). Поэтому режим оси вынесен в параметр: различитель обязан уметь
    # встать туда, где предмет падает, иначе он меряет собственную дистанцию.
    ap.add_argument("--axis-method", choices=["limited", "plain"], default="limited",
                    help="метод для оси СОЛВЕР; plain = без бюджета, доходит до участка падения")
    ap.add_argument("--solvers", default="", help="через запятую; пусто = весь список")
    ap.add_argument("--skip-method-axis", action="store_true")
    ap.add_argument("--tag", default="", help="суффикс имени отчёта: прогоны НЕ затирают друг друга")
    args = ap.parse_args()
    solvers = [s for s in args.solvers.split(",") if s] or SOLVERS

    base = ["--k", str(args.k), "--hi", str(args.hi), "--budget", str(args.budget),
            "--wall", str(args.wall)]
    cells = []

    print("=== РАЗЛИЧИТЕЛЬ падения подъёма: связка или идея? ===\n")
    print("0. Положительный контроль драйвера (ребёнок обязан умереть на N=50):")
    c = run_cell("poscontrol", base + ["--solver", "Minisat22", "--method", "limited",
                                       "--model-every", "--crash-now", "50"], args.hi)
    cells.append(c)
    driver_sees_death = (c["rc"] != 0) and (c["reached_N"] or 0) >= 40
    print(f"   rc={c['rc']} reached={c['reached_N']}  -> "
          f"{'драйвер ВИДИТ смерть ребёнка' if driver_sees_death else 'ПРИБОР СЛЕП: матрица ниже недействительна'}")
    if not driver_sees_death:
        json.dump({"driver_sees_death": False, "cells": cells},
                  open(OUT_DIR / "report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return 1

    print("\n1. Ось СОЛВЕР (метод и способ снятия модели одинаковы):")
    for name in solvers:
        c = run_cell(f"solver_{name}", base + ["--solver", name, "--method", args.axis_method,
                                               "--model-every"], args.hi)
        cells.append(c)
        print(f"   {name:<11} rc={c['rc']:<12} reached={str(c['reached_N']):<5} "
              f"last_sat={str(c['last_sat']):<5} [{c['s']}s] {c['why'] or c['stderr_tail'][:60]}")

    print("\n2. Ось СПОСОБ ВЫЗОВА (солвер один — тот, что падал):")
    method_cells = [] if args.skip_method_axis else [
        ("limited_modelevery", ["--method", "limited", "--model-every"]),
        ("limited_nomodel", ["--method", "limited"]),
        ("plain_modelevery", ["--method", "plain", "--model-every"])]
    for label, extra in method_cells:
        c = run_cell(f"m22_{label}", base + ["--solver", "Minisat22"] + extra, args.hi)
        cells.append(c)
        print(f"   {label:<20} rc={c['rc']:<12} reached={str(c['reached_N']):<5} "
              f"[{c['s']}s] {c['why'] or c['stderr_tail'][:60]}")

    crashed = [c for c in cells if c["label"] != "poscontrol" and c["rc"] != 0]
    survived = [c for c in cells if c["label"] != "poscontrol" and c["rc"] == 0]
    # ЗНАМЕНАТЕЛЬ: «дошёл до hi без падения» и «не дошёл до участка падения» —
    # РАЗНЫЕ исходы, второй не является прохождением.
    short = [c for c in survived if (c["reached_N"] or 0) < 145]
    print(f"\nИТОГ: упало {len(crashed)} из {len(cells)-1}; "
          f"выжило {len(survived)}, из них НЕ ДОШЛИ до N=145: {len(short)}"
          + (f" ({', '.join(c['label'] for c in short)})" if short else ""))
    if crashed:
        print("Упавшие поимённо: " + ", ".join(f"{c['label']}@N={c['reached_N']}" for c in crashed))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rep = OUT_DIR / f"report{('_' + args.tag) if args.tag else ''}.json"
    json.dump({"driver_sees_death": True, "k": args.k, "hi": args.hi,
               "axis_method": args.axis_method,
               "budget": args.budget, "cells": cells},
              open(rep, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\nЧек: {rep}")
    return 0


if __name__ == "__main__":
    if "--worker" in sys.argv:
        ap = argparse.ArgumentParser()
        ap.add_argument("--worker", action="store_true")
        ap.add_argument("--solver", required=True)
        ap.add_argument("--k", type=int, default=6)
        ap.add_argument("--hi", type=int, default=160)
        ap.add_argument("--budget", type=int, default=200000)
        ap.add_argument("--method", choices=["limited", "plain"], default="limited")
        ap.add_argument("--model-every", action="store_true")
        ap.add_argument("--wall", type=float, default=120.0)
        ap.add_argument("--live", default="")
        ap.add_argument("--crash-now", type=int, default=0)
        a = ap.parse_args()
        sys.exit(worker(a.solver, a.k, a.hi, a.budget, a.method,
                        a.model_every, a.wall, a.live, a.crash_now))
    sys.exit(main())
