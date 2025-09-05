# -*- coding: utf-8 -*-
"""
入口檔：GUI（預設）或命令列（--cli）
"""
import json, argparse
from sql_utils import parse_bind_params
from settings import SQL_MAX_ROWS
from api_client import call_api, summarize_api_payload
from db_oracle import call_sql_by_sn, call_sql_raw
from ui_tk import App


def main():
    p = argparse.ArgumentParser(
        description="SOP 資料檢視工具（API / SQL by SN / SQL 指令）"
    )
    p.add_argument("--sn", help="序號（不含大括號）")
    p.add_argument("--mode", choices=["api", "sql_sn", "sql_raw"], default="api")
    p.add_argument("--sql", help="直接執行的 SQL 指令（僅 SELECT）")
    p.add_argument("--params", help='命名參數，JSON 或 "k=v,k2=v2"', default="")
    p.add_argument(
        "--max_rows", type=int, default=SQL_MAX_ROWS, help="SQL 指令最大列數"
    )
    p.add_argument("--cli", action="store_true", help="走命令列輸出（不開 GUI）")
    args = p.parse_args()

    if args.cli:
        if args.mode == "sql_raw" or args.sql:
            if not args.sql:
                print('請用 --sql "SELECT ..." 指定查詢指令')
                return
            binds = parse_bind_params(args.params)
            res = call_sql_raw(args.sql, max_rows=args.max_rows, params=binds)
            print(json.dumps(res, ensure_ascii=False, indent=2))
            return

        if args.mode == "api":
            if not args.sn:
                print("請用 --sn 指定序號")
                return
            payload = call_api(args.sn.strip("{}"))
            print(summarize_api_payload(payload))
            print("\n完整 JSON：")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        if args.mode == "sql_sn":
            if not args.sn:
                print("請用 --sn 指定序號")
                return
            row = call_sql_by_sn(args.sn.strip("{}"))
            if row:
                print(
                    json.dumps(
                        {"MODEL_NAME": row[0], "SHIPPING_SN": row[1], "DATA1": row[2]},
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                print("找不到資料")
            return

    # 預設啟動 GUI
    App().mainloop()


if __name__ == "__main__":
    main()
