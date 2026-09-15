"""verdict_line называет ПРИЧИНУ вилки. Это две разные вилки, и следующие шаги у них разные.

15-09: C-004 встал на N=146, исчерпав 50M конфликтов, а вердикт написал
«истёкшее время». На старом коде оба теста красные: причину он не называл никогда.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chain_lift import verdict_line  # noqa: E402


def _fork(why=None):
    row = {"N": 146, "verdict": "UNKNOWN"}
    if why is not None:
        row["why"] = why
    return {"first_unsat": None, "last_sat": 145, "stalled_at": 146, "ladder": [row]}


def test_conflict_budget_fork_is_not_called_elapsed_time():
    line = verdict_line(_fork("conflict budget 50000000"))
    assert "бюджет шага" in line
    assert "истёкшее время" not in line
    assert "по часам" not in line


def test_wall_clock_fork_is_named_as_wall_clock():
    line = verdict_line(_fork("wall-clock stop (НЕ бюджет шага)"))
    assert "по часам" in line
    assert "бюджет шага (" not in line


def test_missing_reason_is_said_not_guessed():
    assert "не записана" in verdict_line(_fork())


def test_closed_value_untouched():
    assert verdict_line({"first_unsat": 46, "last_sat": 45, "stalled_at": None,
                         "ladder": []}) == "M = 45 (SAT 45, UNSAT 46)"
