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

# --- Oracle 設定 ---
ORACLE_USER = os.getenv("ORACLE_USER", "TE")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "B05te")
ORACLE_DSN = os.getenv("ORACLE_DSN", "10.220.130.221:1521/vnsfc")
ORACLE_SQL_SN = (
    "SELECT MODEL_NAME, SHIPPING_SN, DATA1 FROM sfism4.R109 WHERE SHIPPING_SN = :sn"
)
SQL_MAX_ROWS = int(os.getenv("SQL_MAX_ROWS", "200"))


def augment_easy_connect_with_timeout(dsn: str, timeout: int = 20) -> str:
    if any(sep in dsn for sep in ("/", ":", "@")) and "connect_timeout=" not in dsn:
        joiner = "&" if "?" in dsn else "?"
        return f"{dsn}{joiner}connect_timeout={timeout}"
    return dsn


def resolve_verify_param():
    if API_CA:
        return API_CA
    return True if API_VERIFY == "1" else False
