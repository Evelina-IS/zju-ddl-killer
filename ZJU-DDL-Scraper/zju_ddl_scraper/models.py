"""
数据模型 - 统一 DDL 条目
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional

CST = timezone(timedelta(hours=8))


@dataclass
class DDLItem:
    """统一的 DDL 条目"""
    title: str
    source: str            # "zju" 或 "pta"
    course: str            # 课程名称
    deadline: datetime     # UTC 时间
    url: str = ""
    rate: Optional[int] = None    # 提交率（学在浙大）
    problem_set_id: Optional[str] = None  # PTA 题目集 ID
    teacher: str = ""
    school: str = ""

    def deadline_cst(self) -> str:
        return self.deadline.astimezone(CST).strftime("%Y-%m-%d %H:%M")

    def deadline_cst_short(self) -> str:
        return self.deadline.astimezone(CST).strftime("%m-%d %H:%M")

    def tag(self) -> str:
        """返回紧急程度标签"""
        delta = (self.deadline - datetime.now(timezone.utc)).days
        if delta < 0:
            return "⚠️"
        if delta <= 1:
            return "🔥"
        if delta <= 3:
            return "⚡"
        if delta <= 7:
            return "📌"
        return "✅"

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "source": self.source,
            "course": self.course,
            "deadline": self.deadline.isoformat(),
            "url": self.url,
            "rate": self.rate,
            "teacher": self.teacher,
            "school": self.school,
            "tag": self.tag(),
        }

    @classmethod
    def from_pta_item(cls, item: dict) -> "DDLItem":
        """从 PTA API 响应创建 DDLItem"""
        from dateutil.parser import isoparse

        end_str = item.get("endAt")
        start_str = item.get("startAt")
        deadline = isoparse(end_str) if end_str else None
        if not deadline:
            # 如果没有截止时间，用开始时间 + 7天估算
            deadline = isoparse(start_str) + timedelta(days=7) if start_str else datetime.now(timezone.utc)

        name = item.get("name", "")
        teacher = item.get("ownerNickname", "")
        school = item.get("organizationName", "")

        return cls(
            title=name,
            source="pta",
            course=name.split("_")[0] if "_" in name else school,
            deadline=deadline,
            url=f"https://pintia.cn/problem-sets/{item.get('id', '')}",
            problem_set_id=item.get("id"),
            teacher=teacher,
            school=school,
        )
