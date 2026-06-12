# JSON → CSV converter for the uploaded file

import json
import pandas as pd
from pathlib import Path
from typing import Any, Dict, List
from caas_jupyter_tools import display_dataframe_to_user

src = Path("/mnt/data/2025-08-26_19-42-25-803.json")
dst = src.with_suffix(".csv")

def parse_relaxed_json(path: Path) -> List[Dict[str, Any]]:
    """
    Tries multiple strategies to parse a possibly non-standard JSON export:
    1) Standard JSON array.
    2) JSON Lines (one object per line).
    3) Hybrid exports that start with '[' and then have objects per line.
    """
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    # Strategy 1: standard JSON array
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return data
    except Exception:
        pass

    # Strategy 2/3: line-by-line objects
    rows: List[Dict[str, Any]] = []
    # Remove a leading '[' or trailing ']' if present
    if text.startswith("["):
        text = text[1:]
    if text.endswith("]"):
        text = text[:-1]
    for raw_line in text.splitlines():
        line = raw_line.strip().rstrip(",")
        if not line:
            continue
        try:
            obj = json.loads(line)
            rows.append(obj)
            continue
        except Exception:
            # Some exports might be concatenated without commas; try to fix braces
            # Ensure each chunk is a full JSON object by trimming stray characters
            if line.startswith("{") and not line.endswith("}"):
                # attempt to find the last closing brace
                last_brace = line.rfind("}")
                if last_brace != -1:
                    try:
                        obj = json.loads(line[: last_brace + 1])
                        rows.append(obj)
                        continue
                    except Exception:
                        pass
            # Skip lines we truly cannot parse
            continue
    if rows:
        return rows

    raise ValueError("Could not parse the JSON file with relaxed strategies.")

def flatten_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flattens the known schema:
      - 'properties' dict merged into the top-level (no prefix)
      - 'labels' list joined with ';'
      - keep 'id' and 'type'
    Any extra nested dicts will be JSON-encoded strings.
    """
    out: Dict[str, Any] = {}
    out["id"] = rec.get("id")
    # Join labels list
    labels = rec.get("labels")
    if isinstance(labels, list):
        out["labels"] = ";".join(map(str, labels))
    else:
        out["labels"] = labels
    out["type"] = rec.get("type")
    # Merge properties
    props = rec.get("properties", {})
    if isinstance(props, dict):
        for k, v in props.items():
            # normalize lists/dicts to JSON strings
            if isinstance(v, (list, dict)):
                out[k] = json.dumps(v, ensure_ascii=False)
            else:
                out[k] = v
    else:
        out["properties"] = json.dumps(props, ensure_ascii=False)
    # Include any other unexpected top-level keys (except properties/labels we already handled)
    for k, v in rec.items():
        if k in {"id", "labels", "properties", "type"}:
            continue
        if isinstance(v, (list, dict)):
            out[k] = json.dumps(v, ensure_ascii=False)
        else:
            out[k] = v
    return out

# Parse
records = parse_relaxed_json(src)

# Flatten
flat_records = [flatten_record(r) for r in records]

# Build dataframe
df = pd.DataFrame(flat_records)

# Reorder columns: id, type, labels, then the rest alphabetically
front = [c for c in ["id", "type", "labels"] if c in df.columns]
rest = sorted([c for c in df.columns if c not in front])
df = df[front + rest]

# Save CSV
df.to_csv(dst, index=False, encoding="utf-8")

# Show a preview table to the user
preview_rows = min(50, len(df))
display_dataframe_to_user("JSON→CSV Preview (first {} rows)".format(preview_rows), df.head(preview_rows))

dst.as_posix()
