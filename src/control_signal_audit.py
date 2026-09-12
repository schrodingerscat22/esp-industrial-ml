"""Audit whether archived ESP tags contain a controllable regulator input.

This module deliberately distinguishes a measured electrical response from a
recorded command, setpoint, limit, or controller mode.  It never infers a
setpoint from a measured maximum voltage/current.
"""
from __future__ import annotations

import pandas as pd


EXPLICIT_CONTROLLER_TERMS = ("setpoint", "nastaw", "zad", "limit", "eco", "regulat")
MODE_TERMS = ("tryb", "cykl", "ciag")
MEASUREMENT_CATEGORIES = {"esp_power", "esp_current", "esp_voltage", "esp_spark_rate"}


def esp_tags(classification: pd.DataFrame) -> pd.DataFrame:
    """Return the ESP rows of the versioned tag dictionary with a strict schema."""
    required = {"tag", "description", "unit", "category", "role"}
    missing = sorted(required - set(classification))
    if missing:
        raise KeyError(f"Classification misses {missing}")
    return classification.loc[classification.category.astype("string").str.startswith("esp", na=False)].copy()


def tag_semantics(row: pd.Series) -> str:
    """Classify metadata evidence without turning observations into controls."""
    description = str(row.description).lower()
    if any(term in description for term in EXPLICIT_CONTROLLER_TERMS):
        return "explicit_controller_candidate"
    if any(term in description for term in MODE_TERMS):
        return "mode_candidate"
    if row.category in MEASUREMENT_CATEGORIES:
        return "measured_electrical_response"
    if row.category == "esp_status":
        return "confirmation_or_status"
    if row.category == "esp_rapping":
        return "rapping_command_or_confirmation"
    return "auxiliary_esp_signal"


def signal_inventory(frame: pd.DataFrame, classification: pd.DataFrame) -> pd.DataFrame:
    """Summarise availability and variation of every ESP metadata row in `frame`."""
    rows = []
    for _, item in esp_tags(classification).iterrows():
        tag = item.tag
        present = tag in frame
        values = frame[tag] if present else pd.Series(index=frame.index, dtype="float64")
        valid = values.dropna()
        changed = values.ne(values.shift()).iloc[1:] if len(values) else pd.Series(dtype=bool)
        rows.append({
            "tag": tag, "description": item.description, "unit": item.unit, "category": item.category,
            "role": item.role, "semantic_class": tag_semantics(item), "present": present,
            "coverage_pct": float(values.notna().mean() * 100) if len(values) else 0.0,
            "n_unique": int(valid.nunique()), "changed_pct": float(changed.mean() * 100) if len(changed) else 0.0,
            "top_values": "; ".join(f"{key}:{count}" for key, count in valid.value_counts().head(5).items()),
        })
    return pd.DataFrame(rows)


def audit_decision(inventory: pd.DataFrame) -> dict[str, object]:
    """State only what the archive can support about controller intervention."""
    explicit = inventory.loc[inventory.semantic_class.eq("explicit_controller_candidate") & inventory.present]
    modes = inventory.loc[inventory.semantic_class.eq("mode_candidate") & inventory.present]
    varying_modes = modes.loc[modes.n_unique.gt(1)]
    controller_signal_found = len(explicit) > 0
    return {
        "controller_signal_found": controller_signal_found,
        "decision": "candidate_for_control_effect_study" if controller_signal_found else "no_recorded_controller_input",
        "explicit_controller_tags": explicit.tag.tolist(),
        "mode_tags": modes.tag.tolist(),
        "varying_mode_tags": varying_modes.tag.tolist(),
        "interpretation": (
            "A metadata-labelled controller input is available; its units, direction, and operational use still require installation confirmation."
            if controller_signal_found else
            "The archive has no metadata-labelled setpoint, limit, ECO state, or regulator command. Measured U/I/P and rapping modes cannot identify an energy-saving intervention."
        ),
    }
