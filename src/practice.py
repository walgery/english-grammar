"""练习判分与错题本（按学生分别存储：data/<学生>/ 目录）。"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

QUESTION_TYPES = {
    "choice": "单选",
    "fill": "填空",
    "correct": "改错",
    "translate": "翻译",
}


def _dir(student: str = "") -> Path:
    """某学生的数据目录：data/<姓名>。未指定时用 default（本地单人场景）。"""
    safe = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", (student or "").strip()) or "default"
    return ROOT / "data" / safe


def _norm(s: str) -> str:
    """答案规范化：小写、压缩空格、去首尾标点。"""
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[。，,.!?！？;；:：'\"“”‘’]+$", "", s)
    s = s.replace("’", "'")
    return s


def check_answer(q: dict, user_answer: str) -> bool:
    """判分。choice 题的 user_answer 传选项序号字符串。"""
    ans = q.get("answer")
    if q.get("type") == "choice":
        try:
            return int(user_answer) == int(ans)
        except (TypeError, ValueError):
            return False
    answers = ans if isinstance(ans, list) else [ans]
    norm_user = _norm(user_answer)
    return bool(norm_user) and any(_norm(a) == norm_user for a in answers)


# —— 错题本（按学生）——


def load_book(student: str = "") -> dict:
    try:
        return json.loads((_dir(student) / "wrong_book.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_book(book: dict, student: str = "") -> None:
    d = _dir(student)
    d.mkdir(parents=True, exist_ok=True)
    (d / "wrong_book.json").write_text(json.dumps(book, ensure_ascii=False, indent=1), encoding="utf-8")


def record_wrong(student: str, topic_id: str, q_index: int, q: dict, user_answer: str) -> None:
    """记一道错题（同题重复错只累加次数与更新最后答案）。"""
    book = load_book(student)
    key = f"{topic_id}:{q_index}"
    rec = book.get(key, {
        "topic_id": topic_id,
        "question": q,
        "wrong_times": 0,
    })
    rec["wrong_times"] = rec.get("wrong_times", 0) + 1
    rec["last_user_answer"] = user_answer
    rec["last_at"] = time.time()
    book[key] = rec
    save_book(book, student)


def remove_wrong(student: str, key: str) -> None:
    book = load_book(student)
    book.pop(key, None)
    save_book(book, student)


def merge_book(current: dict, imported: dict) -> tuple[dict, int]:
    """合并两个错题本：同一题目保留错题次数更多（更新）的记录。

    返回 (合并后的错题本, 新增/更新的条数)。忽略非法条目。
    """
    merged = dict(current)
    count = 0
    for key, rec in imported.items():
        if not isinstance(rec, dict) or "question" not in rec or ":" not in str(key):
            continue
        old = merged.get(key)
        if old is None:
            merged[key] = rec
            count += 1
        elif rec.get("wrong_times", 0) >= old.get("wrong_times", 0):
            merged[key] = rec
            count += 1
    return merged, count


# —— 专题统计（掌握度，按学生）——


def load_stats(student: str = "") -> dict:
    try:
        return json.loads((_dir(student) / "stats.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_stats(stats: dict, student: str = "") -> None:
    d = _dir(student)
    d.mkdir(parents=True, exist_ok=True)
    (d / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")


def record_attempt(student: str, topic_id: str, correct: bool) -> None:
    stats = load_stats(student)
    rec = stats.setdefault(topic_id, {"attempted": 0, "correct": 0})
    rec["attempted"] += 1
    if correct:
        rec["correct"] += 1
    save_stats(stats, student)


# —— 练习现场（按学生，第二天接着做）——


def save_practice(student: str, state: dict) -> None:
    d = _dir(student)
    d.mkdir(parents=True, exist_ok=True)
    state = dict(state)
    state["saved_at"] = time.time()
    (d / "practice.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def load_practice(student: str = "") -> dict | None:
    try:
        data = json.loads((_dir(student) / "practice.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("practice_qs") else None


def clear_practice(student: str = "") -> None:
    try:
        (_dir(student) / "practice.json").unlink()
    except OSError:
        pass
