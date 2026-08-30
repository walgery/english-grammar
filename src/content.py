"""语法内容库加载：grammar_data/ 下每个专题一个 JSON 文件。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "grammar_data"


def load_level(level: str) -> list[dict]:
    """加载某学段全部专题（level: middle/high），按 id 排序返回。"""
    directory = DATA_DIR / level
    if not directory.exists():
        return []
    items: list[dict] = []
    for p in sorted(directory.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("id") and data.get("questions"):
            items.append(data)
    items.sort(key=lambda t: t["id"])
    return items


def get_topic(level: str, topic_id: str) -> dict | None:
    for t in load_level(level):
        if t["id"] == topic_id:
            return t
    return None


def topic_progress(topic_id: str, stats: dict) -> float:
    """某专题的掌握度：做对题数 / 做过的题数（无记录返回 -1 表示未学）。"""
    rec = stats.get(topic_id)
    if not rec or not rec.get("attempted"):
        return -1.0
    return rec["correct"] / rec["attempted"]


# 专题图标（语法地图美化用）
TOPIC_ICONS = {
    "m01": "⏰", "m02": "🧑‍🏫", "m03": "📚", "m04": "🏠", "m05": "❓", "m06": "🏃",
    "m07": "⏳", "m08": "🚀", "m09": "🔑", "m10": "⚖️", "m11": "📝", "m12": "📌",
    "m13": "🎯", "m14": "💬", "m15": "🔗", "m16": "🛡️", "m17": "🌟", "m18": "❗",
    "h02": "➡️", "h03": "🔁", "h04": "🎭", "h05": "🔍", "h06": "🧩",
    "h07": "🌉", "h08": "💭", "h09": "🔄", "h10": "💡", "h11": "🧮", "h12": "🔮",
    "h13": "⏪", "h14": "🔭", "h15": "⏲️", "h16": "🛠️",
}



def topic_icon(topic_id: str) -> str:
    return TOPIC_ICONS.get(topic_id, "📘")


# 语法分类体系：由易到难排列，类内专题也按难度排序
CATEGORIES = [
    ("🌱", "基础入门", "be 动词、代词、名词——一切语法的地基",
     ["m01", "m02", "m03"]),
    ("🏗️", "基本句型", "there be、特殊疑问句、感叹句与祈使句",
     ["m04", "m05", "m18"]),
    ("⏰", "时态与语态", "从进行时到完成时，再到被动语态（初中 → 高中层层进阶）",
     ["m06", "m07", "m08", "m11", "m12", "m16", "h13", "h14", "h15", "h16"]),
    ("⚡", "动词进阶", "情态动词与非谓语动词（不定式、动名词、分词）",
     ["m09", "m13", "h02", "h03", "h04", "h12"]),
    ("⚖️", "比较与一致", "比较级最高级、主谓一致",
     ["m10", "h11"]),
    ("🧩", "从句体系", "宾语从句 → 状语从句 → 定语从句 → 名词性从句",
     ["m14", "m15", "m17", "h05", "h06", "h07"]),
    ("🎭", "特殊句式与语气", "虚拟语气、倒装句、强调句——冲刺高分",
     ["h08", "h09", "h10"]),
]
