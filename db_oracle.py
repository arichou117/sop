import os, sys
from typing import Optional, Tuple, Any, Dict, List

import settings
from settings import (
    ORACLE_USER,
    ORACLE_PASSWORD,
    ORACLE_DSN,
    ORACLE_SQL_SN,
    SQL_MAX_ROWS,
    augment_easy_connect_with_timeout,
)
from sql_utils import jsonable, normalize_sql_user_friendly


def _maybe_init_oracle():
    try:
        import oracledb  # noqa
    except Exception:
        return
    try:
        base_dir = getattr(sys, "_MEIPASS", os.path.abspath("."))
        for name in (
            "instantclient_23_9",
            "instantclient_23_8",
            "instantclient_23_7",
            "instantclient_23_6",
            "instantclient",
        ):
            p = os.path.join(base_dir, name)
            if os.path.isdir(p):
                import oracledb

                oracledb.init_oracle_client(lib_dir=p)
                break
    except Exception:
        pass


_maybe_init_oracle()


def current_oracle_mode() -> str:
    try:
        import oracledb

        return "Thin" if oracledb.is_thin_mode() else "Thick"
    except Exception:
        return "unavailable"


def _build_dsn(base: str, timeout: int = 20) -> str:
    if not base:
        return ""
    if not base.startswith("//"):
        base = f"//{base}"
    return augment_easy_connect_with_timeout(base, timeout=timeout)


DBS = {
    "primary": {
        "user": ORACLE_USER,
        "password": ORACLE_PASSWORD,
        "dsn": _build_dsn(ORACLE_DSN),
    },
    "vnap": {
        "user": getattr(settings, "ORACLE2_USER", ""),
        "password": getattr(settings, "ORACLE2_PASSWORD", ""),
        "dsn": _build_dsn(getattr(settings, "ORACLE2_DSN", "")),
    },
}

DEFAULT_DB_ALIAS = getattr(settings, "DEFAULT_DB_ALIAS", "primary")
FALLBACK_DB_ALIAS = getattr(settings, "FALLBACK_DB_ALIAS", "vnap")
FALLBACK_TO_VNAP = getattr(settings, "FALLBACK_TO_VNAP", True)


def get_conn(alias: Optional[str] = None):
    try:
        import oracledb
    except Exception as e:
        raise RuntimeError("缺少 oracledb，請先 pip install oracledb") from e
    alias = alias or DEFAULT_DB_ALIAS
    cfg = DBS.get(alias)
    if not cfg or not cfg.get("dsn"):
        raise RuntimeError(f"DB 設定不完整：alias={alias}")
    return oracledb.connect(user=cfg["user"], password=cfg["password"], dsn=cfg["dsn"])


def _exec_once(sql: str, binds: Dict[str, Any], alias: str):
    with get_conn(alias) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, binds)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall() if cur.description else []
            return alias, cols, rows


def _strip_trailing_semicolon(s: str) -> str:
    import re

    return re.sub(r";\s*\Z", "", s)


def _inject_first_rows_hint(s: str, nrows: int) -> str:
    import re

    return re.sub(
        r"(?is)^\s*select\b",
        f"SELECT /*+ FIRST_ROWS({int(nrows)}) */",
        s,
        count=1,
    )


def call_sql_by_sn(sn: str) -> Optional[Tuple[Any, Any, Any]]:
    """
    僅執行 ORACLE_SQL_SN（綁 :sn），固定用 TE（primary）
    """
    _, _, rows = _exec_once(ORACLE_SQL_SN, {"sn": sn}, alias="primary")
    return rows[0] if rows else None


def call_sql_raw(
    sql_text: str,
    max_rows: int = SQL_MAX_ROWS,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    僅允許 SELECT；
    一律優先用 Top‑N（FETCH FIRST N ROWS ONLY + FIRST_ROWS 提示），
    若不支援（如 11g）或失敗，再回退到外包 ROWNUM 寫法。
    固定走 VNAP 連線。
    """
    if not sql_text.strip():
        raise RuntimeError("請輸入 SQL 指令")

    import re

    sql_norm = normalize_sql_user_friendly(sql_text)
    if not re.match(r"(?is)^\s*select\b", sql_norm):
        raise RuntimeError("只允許 SELECT 查詢（不要使用 INSERT/UPDATE/DELETE/DDL）")

    n = int(max_rows)
    user_params = dict(params or {})
    user_params.pop("max_rows", None)

    try:
        sql_with_hint = _inject_first_rows_hint(_strip_trailing_semicolon(sql_norm), n)
        sql_fetch = f"{sql_with_hint} FETCH FIRST {n} ROWS ONLY"
        _, cols, rows = _exec_once(sql_fetch, user_params, alias="vnap")
    except Exception as e:
        s = str(e)

        if any(code in s for code in ("ORA-00933", "ORA-00923", "ORA-32034")):
            wrapped = f"SELECT * FROM ({sql_norm}) WHERE ROWNUM <= :max_rows"
            binds = {**user_params, "max_rows": n}
            _, cols, rows = _exec_once(wrapped, binds, alias="vnap")
        else:
            raise

    data: List[Dict[str, Any]] = [
        {cols[i]: jsonable(r[i]) for i in range(len(cols))} for r in rows
    ]
    return {"columns": cols, "rows": data, "rowcount": len(data), "binds": user_params}
