"""
统一 CLI 入口
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone, timedelta

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .models import DDLItem
from .pta import PTAScraper
from .zju import ZJUScraper
from .reminders import import_to_reminders

CST = timezone(timedelta(hours=8))
console = Console()


def display_ddls(items: list[DDLItem], keyword: str = ""):
    """表格显示 DDL"""
    if keyword:
        kw = keyword.lower()
        items = [d for d in items if kw in d.title.lower() or kw in d.course.lower()]

    if not items:
        console.print("[yellow]没有找到匹配项[/yellow]")
        return

    table = Table(
        title=f"📚 DDL 列表 (共 {len(items)} 项)",
        title_justify="left",
        show_lines=False,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("来源", width=5)
    table.add_column("课程", style="blue", no_wrap=False)
    table.add_column("作业", style="cyan", no_wrap=False)
    table.add_column("截止时间(CST)", style="white")
    table.add_column("状态", style="bold")

    for i, d in enumerate(items, 1):
        table.add_row(
            str(i),
            {"zju": "ZJU", "pta": "PTA"}.get(d.source, d.source),
            d.course,
            d.title,
            d.deadline_cst(),
            d.tag(),
        )

    console.print(table)


def print_summary(items: list[DDLItem]):
    """打印统计摘要"""
    now = datetime.now(timezone.utc)
    active = sum(1 for d in items if d.deadline > now)
    overdue = sum(1 for d in items if d.deadline < now)
    urgent = sum(1 for d in items if now < d.deadline <= now + timedelta(days=3))
    zju_count = sum(1 for d in items if d.source == "zju")
    pta_count = sum(1 for d in items if d.source == "pta")

    console.print(Panel(
        f"总计 [bold]{len(items)}[/bold] 项 | "
        f"ZJU [blue]{zju_count}[/blue] / PTA [green]{pta_count}[/green]\n"
        f"▶️ 进行中 [green]{active}[/green] | "
        f"🔥 3日内 [red]{urgent}[/red] | "
        f"⚠️ 已过期 {overdue}",
        title="📊 统计",
    ))


def export_json(items: list[DDLItem], filepath: str):
    """导出 JSON"""
    data = [d.to_dict() for d in items]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    console.print(f"[green]已导出 {len(data)} 项到 {filepath}[/green]")


def export_csv(items: list[DDLItem], filepath: str):
    """导出 CSV"""
    fieldnames = ["source", "course", "title", "deadline", "url", "rate", "tag", "teacher", "school"]
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for d in items:
            w.writerow(d.to_dict())
    console.print(f"[green]已导出 {len(items)} 项到 {filepath}[/green]")


def main():
    parser = argparse.ArgumentParser(
        description="📚 ZJU DDL 统一爬虫 - 学在浙大 + PTA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 列出所有 DDL
  zju-ddl

  # 仅爬取 PTA
  zju-ddl --pta-only

  # 搜索关键词
  zju-ddl --keyword HW

  # 只看进行中
  zju-ddl --status active

  # 导出
  zju-ddl --export ddls.json
  zju-ddl --export ddls.csv

  # 导入 macOS 提醒事项
  zju-ddl --to-reminders

  # 完整流程
  zju-ddl --keyword 作业 --to-reminders --export ddls.json

环境变量:
  PTA_COOKIES   PTA 的 Cookie（需包含 PTASession 和 JSESSIONID）
  ZJU_USER      学在浙大用户名（学号）
  ZJU_PASS      学在浙大密码
        """,
    )

    src = parser.add_argument_group("数据源")
    src.add_argument("--pta-only", action="store_true", help="仅爬取 PTA")
    src.add_argument("--zju-only", action="store_true", help="仅爬取学在浙大")
    src.add_argument("--pta-cookie", help="PTA Cookie 字符串")

    out = parser.add_argument_group("输出选项")
    out.add_argument("-k", "--keyword", help="按关键词筛选")
    out.add_argument("--status", choices=["active", "upcoming", "ended"],
                     help="按时间状态筛选 (进行中/未开始/已结束)")
    out.add_argument("--export", help="导出到文件 (.json / .csv)")
    out.add_argument("--to-reminders", action="store_true", help="导入 macOS 提醒事项")
    out.add_argument("--reminders-list", default="Reminders", help="提醒事项列表名 (默认: Reminders)")

    args = parser.parse_args()

    all_ddls: list[DDLItem] = []
    scraper_zju = ZJUScraper()
    scraper_pta = PTAScraper(cookie_str=args.pta_cookie or "")

    # ── PTA ──
    fetch_pta = not args.zju_only
    if fetch_pta:
        if scraper_pta.verify():
            console.print("[green]✅ PTA 登录验证成功[/green]")
            items = scraper_pta.get_ddl_items()
            all_ddls.extend(items)
            console.print(f"  → 获取 [cyan]{len(items)}[/cyan] 项 PTA 作业")
        else:
            console.print("[yellow]⚠️ PTA 未配置或 Cookie 已过期（跳过）[/yellow]")
            console.print("  设置 [bold]PTA_COOKIES[/bold] 环境变量或使用 [bold]--pta-cookie[/bold]")

    # ── 学在浙大 ──
    fetch_zju = not args.pta_only
    if fetch_zju and scraper_zju.has_credentials():
        import asyncio
        console.print("[blue]🔑 学在浙大登录中...[/blue]")
        try:
            items = asyncio.run(scraper_zju.get_ddl_items())
            all_ddls.extend(items)
            console.print(f"  → 获取 [blue]{len(items)}[/blue] 项 ZJU 作业")
        except Exception as e:
            console.print(f"[red]❌ 学在浙大抓取失败: {e}[/red]")
    elif fetch_zju:
        console.print("[yellow]⚠️ 学在浙大未配置（跳过）[/yellow]")
        console.print("  设置 [bold]ZJU_USER[/bold] 和 [bold]ZJU_PASS[/bold] 环境变量")

    # ── 排序 ──
    all_ddls.sort(key=lambda d: d.deadline)

    if not all_ddls:
        console.print("\n[yellow]没有获取到任何 DDL[/yellow]")
        sys.exit(0)

    # ── 按状态筛选 ──
    if args.status:
        now = datetime.now(timezone.utc)
        if args.status == "active":
            all_ddls = [d for d in all_ddls if d.deadline > now]
        elif args.status == "ended":
            all_ddls = [d for d in all_ddls if d.deadline < now]
        elif args.status == "upcoming":
            # "未开始" 对 PTA 来说是有 startAt 且 startAt > now 的作业
            all_ddls = [d for d in all_ddls if d.deadline > now + timedelta(days=7)]

    # ── 按关键词筛选 ──
    if args.keyword:
        kw = args.keyword.lower()
        all_ddls = [d for d in all_ddls if kw in d.title.lower() or kw in d.course.lower()]

    if not all_ddls:
        console.print("[yellow]没有匹配的 DDL[/yellow]")
        sys.exit(0)

    # ── 显示 ──
    console.print()
    display_ddls(all_ddls)
    print_summary(all_ddls)

    # ── 导出 ──
    if args.export:
        ext = os.path.splitext(args.export)[1].lower()
        if ext == ".csv":
            export_csv(all_ddls, args.export)
        else:
            export_json(all_ddls, args.export)

    # ── 提醒事项 ──
    if args.to_reminders:
        console.print(f"\n📲 导入 macOS 提醒事项 (列表: {args.reminders_list})...", end=" ")
        ok = import_to_reminders(all_ddls, args.reminders_list)
        console.print(f"[green]✅ {ok}/{len(all_ddls)}[/green]")


if __name__ == "__main__":
    main()
