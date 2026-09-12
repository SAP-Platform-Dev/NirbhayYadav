"""Lightweight run-history tracking for the V4 observation period.

The history is deliberately observational: it records what the existing
pipeline did without changing scoring, thresholds, or recommendations.
"""

import csv
import os
from datetime import datetime, timezone
from typing import Any, Mapping


FIELDS = [
    "timestamp_utc",
    "run_type",
    "candidates",
    "corporate_rejects",
    "analyzed",
    "buy",
    "watchlist",
    "avoid",
    "errors",
    "notes",
]


def summarize_results(results: list[Mapping[str, Any]]) -> dict[str, int]:
    """Summarize scanner results without modifying any decision logic."""
    return {
        "candidates": len(results),
        "corporate_rejects": sum(r.get("status") == "CORPORATE_RISK_REJECT" for r in results),
        "analyzed": sum(r.get("status") == "ANALYZED" for r in results),
        "buy": sum(r.get("verdict") == "BUY" for r in results),
        "watchlist": sum(r.get("verdict") == "WATCHLIST" for r in results),
        "avoid": sum(r.get("verdict") == "AVOID" for r in results),
        "errors": sum(r.get("status") == "ERROR" for r in results),
    }


def record_run(
    run_type: str,
    summary: Mapping[str, Any],
    output_dir: str = "./outputs",
    notes: str = "",
) -> str:
    """Append one observational run record and return its CSV path."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "v4_run_history.csv")
    exists = os.path.exists(path)
    row = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "run_type": run_type,
        "notes": notes,
        **{key: summary.get(key, 0) for key in FIELDS if key not in {"timestamp_utc", "run_type", "notes"}},
    }
    with open(path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(row)
    return path
