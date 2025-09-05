# -*- coding: utf-8 -*-
import os, sys
from typing import Optional, Tuple, Any, Dict, List
from settings import (
    ORACLE_USER,
    ORACLE_PASSWORD,
    ORACLE_DSN,
    ORACLE_SQL_SN,
    SQL_MAX_ROWS,
    augment_easy_connect_with_timeout,
)
from sql_utils import jsonable, normalize_sql_user_friendly


# Optional：自動載入 instantclient（打包後可 Thick）
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


def call_sql_by_sn(sn: str) -> Optional[Tuple[Any, Any, Any]]:
    try:
        import oracledb
    except Exception as e:
        raise RuntimeError("未安裝 oracledb，請先 pip install oracledb") from e
    dsn = augment_easy_connect_with_timeout(ORACLE_DSN, timeout=20)
    with oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(ORACLE_SQL_SN, sn=sn)
            return cur.fetchone()


def call_sql_raw(
    sql_text: str, max_rows: int = SQL_MAX_ROWS, params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    try:
        import oracledb
    except Exception as e:
        raise RuntimeError("未安裝 oracledb，請先 pip install oracledb") from e
    if not sql_text.strip():
        raise RuntimeError("請輸入 SQL 指令")
    sql_norm = normalize_sql_user_friendly(sql_text)
    import re

    if not re.match(r"(?is)^\s*select\b", sql_norm):
        raise RuntimeError(
            "僅允許 SELECT 查詢（讀取），請勿使用 INSERT/UPDATE/DELETE/DDL"
        )

    wrapped = f"SELECT * FROM ({sql_norm}) WHERE ROWNUM <= :max_rows"
    user_params = dict(params or {})
    user_params.pop("max_rows", None)
    binds = {**user_params, "max_rows": int(max_rows)}

    dsn = augment_easy_connect_with_timeout(ORACLE_DSN, timeout=20)
    with oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(wrapped, binds)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall()
            data = [{cols[i]: jsonable(r[i]) for i in range(len(cols))} for r in rows]
            return {
                "columns": cols,
                "rows": data,
                "rowcount": len(data),
                "binds": binds,
            }
