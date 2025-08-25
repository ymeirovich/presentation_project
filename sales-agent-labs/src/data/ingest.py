from __future__ import annotations
import pathlib, csv
from typing import Dict, Any, List, Tuple
import pandas as pd

from .catalog import sha256_of_file, register_dataset


def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    # light coercion
    for c in df.columns:
        if pd.api.types.is_object_dtype(df[c]):
            # try numeric
            df[c] = pd.to_numeric(df[c], errors="ignore")
    return df


def _schema(df: pd.DataFrame) -> List[Dict[str, str]]:
    out = []
    for c in df.columns:
        d = str(df[c].dtype)
        out.append({"name": c, "dtype": d})
    return out


def _preview_csv(df: pd.DataFrame, rows: int = 10) -> str:
    buf = []
    cols = list(df.columns)
    buf.append(",".join(cols))
    for _, r in df.head(rows).iterrows():
        buf.append(",".join([str(r[c]) for c in cols]))
    return "\n".join(buf)


def ingest_file(raw_path: pathlib.Path, *, original_name: str) -> Dict[str, Any]:
    """
    Save parquet(s) under out/data/<sha256>/<sheet>.parquet
    Return dataset_id + sheets + schema + preview
    """
    raw_path = raw_path.resolve()
    sha = sha256_of_file(raw_path)
    out_dir = pathlib.Path("out/data") / sha
    out_dir.mkdir(parents=True, exist_ok=True)

    sheets: List[str] = []
    schemas: List[Dict[str, Any]] = []
    preview_csv = ""

    if original_name.lower().endswith(".xlsx"):
        xl = pd.ExcelFile(raw_path)
        for sheet in xl.sheet_names:
            df = xl.parse(sheet)
            df = _coerce_types(df)
            df.to_parquet(out_dir / f"{sheet}.parquet")
            sheets.append(sheet)
            schemas.append({"sheet": sheet, "columns": _schema(df)})
        # choose first sheet preview
        if sheets:
            df0 = xl.parse(sheets[0])
            preview_csv = _preview_csv(df0)
    else:
        # treat as CSV
        df = pd.read_csv(raw_path)
        df = _coerce_types(df)
        df.to_parquet(out_dir / "main.parquet")
        sheets = ["main"]
        schemas.append({"sheet": "main", "columns": _schema(df)})
        preview_csv = _preview_csv(df)

    ds_id = register_dataset(file_name=original_name, sha256=sha, sheets=sheets)
    return {
        "dataset_id": ds_id,
        "file_name": original_name,
        "sheets": sheets,
        "schema": schemas,
        "preview_csv": preview_csv,
    }
