
import json, re
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any


def jsonable(v):
    try:
        json.dumps(v)
        return v
    except TypeError:
        if isinstance(v, (datetime, date)):
            return v.isoformat()
        if isinstance(v, Decimal):
            return float(v)
        return str(v)


def normalize_sql_user_friendly(sql_text: str) -> str:
    s = sql_text.strip()
    s = re.sub(r";\s*\Z", "", s)
    s = re.sub(r"(?is)^\s*selec\b", "SELECT", s)
    s = re.sub(
        r"(?is)\bTO[\s_]*NUMBER\s*\(", "TO_NUMBER(", s
    )
    s = re.sub(r"(?is)(\w)\s*_\s*(\w)", r"\1_\2", s)
    s = re.sub(r"[ \t]+", " ", s)
    return s


def parse_bind_params(text: str) -> Dict[str, Any]:
    s = (text or "").strip()
    if not s:
        return {}
    if s.startswith("{") and s.endswith("}"):
        try:
            obj = json.loads(s)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            pass
    params: Dict[str, Any] = {}
    parts = re.split(r"[,\n;]+", s)
    for part in parts:
        if not part.strip() or "=" not in part:
            continue
        k, v = part.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if re.fullmatch(r"-?\d+", v):
            val = int(v)
        elif re.fullmatch(r"-?\d+\.\d*", v):
            val = float(v)
        elif v.lower() in ("true", "false"):
            val = v.lower() == "true"
        elif v.lower() in ("null", "none"):
            val = None
        else:
            val = v
        params[k] = val
    return params
