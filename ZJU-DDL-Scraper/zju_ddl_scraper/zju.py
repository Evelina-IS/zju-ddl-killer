"""
学在浙大 (courses.zju.edu.cn) 爬虫模块
使用 Playwright 自动化浏览器获取作业 DDL
"""

import asyncio
import json
from datetime import datetime
from typing import Optional

from .models import DDLItem


class ZJUScraper:
    """学在浙大爬虫 - 通过 Playwright 登录并获取作业"""

    def __init__(self, username: str = "", password: str = ""):
        self.username = username or ""
        self.password = password or ""

        if not self.username:
            import os
            self.username = os.environ.get("ZJU_USER", "")
        if not self.password:
            import os
            self.password = os.environ.get("ZJU_PASS", "")

    async def _login_and_fetch(self) -> list[dict]:
        """登录学在浙大并获取作业数据"""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
            page = await ctx.new_page()

            # Step 1: CAS 登录
            await page.goto("https://zjuam.zju.edu.cn/cas/login", wait_until="load")
            await page.fill("#username", self.username)
            await page.fill("#password", self.password)
            await page.click("#dl")
            await asyncio.sleep(3)

            # Step 2: 跳转到学在浙大
            await page.goto("https://course.zju.edu.cn/learninginzju?locale=en-US", wait_until="load")
            await asyncio.sleep(2)
            cas_btn = await page.query_selector("text=CAS Login")
            if cas_btn:
                await cas_btn.click()
                await asyncio.sleep(5)

            # Step 3: 访问用户中心
            await page.goto("https://courses.zju.edu.cn/user/index#/", wait_until="load")
            await asyncio.sleep(3)

            # Step 4: 获取 API 数据
            await page.goto("https://courses.zju.edu.cn/api/todos?no-intercept=true", wait_until="load")
            await asyncio.sleep(2)

            raw_text = await page.inner_text("pre")
            await browser.close()

        return json.loads(raw_text)

    def has_credentials(self) -> bool:
        return bool(self.username) and bool(self.password)

    async def get_ddl_items(self) -> list[DDLItem]:
        """获取学在浙大的 DDL 列表"""
        if not self.has_credentials():
            return []

        data = await self._login_and_fetch()
        ddls = []
        seen = set()

        for todo in data.get("todo_list", []):
            end = todo.get("end_time")
            if not end:
                continue
            try:
                dl = datetime.fromisoformat(end.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue

            title = todo.get("title", "未知")
            course = todo.get("course_name", "未知")
            course_id = todo.get("course_id", "")

            # 去重
            key = (title, course, dl.isoformat())
            if key in seen:
                continue
            seen.add(key)

            ddls.append(DDLItem(
                title=title,
                source="zju",
                course=course,
                deadline=dl,
                url=f"https://courses.zju.edu.cn/course/{course_id}" if course_id else "",
                rate=todo.get("submit_rate"),
            ))

        ddls.sort(key=lambda x: x.deadline)
        return ddls
