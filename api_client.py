
import os, sys, requests
from typing import List
from settings import (
    API_HOST,
    API_PORT,
    API_PATH,
    API_TIMEOUT,
    USE_SYSTEM_PROXY,
    API_HOST_HEADER,
    API_VERIFY,
    API_CA,
    resolve_verify_param,
)


try:
    from requests_toolbelt.adapters.host_header_ssl import HostHeaderSSLAdapter

    _HAS_HOSTHEADER_ADAPTER = True
except Exception:
    _HAS_HOSTHEADER_ADAPTER = False


try:
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass


def _build_api_urls(sn: str) -> List[str]:
    if "{sn}" not in API_PATH:
        raise RuntimeError("API_PATH 必須包含 {sn}")
    path = API_PATH.format(sn=sn)
    urls = [
        f"https://{API_HOST}{path}",
        f"https://{API_HOST}:{API_PORT}{path}",
        f"http://{API_HOST}:{API_PORT}{path}",
    ]
    uniq, seen = [], set()
    for u in urls:
        if u not in seen:
            uniq.append(u)
            seen.add(u)
    return uniq


def call_api(sn: str) -> dict:
    urls = _build_api_urls(sn)
    sess = requests.Session()
    sess.trust_env = USE_SYSTEM_PROXY
    verify_param = resolve_verify_param()
    if API_HOST_HEADER and _HAS_HOSTHEADER_ADAPTER:
        sess.mount("https://", HostHeaderSSLAdapter())
    headers = {"Host": API_HOST_HEADER} if API_HOST_HEADER else None

    last_err, tried = None, []
    for url in urls:
        tried.append(url)
        try:
            resp = sess.get(
                url, timeout=API_TIMEOUT, verify=verify_param, headers=headers
            )
            resp.raise_for_status()
            try:
                return resp.json()
            except Exception:
                return {"status": resp.status_code, "text": resp.text}
        except Exception as e:
            last_err = f"{url} -> {e}"
    raise RuntimeError(
        "API 連線失敗；已嘗試：\n  - "
        + "\n  - ".join(tried)
        + f"\n設定：host={API_HOST} port={API_PORT} timeout={API_TIMEOUT}s "
        f"use_system_proxy={USE_SYSTEM_PROXY} "
        f"verify={'CA:'+API_CA if API_CA else ('True' if API_VERIFY=='1' else 'False')} "
        f"host_header={'<none>' if not API_HOST_HEADER else API_HOST_HEADER} "
        f"sni_adapter={'on' if (API_HOST_HEADER and _HAS_HOSTHEADER_ADAPTER) else 'off'}\n"
        f"最後錯誤：{last_err}"
    )


def summarize_api_payload(payload: dict) -> str:
    try:
        status = payload.get("status")
        results = payload.get("result", [])
        repair = [r for r in results if r.get("TABLES") == "REPAIR STATUS"]
        wip = [r for r in results if r.get("TABLES") == "WIP STATUS"]
        lines = [
            f"status: {status}",
            f"REPAIR STATUS 筆數: {len(repair)}",
            f"WIP STATUS 筆數: {len(wip)}",
        ]
        if wip:
            last = wip[-1]
            lines.append(f"MODEL_NAME: {last.get('MODEL_NAME','')}")
            lines.append(f"WIP_GROUP: {last.get('WIP_GROUP','')}")
        if repair:
            last = repair[-1]
            lines.append(f"最後測試 TEST_CODE: {last.get('TEST_CODE','')}")
            lines.append(f"最後測試 DATA1: {last.get('DATA1','')}")
        return "\n".join(lines)
    except Exception:
        return "(無法產生摘要)"
