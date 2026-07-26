"""Receipt persistence for solver runs — shared by the WS(5) search scripts.

WHY THIS EXISTS
---------------
Every script here can burn tens of minutes of solver time and then produce a
single answer whose only proof-of-work is a hashed receipt. Until 27-07 each
script took `--out` as an *opt-in*: forget the flag and the result is gone,
with a warning printed AFTER the work is already lost.

That cost 2 x 71 minutes on the MUS(35,55) run (26-07, twice). The defect is
not forgetfulness — it is the shape of the tool: expensive work must default
to keeping its result, and any check that a result CAN be written must run
BEFORE the work, not after.

So this module enforces two invariants:
  1. Persisting is the default. Discarding requires an explicit --no-out.
  2. The output path is reserved (and thus proven writable) at startup, with
     an in_progress stub, so a bad path fails in seconds instead of an hour.

Usage in a script:

    import receipts
    ...
    ap.add_argument("--out", type=str, default="",
                    help="receipt path; default = auto under search/out/")
    ap.add_argument("--no-out", action="store_true",
                    help="explicitly discard the receipt (default is to keep it)")
    args = ap.parse_args()

    out_path = receipts.resolve_out(args, __file__, N=args.N, k=args.k)
    receipts.probe_writable(out_path)
    ...                                    # the expensive part
    receipts.write_receipt(out_path, receipt)
"""

import os
import json
import hashlib
import datetime
import sys


def wake_iso():
    """UTC timestamp, seconds precision, Z-suffixed."""
    return (datetime.datetime.now(datetime.timezone.utc)
            .isoformat(timespec="seconds").replace("+00:00", "Z"))


def default_out(script_file, **params):
    """Auto-derived receipt path: search/out/<script-stem>_<k=v pairs>.json

    Params are sorted so the same run always maps to the same file — a rerun
    overwrites its own receipt rather than littering the directory.
    """
    stem = os.path.splitext(os.path.basename(script_file))[0]
    parts = [f"{k}{v}" for k, v in sorted(params.items())]
    name = "_".join([stem] + parts) + ".json"
    d = os.path.join(os.path.dirname(os.path.abspath(script_file)), "out")
    return os.path.join(d, name)


def resolve_out(args, script_file, **params):
    """Single decision point: explicit --out > auto path; --no-out disables."""
    if getattr(args, "no_out", False):
        return ""
    return getattr(args, "out", "") or default_out(script_file, **params)


def probe_writable(out_path):
    """Reserve the path NOW so a bad one fails in seconds, not after an hour."""
    if not out_path:
        sys.stderr.write(
            "  [warn] --no-out given; this run's result will NOT be persisted.\n")
        return
    d = os.path.dirname(out_path) or "."
    os.makedirs(d, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"status": "in_progress", "started": wake_iso()}, f)
    print(f"  receipt path reserved -> {out_path}")


def write_receipt(out_path, receipt):
    """Hash the payload, embed sha16, write. Returns sha16 (or None).

    VERIFIER NOTE — the hash is computed over the receipt WITHOUT its `sha16`
    field, then that field is added to the file. So the written file does not
    hash to its own sha16. To re-verify:

        d = json.load(open(path)); d.pop("sha16")
        hashlib.sha256(json.dumps(d, indent=2, ensure_ascii=False,
                                  sort_keys=True).encode()).hexdigest()[:16]

    This is the original 26-07 behaviour, kept deliberately: receipts already
    cited in the canon (ac1d0b86255578c5, 64f69fb7216a3dce, 80741ca17ac4b316)
    were produced this way, and a prettier scheme would silently invalidate
    every published checksum. Compatibility beats elegance here.
    """
    if not out_path:
        sys.stderr.write("  [warn] --no-out given; result NOT persisted.\n")
        return None
    payload = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True)
    sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    receipt["sha16"] = sha
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False, sort_keys=True)
    print(f"  receipt -> {out_path}  sha16={sha}")
    return sha
