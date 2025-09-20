import json, tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
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
    ORACLE2_DSN,
    DEFAULT_DB_ALIAS,
    FALLBACK_DB_ALIAS,
    augment_easy_connect_with_timeout,
)
from db_oracle import call_sql_by_sn, call_sql_raw, current_oracle_mode

try:
    from db_mysql import call_sql_raw_mysql

    _HAS_MYSQL = True
except Exception:
    _HAS_MYSQL = False


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("salvage system（SQL by SN / SQL Raw）")
        self.geometry("1100x860")

        self._last_columns = []
        self._last_rows = []
        self._last_table_text = ""
        self._build()

    def _build(self):
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        row1 = ttk.Frame(frm)
        row1.pack(fill="x", pady=5)
        ttk.Label(row1, text="SN：").pack(side="left")
        self.sn_var = tk.StringVar()
        self.entry_sn = ttk.Entry(row1, textvariable=self.sn_var, font=("Consolas", 14))
        self.entry_sn.pack(side="left", fill="x", expand=True)
        self.entry_sn.focus()

        row2 = ttk.Frame(frm)
        row2.pack(fill="x", pady=5)
        self.mode = tk.StringVar(value="sql_sn")
        ttk.Radiobutton(
            row2,
            text="SQL（以 SN 查詢）",
            value="sql_sn",
            variable=self.mode,
            command=self._update_mode_ui,
        ).pack(side="left", padx=5)
        ttk.Radiobutton(
            row2,
            text="SQL 指令（MySQL）",
            value="mysql_raw",
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
        ttk.Button(row2, text="查詢", command=self.on_query).pack(side="left", padx=10)
        ttk.Button(row2, text="清空", command=self.on_clear).pack(side="left")
        ttk.Button(row2, text="複製結果", command=self.on_copy_table).pack(
            side="left", padx=5
        )
        ttk.Button(row2, text="匯出CSV", command=self.on_export_csv).pack(
            side="left", padx=5
        )
        ttk.Label(row2, text="最大筆數").pack(side="left", padx=(20, 2))
        self.max_rows_var = tk.IntVar(value=SQL_MAX_ROWS)
        self.spin_max = ttk.Spinbox(
            row2, from_=10, to=100000, textvariable=self.max_rows_var, width=8
        )
        self.spin_max.pack(side="left")

        row3 = ttk.Frame(frm)
        row3.pack(fill="both", pady=(8, 5))
        ttk.Label(
            row3,
            text="SQL 指令（限 SELECT；可含 ORDER BY）",
        ).pack(anchor="w")
        self.txt_sql = tk.Text(row3, height=6, wrap="word", font=("Consolas", 12))
        self.txt_sql.pack(fill="x", expand=False, pady=(0, 6))

        self.txt = tk.Text(frm, wrap="word", font=("Consolas", 12), height=10)
        self.txt.pack(fill="both", expand=False, pady=(8, 8))
        self.txt.tag_configure("summary", foreground="blue")
        self.txt.tag_configure("error", foreground="red")
        self.txt.tag_configure("hint", foreground="gray")

        tbl_wrap = ttk.Frame(frm)
        tbl_wrap.pack(fill="both", expand=True, pady=(0, 8))
        self.tbl = ttk.Treeview(tbl_wrap, columns=(), show="headings")
        self.tbl_scroll_y = ttk.Scrollbar(
            tbl_wrap, orient="vertical", command=self.tbl.yview
        )
        self.tbl_scroll_x = ttk.Scrollbar(
            tbl_wrap, orient="horizontal", command=self.tbl.xview
        )
        self.tbl.configure(
            yscrollcommand=self.tbl_scroll_y.set, xscrollcommand=self.tbl_scroll_x.set
        )
        self.tbl.pack(side="left", fill="both", expand=True)
        self.tbl_scroll_y.pack(side="right", fill="y")
        self.tbl_scroll_x.pack(side="bottom", fill="x")

        self.bind("<Return>", lambda e: self.on_query())
        self._update_mode_ui()

    def _insert_hint_header(self):
        mode = current_oracle_mode()
        primary_url = f"https://{API_HOST}{API_PATH.replace('{sn}','<SN>')}"
        backup1 = f"https://{API_HOST}:{API_PORT}{API_PATH.replace('{sn}','<SN>')}"
        backup2 = f"http://{API_HOST}:{API_PORT}{API_PATH.replace('{sn}','<SN>')}"
        dsn_primary = augment_easy_connect_with_timeout(ORACLE_DSN)
        dsn_vnap = (
            augment_easy_connect_with_timeout(ORACLE2_DSN) if ORACLE2_DSN else "<none>"
        )

        info = [
            f"[API] primary={primary_url}",
            f"[API] backups={backup1} | {backup2}  timeout={API_TIMEOUT}s "
            f"use_system_proxy={USE_SYSTEM_PROXY} host_header={'<none>' if not API_HOST_HEADER else API_HOST_HEADER} "
            f"verify={'CA:'+API_CA if API_CA else ('True' if API_VERIFY=='1' else 'False')} "
            f"sni_adapter={'on' if API_HOST_HEADER else 'off'}",
            f"[SQL] default={DEFAULT_DB_ALIAS}  fallback={FALLBACK_DB_ALIAS}  mode={mode}",
            f"[SQL] primary_dsn={dsn_primary}",
            f"[SQL] vnap_dsn={dsn_vnap}",
            f"[SQL RAW] 僅允許 SELECT；優先使用 FETCH FIRST {self.max_rows_var.get()} ROWS ONLY；"
            f"不支援時回退 ROWNUM <= {self.max_rows_var.get()}",
        ]
        self.txt.insert("end", "\n".join(info) + "\n\n", "hint")

    def _update_mode_ui(self):
        m = self.mode.get()
        self.entry_sn.configure(state=("normal" if m == "sql_sn" else "disabled"))
        self.txt_sql.configure(
            state=("normal" if m in ("sql_raw", "mysql_raw") else "disabled")
        )

    def _clear_table(self):
        self.tbl["columns"] = ()
        for i in self.tbl.get_children(""):
            self.tbl.delete(i)

    def _set_table(self, columns, rows, *, max_col_chars=60):

        for i in self.tbl.get_children(""):
            self.tbl.delete(i)
        self.tbl["columns"] = columns or ()

        self._last_columns = list(columns or [])
        self._last_rows = list(rows or [])

        widths = []
        for c in columns or ():
            max_len = len(str(c))
            for r in rows or []:
                val = r.get(c, "")
                if val is None:
                    val = ""
                max_len = max(max_len, len(str(val)))
            max_len = min(max_len, max_col_chars)
            widths.append(max_len * 8)
            self.tbl.heading(c, text=str(c))
            self.tbl.column(c, width=widths[-1], anchor="w", stretch=True)

        for r in rows or []:
            vals = [r.get(c, "") for c in (columns or ())]
            self.tbl.insert("", "end", values=vals)

        lines = []
        if columns:
            lines.append("\t".join(str(c) for c in columns))
            for r in rows or []:
                lines.append("\t".join(str(r.get(c, "")) for c in columns))
        self._last_table_text = "\n".join(lines)

    def on_copy_table(self):
        text = getattr(self, "_last_table_text", "")
        if not text:

            text = self.txt.get("1.0", "end").strip()
            if not text:
                messagebox.showinfo("提示", "沒有可複製的內容")
                return
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("提示", "已複製為 TSV 到剪貼簿")

    def on_clear(self):
        self.txt.delete("1.0", "end")
        self._clear_table()
        self._last_columns = []
        self._last_rows = []
        self._last_table_text = ""

    def on_export_csv(self):
        cols = getattr(self, "_last_columns", [])
        rows = getattr(self, "_last_rows", [])
        if not cols or not rows:
            messagebox.showinfo("提示", "沒有可匯出的表格資料")
            return
        path = filedialog.asksaveasfilename(
            title="匯出 CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            import csv

            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow([str(c) for c in cols])
                for r in rows:
                    w.writerow(["" if r.get(c) is None else r.get(c) for c in cols])
            messagebox.showinfo("提示", "已匯出 CSV")
        except Exception as e:
            messagebox.showerror("錯誤", f"匯出失敗：{e}")

    def on_query(self):
        m = self.mode.get()
        sn = self.sn_var.get().strip().strip("{}")
        sql_raw = self.txt_sql.get("1.0", "end").strip()
        self.on_clear()
        self._insert_hint_header()

        if m == "mysql_raw":
            if not sql_raw:
                messagebox.showinfo("提示", "請輸入 SQL 指令（僅 SELECT）")
                return
            if not _HAS_MYSQL:
                messagebox.showerror(
                    "錯誤",
                    "未找到 MySQL 支援，請安裝 mysql-connector-python 或 PyMySQL。",
                )
                return
            self.txt.insert("end", "查詢中（MySQL）\n\n")
            res = call_sql_raw_mysql(sql_raw, max_rows=self.max_rows_var.get())
            header = (
                f"[ROWS] {res['rowcount']}  [COLUMNS] {', '.join(res['columns'])}\n"
            )
            self.txt.insert("end", header, "summary")
            self._set_table(res.get("columns", []), res.get("rows", []))
            return

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

                    self._set_table(["MODEL_NAME", "SHIPPING_SN", "DATA1"], [out])

                    self.txt.insert(
                        "end",
                        "[ROWS] 1  [COLUMNS] MODEL_NAME, SHIPPING_SN, DATA1\n",
                        "summary",
                    )
                else:
                    self.txt.insert("end", f"查無此 SN：{sn}\n", "error")
            else:
                if not sql_raw:
                    messagebox.showinfo("提示", "請輸入 SQL 指令（限 SELECT）")
                    return
                self.txt.insert("end", "查詢中（SQL 指令）\n\n")
                res = call_sql_raw(sql_raw, max_rows=self.max_rows_var.get())
                header = (
                    f"[ROWS] {res['rowcount']}  [COLUMNS] {', '.join(res['columns'])}\n"
                )
                self.txt.insert("end", header, "summary")

                self._set_table(res.get("columns", []), res.get("rows", []))
        except Exception as e:
            self.txt.insert("end", f"查詢失敗：{e}\n", "error")


def require_login(
    username_expected: str = "vvn", password_expected: str = "vvn"
) -> bool:

    root = tk.Tk()
    root.withdraw()
    try:
        username = simpledialog.askstring("登入", "帳號：", parent=root)
        if username is None:
            return False
        password = simpledialog.askstring("登入", "密碼：", show="*", parent=root)
        if password is None:
            return False
        if username == username_expected and password == password_expected:
            return True
        messagebox.showerror("錯誤", "帳號或密碼錯誤", parent=root)
        return False
    finally:
        try:
            root.destroy()
        except Exception:
            pass


if __name__ == "__main__":

    if require_login():
        App().mainloop()
