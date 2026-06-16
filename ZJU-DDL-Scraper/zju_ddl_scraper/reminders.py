"""
macOS 提醒事项导入模块
"""

import json
import os
import subprocess
from datetime import datetime, timezone
from .models import DDLItem

# 缓存文件：记录已导入的提醒事项名称
CACHE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    ".imported_reminders_cache.json"
)


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _make_reminder_name(d: DDLItem) -> str:
    return f"📚 [{d.source.upper()}] [{d.course}] {d.title}"


def _load_cache() -> set:
    """加载已导入提醒事项的缓存"""
    if not os.path.exists(CACHE_FILE):
        return set()
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, IOError):
        return set()


def _save_cache(names: set):
    """保存已导入提醒事项的缓存"""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(names), f, ensure_ascii=False, indent=2)
    except IOError:
        pass


def import_to_reminders(items: list[DDLItem], list_name: str = "Reminders") -> int:
    """将新 DDL 导入 macOS 提醒事项，自动跳过已导入的"""
    now = datetime.now(timezone.utc)
    active = [d for d in items if d.deadline > now]

    if not active:
        return 0

    # 查缓存
    imported = _load_cache()
    new_items = [d for d in active if _make_reminder_name(d) not in imported]

    if not new_items:
        return 0

    # 批量导入
    cmds = []
    for d in new_items:
        name = _make_reminder_name(d)
        due = d.deadline.strftime("%Y-%m-%d %H:%M:%S")
        notes = f"提交率: {d.rate}%  {d.url}" if d.rate is not None else d.url
        cmds.append(
            f'make new reminder with properties {{'
            f'name:"{_esc(name)}", '
            f'due date:(date "{due}"), '
            f'body:"{_esc(notes)}"'
            f'}}'
        )

    script = f'''
    tell application "Reminders"
        tell list "{_esc(list_name)}"
            {"".join(cmds)}
        end tell
    end tell
    '''

    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=60
    )

    if result.returncode == 0:
        # 记录到缓存
        for d in new_items:
            imported.add(_make_reminder_name(d))
        _save_cache(imported)
        return len(new_items)

    # 逐个导入
    success = 0
    for d in new_items:
        name = _make_reminder_name(d)
        due = d.deadline.strftime("%Y-%m-%d %H:%M:%S")
        notes = f"提交率: {d.rate}%  {d.url}" if d.rate is not None else d.url
        single = f'''tell application "Reminders"
            tell list "{_esc(list_name)}"
                make new reminder with properties {{name:"{_esc(name)}", due date:(date "{due}"), body:"{_esc(notes)}"}}
            end tell
        end tell'''
        r = subprocess.run(["osascript", "-e", single], capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            imported.add(name)
            success += 1

    _save_cache(imported)
    return success
