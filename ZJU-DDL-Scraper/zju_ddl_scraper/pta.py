"""
PTA (拼题 A) 爬虫模块
使用 REST API 直接获取作业列表（不需要浏览器）
"""

import os
import time
from typing import Optional
from urllib.parse import urljoin

import requests
from dateutil.parser import isoparse

from .models import DDLItem

BASE_URL = "https://pintia.cn"
API_PROBLEM_SETS = "/api/problem-sets"


class PTAScraper:
    """PTA 爬虫 - 通过 API 获取作业列表"""

    def __init__(self, cookie_str: str = "", timeout: int = 30):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        })
        self.timeout = timeout

        if cookie_str:
            self._set_cookies(cookie_str)
        else:
            self._load_cookies_from_env()

    def _set_cookies(self, cookie_str: str):
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                self.session.cookies.set(key.strip(), value.strip(), domain=".pintia.cn")

    def _load_cookies_from_env(self):
        env_cookies = os.environ.get("PTA_COOKIES", "")
        if env_cookies:
            self._set_cookies(env_cookies)

    def _request_json(self, method: str, path: str, **kwargs):
        url = urljoin(BASE_URL, path)
        kwargs.setdefault("timeout", self.timeout)
        headers = kwargs.pop("headers", {})
        headers.setdefault("Accept", "application/json")
        headers.setdefault("Origin", BASE_URL)
        headers.setdefault("Referer", f"{BASE_URL}/problem-sets")
        kwargs["headers"] = headers
        resp = self.session.request(method, url, **kwargs)

        ct = resp.headers.get("content-type", "")
        if "json" not in ct.lower():
            raise RuntimeError(f"API 返回非 JSON (HTTP {resp.status_code})，Cookie 可能已过期")
        data = resp.json()
        if "error" in data or "code" in data:
            raise RuntimeError(data.get("message", str(data)))
        return data

    def verify(self) -> bool:
        try:
            self._request_json("GET", API_PROBLEM_SETS, params={"page": 0, "limit": 1})
            return True
        except RuntimeError:
            return False

    def fetch_all(self) -> list[dict]:
        """获取所有题目集"""
        all_items = []
        total = None
        limit = 50
        page = 0

        while total is None or len(all_items) < total:
            data = self._request_json("GET", API_PROBLEM_SETS, params={"page": page, "limit": limit})
            if total is None:
                total = data.get("total", 0)
            items = data.get("problemSets", [])
            all_items.extend(items)
            page += 1
            if len(items) < limit:
                break
            time.sleep(0.3)

        return all_items

    def get_ddl_items(self) -> list[DDLItem]:
        """获取 DDL 列表"""
        items = self.fetch_all()
        ddls = []
        for item in items:
            end_str = item.get("endAt")
            if not end_str:
                continue
            try:
                deadline = isoparse(end_str)
            except (ValueError, TypeError):
                continue
            ddls.append(DDLItem.from_pta_item(item))

        ddls.sort(key=lambda x: x.deadline)
        return ddls
