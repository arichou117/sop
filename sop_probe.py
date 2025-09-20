# -*- coding: utf-8 -*-
"""
入口：支援 CLI 與 GUI。新增 --out_csv 以在 SQL 模式匯出 CSV。
"""
import json
import argparse
import csv, os

from sql_utils import parse_bind_params
from settings import SQL_MAX_ROWS
from api_client import call_api, summarize_api_payload
from db_oracle import call_sql_by_sn, call_sql_raw
try:
    from db_mysql import call_sql_raw_mysql
    _HAS_MYSQL = True
except Exception:
    _HAS_MYSQL = False
from ui_tk import App, require_login


def _write_csv(columns, rows, path):
    """
    將 SQL 結果寫出為 CSV
    - columns: List[str]
    - rows: List[Dict[str,Any]]
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([str(c) for c in (columns or [])])
        for r in rows or []:
            w.writerow(["" if r.get(c) is None else r.get(c) for c in (columns or [])])


def main():
    p = argparse.ArgumentParser(
        description="SOP 資訊檢視工具（API / SQL by SN / SQL Raw）"
    )
    p.add_argument("--sn", help="序號（可帶或不帶大括號）")
    p.add_argument(
        "--mode", choices=["api", "sql_sn", "sql_raw", "mysql_raw"], default="api"
    )
    p.add_argument("--sql", help="直接執行的 SELECT 指令（僅 SQL Raw 模式）")
    p.add_argument("--params", help='綁定參數，JSON 或 "k=v,k2=v2"', default="")
    p.add_argument(
        "--max_rows", type=int, default=SQL_MAX_ROWS, help="SQL 指令最大筆數"
    )
    p.add_argument("--out_csv", help="將結果匯出為 CSV 檔案（僅 SQL 模式）")
    p.add_argument("--cli", action="store_true", help="命令列輸出（不啟動 GUI）")
    args = p.parse_args()

    # 新增：CLI 模式下的 MySQL Raw 支援（獨立處理以避免影響原邏輯）
    if getattr(args, "cli", False) and args.mode == "mysql_raw":
        if not args.sql:
            print('請用 --sql "SELECT ..." 提供查詢指令')
            return
        if not _HAS_MYSQL:
            print("未找到 MySQL 支援，請安裝 mysql-connector-python 或 PyMySQL 後再試。")
            return
        binds = parse_bind_params(args.params)
        res = call_sql_raw_mysql(args.sql, max_rows=args.max_rows, params=binds)
        if args.out_csv:
            _write_csv(res.get("columns", []), res.get("rows", []), args.out_csv)
            print(f"CSV 已輸出到 {os.path.abspath(args.out_csv)}")
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    if args.cli:
        # SQL Raw（或只要有帶 --sql 就視為 Raw）
        if args.mode == "sql_raw" or args.sql:
            if not args.sql:
                print('請用 --sql "SELECT ..." 提供查詢指令')
                return
            binds = parse_bind_params(args.params)
            res = call_sql_raw(args.sql, max_rows=args.max_rows, params=binds)
            if args.out_csv:
                _write_csv(res.get("columns", []), res.get("rows", []), args.out_csv)
                print(f"CSV 已輸出：{os.path.abspath(args.out_csv)}")
            print(json.dumps(res, ensure_ascii=False, indent=2))
            return

        # API
        if args.mode == "api":
            if not args.sn:
                print("請用 --sn 輸入序號")
                return
            payload = call_api(args.sn.strip("{}"))
            print(summarize_api_payload(payload))
            print("\n完整 JSON")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        # SQL by SN
        if args.mode == "sql_sn":
            if not args.sn:
                print("請用 --sn 輸入序號")
                return
            row = call_sql_by_sn(args.sn.strip("{}"))
            if row:
                out = {"MODEL_NAME": row[0], "SHIPPING_SN": row[1], "DATA1": row[2]}
                if args.out_csv:
                    _write_csv(
                        ["MODEL_NAME", "SHIPPING_SN", "DATA1"], [out], args.out_csv
                    )
                    print(f"CSV 已輸出：{os.path.abspath(args.out_csv)}")
                print(json.dumps(out, ensure_ascii=False, indent=2))
            else:
                print("查無資料")
            return

    # 預設：GUI（需要登入）
    if not require_login():
        return
    App().mainloop()


if __name__ == "__main__":
    main()
