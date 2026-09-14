"""Tests for candidates.py -- the POWER gate (if_true / if_false).

Each test names what would break if the gate were rolled back. The mutant test
(`test_mutant_equal_outcomes_is_red`) fails on the pre-2026-09-14 code, because
that code accepted any open record with a priced discriminator.
"""

from __future__ import annotations

import json
import pathlib

import candidates as C

BASE_OPEN = {
    "id": "C-900",
    "claim": "x holds",
    "discriminator": "run probe.py --n 5; read exit code",
    "cost_min": 5,
    "opened": "2026-09-14",
    "status": "open",
    "if_true": "exit 0, verdict SAT",
    "if_false": "exit 0, verdict UNKNOWN",
}


def _write(tmp_path: pathlib.Path, *recs: dict) -> pathlib.Path:
    p = tmp_path / "c.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n",
                 encoding="utf-8")
    return p


def _errors(tmp_path, *recs):
    return C.load(_write(tmp_path, *recs))[1]


def test_well_formed_open_record_is_green(tmp_path):
    assert _errors(tmp_path, BASE_OPEN) == []


def test_mutant_equal_outcomes_is_red(tmp_path):
    rec = dict(BASE_OPEN, if_false=BASE_OPEN["if_true"])
    errs = _errors(tmp_path, rec)
    assert any("same" in e for e in errs), errs


def test_outcomes_equal_after_folding_are_red(tmp_path):
    # Case, spacing and trailing punctuation must not buy a pass.
    rec = dict(BASE_OPEN, if_true="Exit 0,  verdict SAT.", if_false="exit 0, verdict sat")
    assert any("same" in e for e in _errors(tmp_path, rec))


def test_missing_outcome_on_open_is_red(tmp_path):
    for field in ("if_true", "if_false"):
        rec = {k: v for k, v in BASE_OPEN.items() if k != field}
        errs = _errors(tmp_path, rec)
        assert any(field in e for e in errs), (field, errs)


def test_blank_outcome_on_open_is_red(tmp_path):
    rec = dict(BASE_OPEN, if_false="   ")
    assert any("if_false" in e for e in _errors(tmp_path, rec))


def test_resolved_record_without_outcomes_stays_green(tmp_path):
    # Back-filling predictions after the result would forge pre-registration.
    rec = {k: v for k, v in BASE_OPEN.items() if k not in ("if_true", "if_false")}
    rec.update(status="resolved", resolved="2026-09-14", outcome="SAT at 5")
    assert _errors(tmp_path, rec) == []


def test_next_action_prints_both_outcomes(tmp_path, capsys):
    # The outcomes must be in front of me at the moment of acting, not only in the file.
    C.report(_write(tmp_path, BASE_OPEN), show_all=False)
    out = capsys.readouterr().out
    assert BASE_OPEN["if_true"] in out and BASE_OPEN["if_false"] in out


def test_real_queue_passes_gate():
    records, errors = C.load(C.DEFAULT_PATH)
    assert records, "real queue is empty -- gate would pass vacuously"
    assert errors == []
