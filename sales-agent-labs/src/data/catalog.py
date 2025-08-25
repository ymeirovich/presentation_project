from __future__ import annotations
import json, time, hashlib, pathlib
from typing import Dict, Any, List, Optional

CATALOG_PATH = pathlib.Path("out/state/datasets.json")


def _load() -> Dict[str, Any]:
    if not CATALOG_PATH.exists():
        CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CATALOG_PATH.write_text("{}", encoding="utf-8")
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8") or "{}")


def _save(cat: Dict[str, Any]) -> None:
    CATALOG_PATH.write_text(json.dumps(cat, indent=2), encoding="utf-8")


def sha256_of_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def register_dataset(*, file_name: str, sha256: str, sheets: List[str]) -> str:
    cat = _load()
    ds_id = "ds_" + sha256[:8]
    cat[ds_id] = {
        "hash": sha256,
        "file_name": file_name,
        "sheets": sheets,
        "created_at": int(time.time()),
    }
    _save(cat)
    return ds_id


def list_datasets() -> Dict[str, Any]:
    return _load()


def resolve_dataset(hint: Optional[str]) -> Optional[str]:
    """hint can be 'latest', dataset_id, or file_name"""
    cat = _load()
    if not hint:
        return None
    if hint.lower() == "latest":
        if not cat:
            return None
        return max(cat.items(), key=lambda kv: kv[1].get("created_at", 0))[0]
    if hint in cat:
        return hint
    # match by file_name (case-insensitive)
    for ds_id, meta in cat.items():
        if meta.get("file_name", "").lower() == hint.lower():
            return ds_id
    return None


def parquet_path_for(ds_id: str, sheet: Optional[str]) -> pathlib.Path:
    cat = _load()
    meta = cat.get(ds_id) or {}
    sha = meta.get("hash")
    base = pathlib.Path("out/data") / sha
    if sheet:
        p = base / f"{sheet}.parquet"
        if p.exists():
            return p
    # fallback: first parquet in folder
    for cand in base.glob("*.parquet"):
        return cand
    raise FileNotFoundError(f"No parquet found for {ds_id} (sheet={sheet})")
