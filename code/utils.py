"""Shared utilities for the SMS research pipeline."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def git_sha() -> str:
    """Return the current HEAD commit SHA, or 'unknown' if not in a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def write_with_meta(
    target_path: str | Path,
    script: str,
    inputs: list[str],
    seed: int = 42,
) -> Path:
    """Write a sibling .meta.json next to *target_path*.

    The meta file records provenance so any artifact can be traced back to the
    code and data that produced it.

    Parameters
    ----------
    target_path : str | Path
        Path to the data file that was (or will be) written.
    script : str
        Name of the script that generated the file.
    inputs : list[str]
        Paths or identifiers of input data consumed.
    seed : int
        Random seed used (default 42).

    Returns
    -------
    Path
        Path to the written .meta.json file.
    """
    target_path = Path(target_path)
    meta = {
        "generated_by": "erp2-sms pipeline",
        "script": script,
        "inputs": inputs,
        "git_sha": git_sha(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
    }
    meta_path = target_path.with_suffix(target_path.suffix + ".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta_path
