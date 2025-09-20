# -*- coding: utf-8 -*-
import os

# --- API 設定（可用環境變數覆蓋） ---
API_HOST = os.getenv("API_HOST", "10.224.24.21")
API_PORT = int(os.getenv("API_PORT", "8080"))
API_PATH = os.getenv("API_PATH", "/FPORTAL/GoodsOut/GetAssetInfoWithParams?sn={sn}")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "20"))
USE_SYSTEM_PROXY = os.getenv("USE_SYSTEM_PROXY", "1") == "1"
API_HOST_HEADER = os.getenv("API_HOST_HEADER", "").strip()
API_VERIFY = os.getenv("API_VERIFY", "0").strip()
API_CA = os.getenv("API_CA", "").strip()

# 內網常見：對 10.* 直連
os.environ.setdefault("NO_PROXY", "10.0.0.0/8,127.0.0.1,localhost")

# --- Oracle（Primary）— 供「以 SN 查」：TE@10.220.130.221:1521/vnsfc ---
ORACLE_USER = os.getenv("ORACLE_USER", "TE")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "B05te")
ORACLE_DSN = os.getenv("ORACLE_DSN", "10.220.130.221:1521/vnsfc")

# 以 SN 查詢的 SQL
ORACLE_SQL_SN = (
    "SELECT MODEL_NAME, SHIPPING_SN, DATA1 FROM sfism4.R109 WHERE SHIPPING_SN = :sn"
)
SQL_MAX_ROWS = int(os.getenv("SQL_MAX_ROWS", "200"))

# --- Oracle（第二組 VNAP）— 供「SQL 指令(SELECT)」：CQYR@10.220.130.100:1903/VNAP ---
ORACLE2_USER = os.getenv("ORACLE2_USER", "CQYR")
ORACLE2_PASSWORD = os.getenv("ORACLE2_PASSWORD", "CQYIELDRATE")
ORACLE2_DSN = os.getenv("ORACLE2_DSN", "//10.220.130.100:1903/VNAP")

# --- 跨 DB 設定（UI 也會顯示用）---
DEFAULT_DB_ALIAS = os.getenv("DEFAULT_DB_ALIAS", "primary")  # primary=TE
FALLBACK_DB_ALIAS = os.getenv("FALLBACK_DB_ALIAS", "vnap")  # vnap=VNAP
FALLBACK_TO_VNAP = os.getenv("FALLBACK_TO_VNAP", "1") == "1"

# --- SQLite（可選：本機快取） ---
LOCAL_DB = os.getenv("LOCAL_DB", "local_cache.db")
CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "6"))


def augment_easy_connect_with_timeout(dsn: str, timeout: int = 20) -> str:
    # 若是 Easy Connect / TNS 字串且尚未帶 connect_timeout，則附加
    if any(sep in dsn for sep in ("/", ":", "@")) and "connect_timeout=" not in dsn:
        joiner = "&" if "?" in dsn else "?"
        return f"{dsn}{joiner}connect_timeout={timeout}"
    return dsn


def resolve_verify_param():
    if API_CA:
        return API_CA
    return True if API_VERIFY == "1" else False


# --- MySQL 設定（可由環境變數覆寫；僅用於 CLI mysql_raw 模式） ---
# 例：
#   set MYSQL_HOST=127.0.0.1
#   set MYSQL_PORT=3306
#   set MYSQL_DB=test
#   set MYSQL_USER=root
#   set MYSQL_PASSWORD=secret
#   set MYSQL_TIMEOUT=20
#   set MYSQL_CHARSET=utf8mb4
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1").strip()
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
# 預設直接覆蓋為你的資料庫名稱，仍可用環境變數覆寫
MYSQL_DB = os.getenv("MYSQL_DB", "mydb").strip()
# 預設直接覆蓋為你的帳號/密碼，仍可用環境變數覆寫
MYSQL_USER = os.getenv("MYSQL_USER", "root").strip()
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "apple586").strip()
MYSQL_TIMEOUT = int(os.getenv("MYSQL_TIMEOUT", "20"))
MYSQL_CHARSET = os.getenv("MYSQL_CHARSET", "utf8mb4").strip()
