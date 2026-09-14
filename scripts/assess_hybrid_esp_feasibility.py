"""Read-only signal inventory for the hybrid ESP feasibility study; no training."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import psutil
import scipy
import sklearn

from src.electrical_state import BASE_PROCESS, EXTENDED_PROCESS, FIELDS, RAPPING_TAGS, TARGET
from src.time_analysis import coverage, rapping_starts, time_shift, validate_time


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    source = ROOT / "data/processed/audit_v3/df_model_clean_v1.parquet"
    before = digest(source)
    frame = pd.read_parquet(source)
    validate_time(frame)
    requested = list(dict.fromkeys(
        [TARGET] + list(BASE_PROCESS) + list(EXTENDED_PROCESS)
        + [tag for field in FIELDS for tag in
           (field.voltage, field.current, field.power, field.spark, field.enabled)]
        + list(RAPPING_TAGS)
    ))
    missing = sorted(set(requested) - set(frame))
    rows = []
    for tag in requested:
        if tag not in frame:
            continue
        series = frame[tag]
        previous = time_shift(series, 1)
        valid_pair = np.isfinite(series) & np.isfinite(previous)
        finite = series[np.isfinite(series)]
        rows.append({
            "tag": tag, "finite_n": len(finite), "unique_n": int(finite.nunique()),
            "p05": float(finite.quantile(.05)) if len(finite) else None,
            "median": float(finite.median()) if len(finite) else None,
            "p95": float(finite.quantile(.95)) if len(finite) else None,
            "top3_share": float(finite.value_counts().head(3).sum() / len(finite)) if len(finite) else None,
            "changed_valid_pair_share": float(series[valid_pair].ne(previous[valid_pair]).mean()) if valid_pair.any() else None,
        })

    # Exact structural ambiguity of C_out = C_in * exp(-K), synthetic only.
    # A different unobserved inlet and collection number give identical outlets.
    c_in = 1000.0
    k = 4.6
    other_c_in = 2 * c_in
    other_k = k + np.log(2.0)
    same = np.isclose(c_in * np.exp(-k), other_c_in * np.exp(-other_k), rtol=1e-12)
    if not same:
        raise AssertionError("Synthetic identifiability identity failed")
    after = digest(source)
    if before != after:
        raise RuntimeError("Input changed during feasibility inventory")
    report = {
        "input": {"path": source.relative_to(ROOT).as_posix(), "sha256_before": before,
                  "sha256_after": after, "unchanged": before == after},
        "scope": "Descriptive inventory and synthetic identity only; no model fit or physical calibration",
        "rows": len(frame), "columns": len(frame.columns),
        "calendar_dates_with_rows": int(frame.index.normalize().nunique()),
        "start": str(frame.index.min()), "end": str(frame.index.max()),
        "coverage": coverage(frame[[tag for tag in requested if tag in frame]]),
        "missing_requested_tags": missing, "signals": rows,
        "rapping_start_counts": {tag: int(rapping_starts(frame[tag]).sum()) for tag in RAPPING_TAGS if tag in frame},
        "synthetic_ambiguity": {
            "units": "arbitrary concentration units, not industrial measurements",
            "reference_outlet_both_models": float(c_in * np.exp(-k)),
            "outlet_at_1_1_exposure_model_a": float(c_in * np.exp(-k * 1.1)),
            "outlet_at_1_1_exposure_model_b": float(other_c_in * np.exp(-other_k * 1.1)),
            "same_reference_output": bool(same),
        },
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "pandas": pd.__version__, "scipy": scipy.__version__,
                        "sklearn": sklearn.__version__,
                        "disk_free_GiB": shutil.disk_usage(ROOT).free / 2**30,
                        "available_RAM_GiB": psutil.virtual_memory().available / 2**30,
                        "process_RSS_GiB": psutil.Process().memory_info().rss / 2**30},
    }
    output = ROOT / "data/processed/hybrid_esp_feasibility_20260914"
    output.mkdir(parents=True, exist_ok=True)
    (output / "preflight.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "signals"}, indent=2))


if __name__ == "__main__":
    main()
