"""Общий носитель «ячейка = отдельный процесс» для зондов proving-ground.

ЗАЧЕМ (NEED-090 (б), L3 #4297).  13-09 ночью один и тот же класс дефекта чинился
ПООДИНОЧКЕ в соседних зондах, и каждая починка оставалась в коде того, кто
чинил:
  * `ctypes.string_at(0)` как «жёсткая смерть» — на Windows даёт OSError/rc=1,
    т.е. контроль зелёный у драйвера, который видит только traceback
    (починено в probe_death_phase, через два часа найдено в probe_segfault);
  * «ячейку убил предохранитель драйвера» читалось как СМЕРТЬ ребёнка —
    фантомное падение из собственного нетерпения (починено в probe_segfault
    5975fa0 и probe_fresh_solver 732d16b; при постройке ЭТОГО файла тот же
    дефект найден живым ещё в probe_conflict_budget и probe_death_phase);
  * `TimeoutExpired` вылетал из main и уносил отчёт по всей матрице.
Лечение, лежащее у предмета, а не у вылечившего: здесь одна функция вердикта,
одна жёсткая смерть, один живой след, одна сверка предохранителей. Зонды
только размечают свои ячейки.

ВЕРДИКТ ЯЧЕЙКИ — три графы, не две:
  survived    rc == 0
  died        rc != 0 (любой: и ACCESS_VIOLATION, и питоновский traceback)
  no_verdict  ячейку убил драйвер по времени — НЕ упала и НЕ выжила
`hard` отдельно: смерть без питоновского исключения (rc не 0 и не 1).

САМОПРОВЕРКА.  `python search/probe_common.py --check` — четыре ребёнка
(ok / жёсткая смерть / исключение / вечное зависание) обязаны получить четыре
РАЗНЫХ правильных вердикта, и живой след, записанный перед смертью, обязан
читаться с диска. Мутант «None -> died» (старое `rc != 0`) обязан покраснеть.
"""

import faulthandler
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

ACCESS_VIOLATION = 3221225477          # Windows 0xC0000005, как у настоящего minisat22
SURVIVED, DIED, NO_VERDICT = "survived", "died", "no_verdict"


def hard_crash() -> None:
    """Смерть без исключения — ту, что ловим, а не похожую (#3734).

    13-09 10:00, замер при постройке этого файла: `faulthandler._sigsegv()`,
    которым пользовались ВСЕ четыре зонда, на Windows даёт rc=3 (CRT abort), а
    не 3221225477. Комментарии зондов «контроль воспроизводит ТУ смерть»
    были неверны: драйверы видели смерть, но не ту. `_read_null()` — настоящее
    разыменование нуля в C, rc=3221225477, как у minisat22. `--check` это держит.
    """
    faulthandler._read_null()


def write_live(path, payload: dict) -> None:
    """След пишется НА ДИСК до входа в опасное место: у трупа stdout нет (#3961)."""
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
            fh.flush()
    except OSError:
        pass


def read_live(path) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def verdict_of(rc: Optional[int]) -> str:
    if rc is None:
        return NO_VERDICT
    return SURVIVED if rc == 0 else DIED


def is_hard(rc: Optional[int]) -> bool:
    return rc is not None and rc not in (0, 1)


def fuse_conflict(child_wall: float, driver_timeout: float) -> Optional[str]:
    """Предохранитель драйвера обязан быть больше детского, иначе ребёнок не скажет вердикт никогда."""
    if driver_timeout <= child_wall:
        return (f"ПРИБОР НЕСОГЛАСОВАН: предохранитель драйвера {driver_timeout}s <= "
                f"детского wall {child_wall}s — матрица мерила бы терпение родителя, а не предмет.")
    return None


def run_cell(script: Path, label: str, argv: List[str], timeout: float,
             out_dir: Path) -> dict:
    """Одна ячейка = отдельный процесс. Ни один её исход не имеет права убить драйвер.

    Ребёнок вызывается как `script --worker --live <out_dir/label.live.json> <argv>`.
    Возвращает: label, rc (int | None), verdict, hard, killed_by_driver, s,
    stderr_tail, driver_timeout_s, live (след ребёнка с диска).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    live = out_dir / f"{label}.live.json"
    if live.exists():
        live.unlink()
    cmd = [sys.executable, str(script), "--worker", "--live", str(live)] + list(argv)
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        rc, err = p.returncode, (p.stderr or "")
    except subprocess.TimeoutExpired as e:
        rc = None
        raw = e.stderr or ""
        err = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
    tail = err.strip().splitlines()
    return {"label": label, "rc": rc, "verdict": verdict_of(rc), "hard": is_hard(rc),
            "killed_by_driver": rc is None, "s": round(time.time() - t0, 1),
            "stderr_tail": tail[-1] if tail else "", "driver_timeout_s": timeout,
            "live": read_live(live)}


# --------------------------------------------------------------- самопроверка

def _child(kind: str, live: str) -> int:
    write_live(live, {"kind": kind, "phase": "armed"})
    if kind == "crash":
        hard_crash()
    elif kind == "exc":
        raise RuntimeError("питоновская смерть")
    elif kind == "hang":
        while True:
            time.sleep(3600)
    write_live(live, {"kind": kind, "phase": "done"})
    return 0


def check() -> int:
    import tempfile
    out = Path(tempfile.mkdtemp(prefix="probe_common_"))
    me = Path(__file__).resolve()
    expect = {  # kind -> (verdict, hard, фаза в следе)
        "ok": (SURVIVED, False, "done"),
        "crash": (DIED, True, "armed"),
        "exc": (DIED, False, "armed"),
        "hang": (NO_VERDICT, False, "armed"),
    }
    bad = 0
    for kind, (v, hard, phase) in expect.items():
        c = run_cell(me, f"self_{kind}", ["--kind", kind], 20.0 if kind != "hang" else 4.0, out)
        got = (c["verdict"], c["hard"], c["live"].get("phase"))
        ok = got == (v, hard, phase)
        want = str((v, hard, phase))
        if kind == "crash" and sys.platform == "win32" and c["rc"] != ACCESS_VIOLATION:
            ok = False   # смерть видна, но не ТА (rc=3 от _sigsegv был бы зелёным без этой строки)
            want += f" и rc={ACCESS_VIOLATION} (смерть видна, но не та)"
        bad += not ok
        print(f"  {kind:<6} rc={str(c['rc']):<11} -> {got}  {'ОК' if ok else 'ПРОМАХ, ждала ' + want}")
    if fuse_conflict(120.0, 120.0) is None or fuse_conflict(120.0, 420.0) is not None:
        print("  fuse_conflict: ПРОМАХ")
        bad += 1
    print(f"probe_common --check: {'ЗЕЛЁНЫЙ' if not bad else f'КРАСНЫЙ ({bad})'}")
    return 1 if bad else 0


if __name__ == "__main__":
    if "--worker" in sys.argv:
        import argparse
        wp = argparse.ArgumentParser()
        wp.add_argument("--worker", action="store_true")
        wp.add_argument("--live", default="")
        wp.add_argument("--kind", required=True)
        wa = wp.parse_args()
        sys.exit(_child(wa.kind, wa.live))
    if "--check" in sys.argv:
        sys.exit(check())
    print(__doc__)
