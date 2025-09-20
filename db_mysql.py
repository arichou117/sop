
import re
from typing import Any, Dict, List

import settings
from settings import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_DB,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_TIMEOUT,
    MYSQL_CHARSET,
    SQL_MAX_ROWS,
)
from sql_utils import jsonable, normalize_sql_user_friendly


def _import_driver():
    """Try mysql-connector-python first, then PyMySQL.
    Returns a tuple (driver_name, module).
    driver_name in {"mysql.connector", "pymysql"}
    """
    try:
        import mysql.connector

        return ("mysql.connector", mysql.connector)
    except Exception:
        pass
    try:
        import pymysql

        return ("pymysql", pymysql)
    except Exception as e:
        raise RuntimeError(
            "缺少 MySQL 驅動；請安裝 mysql-connector-python 或 PyMySQL"
        ) from e


def get_conn():
    drv_name, mod = _import_driver()
    if drv_name == "mysql.connector":

        return mod.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            connection_timeout=MYSQL_TIMEOUT,
            charset=MYSQL_CHARSET,
        )
    else:

        return mod.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            connect_timeout=MYSQL_TIMEOUT,
            charset=MYSQL_CHARSET,
            cursorclass=mod.cursors.DictCursor,
        )


def _strip_trailing_semicolon(s: str) -> str:
    return re.sub(r";\s*\Z", "", s)


def _oracle_binds_to_mysql_pyformat(sql: str) -> str:
    """Convert :name to %(name)s for MySQL drivers using pyformat.
    Avoid :: casts by negative lookbehind.
    """
    return re.sub(r"(?<!:):([A-Za-z_][\w]*)", r"%(\1)s", sql)


def call_sql_raw_mysql(
    sql_text: str, max_rows: int = SQL_MAX_ROWS, params: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    if not sql_text or not sql_text.strip():
        raise RuntimeError("請輸入 SQL 指令")

    sql_norm = normalize_sql_user_friendly(sql_text)
    if not re.match(r"(?is)^\s*select\b", sql_norm):
        raise RuntimeError("僅支援 SELECT 查詢（不支援 DML/DDL）")

    n = int(max_rows)
    binds: Dict[str, Any] = dict(params or {})
    binds.pop("max_rows", None)


    sql_no_sc = _strip_trailing_semicolon(sql_norm)
    if not re.search(r"(?is)\blimit\s+\d+\b", sql_no_sc):
        sql_no_sc = f"{sql_no_sc} LIMIT %(max_rows)s"
        binds["max_rows"] = n


    sql_final = _oracle_binds_to_mysql_pyformat(sql_no_sc)

    drv_name, mod = _import_driver()
    rows: List[Dict[str, Any]] = []
    columns: List[str] = []
    with get_conn() as conn:
        if drv_name == "mysql.connector":
            cur = conn.cursor(dictionary=True)
        else:
            cur = conn.cursor()
        try:
            cur.execute(sql_final, binds)

            if hasattr(cur, "column_names"):
                columns = list(getattr(cur, "column_names"))
            elif cur.description:
                columns = [d[0] for d in cur.description]

            for r in cur.fetchall():
                if isinstance(r, dict):
                    rows.append({k: jsonable(v) for k, v in r.items()})
                else:

                    rows.append({columns[i]: jsonable(r[i]) for i in range(len(columns))})
        finally:
            try:
                cur.close()
            except Exception:
                pass

    return {"columns": columns, "rows": rows, "rowcount": len(rows), "binds": binds}

