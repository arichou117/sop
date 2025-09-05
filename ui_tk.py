# -*- coding: utf-8 -*-
import json, tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from settings import (
    API_HOST,
    API_PORT,
    API_PATH,
    API_TIMEOUT,
    USE_SYSTEM_PROXY,
    API_HOST_HEADER,
    API_VERIFY,
    API_CA,
    SQL_MAX_ROWS,
    ORACLE_DSN,
    augment_easy_connect_with_timeout,
)
from db_oracle import call_sql_by_sn, call_sql_raw, current_oracle_mode
from sql_utils import parse_bind_params

# ※ GUI 只提供 SQL by SN / SQL 指令；API 僅顯示提示行


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SOP 資料檢視工具（SQL by SN / SQL 指令）")
        self.geometry("980x820")
        self._build()

    def _build(self):
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        # SN
        row1 = ttk.Frame(frm)
        row1.pack(fill="x", pady=5)
        ttk.Label(row1, text="SN：").pack(side="left")
        self.sn_var = tk.StringVar()
        self.entry_sn = ttk.Entry(row1, textvariable=self.sn_var, font=("Consolas", 14))
        self.entry_sn.pack(side="left", fill="x", expand=True)
        self.entry_sn.focus()

        # 模式
        row2 = ttk.Frame(frm)
        row2.pack(fill="x", pady=5)
        self.mode = tk.StringVar(value="sql_sn")
        ttk.Radiobutton(
            row2,
            text="SQL（以 SN 查）",
            value="sql_sn",
            variable=self.mode,
            command=self._update_mode_ui,
        ).pack(side="left", padx=5)
        ttk.Radiobutton(
            row2,
            text="SQL 指令（SELECT）",
            value="sql_raw",
            variable=self.mode,
            command=self._update_mode_ui,
        ).pack(side="left", padx=5)
        ttk.Button(row2, text="執行", command=self.on_query).pack(side="left", padx=10)
        ttk.Button(row2, text="清空", command=self.on_clear).pack(side="left")
        ttk.Label(row2, text="最大列數：").pack(side="left", padx=(20, 2))
        self.max_rows_var = tk.IntVar(value=SQL_MAX_ROWS)
        self.spin_max = ttk.Spinbox(
            row2, from_=10, to=100000, textvariable=self.max_rows_var, width=8
        )
        self.spin_max.pack(side="left")

        # SQL 指令與參數
        row3 = ttk.Frame(frm)
        row3.pack(fill="both", pady=(8, 5))
        ttk.Label(row3, text="SQL 指令（僅 SELECT；可含 ORDER BY；分號可有可無）").pack(
            anchor="w"
        )
        self.txt_sql = tk.Text(row3, height=6, wrap="word", font=("Consolas", 12))
        self.txt_sql.pack(fill="x", expand=False, pady=(0, 6))
        row3b = ttk.Frame(frm)
        row3b.pack(fill="x", pady=(0, 5))
        ttk.Label(
            row3b,
            text="參數（JSON 或 k=v；逗號/分行/分號分隔；例：d1=2025-08-01,d2=2025-09-01）",
        ).pack(anchor="w")
        self.params_var = tk.StringVar()
        self.entry_params = ttk.Entry(
            row3b, textvariable=self.params_var, font=("Consolas", 12)
        )
        self.entry_params.pack(fill="x", expand=True)

        # 輸出
        self.txt = tk.Text(frm, wrap="word", font=("Consolas", 12))
        self.txt.pack(fill="both", expand=True, pady=8)
        self.txt.tag_configure("summary", foreground="blue")
        self.txt.tag_configure("error", foreground="red")
        self.txt.tag_configure("hint", foreground="gray")

        self.bind("<Return>", lambda e: self.on_query())
        self._update_mode_ui()

    def _insert_hint_header(self):
        mode = current_oracle_mode()
        primary_url = f"https://{API_HOST}{API_PATH.replace('{sn}','<SN>')}"
        backup1 = f"https://{API_HOST}:{API_PORT}{API_PATH.replace('{sn}','<SN>')}"
        backup2 = f"http://{API_HOST}:{API_PORT}{API_PATH.replace('{sn}','<SN>')}"
        info = [
            f"[API] primary={primary_url}",
            f"[API] backups={backup1} | {backup2}  timeout={API_TIMEOUT}s "
            f"use_system_proxy={USE_SYSTEM_PROXY} host_header={'<none>' if not API_HOST_HEADER else API_HOST_HEADER} "
            f"verify={'CA:'+API_CA if API_CA else ('True' if API_VERIFY=='1' else 'False')} "
            f"sni_adapter={'on' if API_HOST_HEADER else 'off'}",
            f"[SQL] dsn={augment_easy_connect_with_timeout(ORACLE_DSN)}  mode={mode}",
            f"[SQL RAW] 僅允許 SELECT；將自動套用 ROWNUM <= {self.max_rows_var.get()}",
        ]
        self.txt.insert("end", "\n".join(info) + "\n\n", "hint")

    def _update_mode_ui(self):
        m = self.mode.get()
        self.entry_sn.configure(state=("normal" if m == "sql_sn" else "disabled"))
        self.txt_sql.configure(state=("normal" if m == "sql_raw" else "disabled"))
        self.entry_params.configure(state=("normal" if m == "sql_raw" else "disabled"))

    def on_clear(self):
        self.txt.delete("1.0", "end")

    def on_query(self):
        m = self.mode.get()
        sn = self.sn_var.get().strip().strip("{}")
        sql_raw = self.txt_sql.get("1.0", "end").strip()
        params_text = getattr(self, "params_var", tk.StringVar(value="")).get()
        self.on_clear()
        self._insert_hint_header()
        try:
            if m == "sql_sn":
                if not sn:
                    messagebox.showinfo("提示", "請輸入 SN")
                    return
                self.txt.insert("end", f"查詢中（SQL by SN）：{sn}\n\n")
                row = call_sql_by_sn(sn)
                if row:
                    model, shipping_sn, data1 = row
                    out = {
                        "MODEL_NAME": model,
                        "SHIPPING_SN": shipping_sn,
                        "DATA1": data1,
                        "queried_at": datetime.now().isoformat(timespec="seconds"),
                    }
                    self.txt.insert(
                        "end", json.dumps(out, ensure_ascii=False, indent=2) + "\n"
                    )
                else:
                    self.txt.insert("end", f"找不到 SN：{sn}\n", "error")
            else:
                if not sql_raw:
                    messagebox.showinfo("提示", "請輸入 SQL 指令（僅 SELECT）")
                    return
                binds = parse_bind_params(params_text)
                self.txt.insert("end", f"查詢中（SQL 指令）... 參數: {binds}\n\n")
                res = call_sql_raw(
                    sql_raw, max_rows=self.max_rows_var.get(), params=binds
                )
                header = (
                    f"[ROWS] {res['rowcount']}  [COLUMNS] {', '.join(res['columns'])}\n"
                )
                self.txt.insert("end", header, "summary")
                self.txt.insert(
                    "end", json.dumps(res, ensure_ascii=False, indent=2) + "\n"
                )
        except Exception as e:
            self.txt.insert("end", f"查詢失敗：{e}\n", "error")
