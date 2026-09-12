"""Run E1.5: read-only inventory of ESP controller, mode, and measurement tags."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.control_signal_audit import audit_decision, esp_tags, signal_inventory

DEFAULT_INPUT = ROOT / "data" / "processed" / "audit_v3" / "df_model_clean_v1.parquet"
DEFAULT_CLASSIFICATION = ROOT / "data" / "processed" / "tag_classification_v1.xlsx"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "control_signal_audit_v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--classification", type=Path, default=DEFAULT_CLASSIFICATION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    source = args.input if args.input.is_absolute() else ROOT / args.input
    classification_path = args.classification if args.classification.is_absolute() else ROOT / args.classification
    output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    classification = pd.read_excel(classification_path)
    tags = esp_tags(classification).tag.tolist()
    source_columns = pd.read_parquet(source, engine="pyarrow").columns
    frame = pd.read_parquet(source, columns=[tag for tag in tags if tag in source_columns])
    before = sha256(source)
    inventory = signal_inventory(frame, classification)
    decision = audit_decision(inventory)
    after = sha256(source)
    inventory.to_csv(output / "esp_signal_inventory.csv", index=False)
    report = {
        "input": {"path": source.as_posix(), "sha256_before": before, "sha256_after": after, "unchanged": before == after},
        "classification": {"path": classification_path.as_posix(), "esp_metadata_rows": len(esp_tags(classification))},
        "inventory": {"present_tags": int(inventory.present.sum()), "missing_tags": int((~inventory.present).sum())},
        "decision": decision,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
