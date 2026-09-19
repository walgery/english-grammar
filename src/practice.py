"""练习判分与错题本（按学生分别存储：data/<学生>/ 目录）。"""

from __future__ import annotations

import difflib
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
    """某学生的数据目录：data/<姓名>。未指定时用 default（本地单人场景）。

    安全：学生名作为目录名，必须防止路径穿越（如 ".." 洗成 "_" 后仍是合法目录名，
    但原始输入若含斜杠/点号组合可能逃出 data/）。统一做两步防护。
    """
    raw = (student or "").strip()
    # 第一步：去掉路径分隔符和点号，杜绝 ../、./、a/b 等穿越
    raw = raw.replace("/", "").replace("\\", "").replace(".", "")
    # 第二步：仅保留中英文、数字、下划线、连字符，其余洗成 _
    safe = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", raw) or "default"
    # 第三步：最终校验——解析后的路径必须仍在 data/ 内
    d = (ROOT / "data" / safe).resolve()
    if d.parent != (ROOT / "data").resolve():
        safe = "default"
        d = (ROOT / "data" / safe).resolve()
    return d


def _norm(s: str) -> str:
    """答案规范化：小写、压缩空格、去首尾标点。"""
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[。，,.!?！？;；:：'\"“”‘’]+$", "", s)
    s = s.replace("’", "'")
    return s


def _norm_loose(s: str) -> str:
    """翻译题用的宽松规范化：在小写/压缩空格基础上，去掉所有标点（保留撇号）。"""
    s = _norm(s)
    s = re.sub(r"[^\w\s']", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _tokens(s: str) -> list[str]:
    """切词：按空白拆，词内标点去掉（保留撇号，如 doesn't）。"""
    return re.sub(r"[^\w\s']", " ", s).split()


def full_correct_sentences(q: dict) -> list[str]:
    """改错题的所有完整正确句子（可能多个）。支持的 answer 数据格式：
    ① "错误词 → 正确词"：替换型，合成一个整句；
    ② "错误词 → 正确词1 / 正确词2 / ..."：替换型多答案，右侧按 " / " 分隔，各合成整句；
    ③ "完整英文句"（删除型/改写型单答案）：直接作为一个正确句；
    ④ ["完整英文句1", "完整英文句2", ...]（删除型/改写型多答案）：每个元素是一个正确句。
    返回去重后的正确句列表，无法确定时返回空列表。
    """
    ans = q.get("answer")
    out: list[str] = []

    def from_sentence(s: str) -> None:
        # answer 是纯英文完整句：去掉末尾括号注释后使用
        s2 = re.sub(r"（[^（）]*）\s*$", "", s.strip()).strip()
        if re.search(r"[A-Za-z]", s2) and not re.search(r"[\u4e00-\u9fff]", s2):
            out.append(s2)

    if isinstance(ans, list):
        for item in ans:
            if isinstance(item, str):
                from_sentence(item)
    elif isinstance(ans, str):
        ans = ans.strip()
        if "→" in ans:
            wrong, _, right = (s.strip() for s in ans.partition("→"))
            stem = q.get("stem") or ""
            if wrong and right and stem:
                for opt in [o.strip() for o in right.split(" / ") if o.strip()]:
                    corrected, n = re.subn(re.escape(wrong), lambda m: opt, stem, count=1)
                    if n == 0:  # 精确匹配失败时忽略大小写再试一次
                        corrected, n = re.subn(re.escape(wrong), lambda m: opt, stem, count=1, flags=re.IGNORECASE)
                    if n:
                        out.append(corrected)
        else:
            from_sentence(ans)
    # 去重保持顺序
    seen: set[str] = set()
    result: list[str] = []
    for s in out:
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result


def full_correct_sentence(q: dict) -> str:
    """兼容包装：返回第一个完整正确句子（用于展示）。"""
    lst = full_correct_sentences(q)
    return lst[0] if lst else ""


def _sentence_close(user_toks: list[str], expect_toks: list[str], key_toks: set[str]) -> bool:
    """整句逐词对比：词数一致；关键词必须完全一致，其余词允许一个字符以内的笔误。"""
    if len(user_toks) != len(expect_toks):
        return False
    for a, b in zip(user_toks, expect_toks):
        if a == b:
            continue
        if a in key_toks or b in key_toks:  # 考点词必须精确写对
            return False
        if difflib.SequenceMatcher(None, a, b).ratio() < 0.8:
            return False
    return True


def check_answer(q: dict, user_answer: str) -> bool:
    """判分。choice 题的 user_answer 传选项序号字符串。"""
    ans = q.get("answer")
    if q.get("type") == "choice":
        try:
            return int(user_answer) == int(ans)
        except (TypeError, ValueError):
            return False
    answers = ans if isinstance(ans, list) else [ans]
    if q.get("type") == "translate":
        # 翻译题：大小写、空格、标点差异不扣分（同义表达由 AI 批改兜底）
        nu = _norm_loose(user_answer)
        return bool(nu) and any(_norm_loose(a) == nu for a in answers)
    if q.get("type") == "correct":
        # 改错题要求写出完整的正确句子：任一正确改法匹配即对，考点词精确、其余词容忍笔误
        fulls = full_correct_sentences(q)
        if fulls:
            user_toks = _tokens(_norm(user_answer))
            stem_toks = set(_tokens(_norm(q.get("stem", ""))))
            for full in fulls:
                if "→" in str(ans):
                    # 替换型：考点词 = 箭头右侧该改法对应的正确词
                    right = str(ans).partition("→")[2]
                    opts = [o.strip() for o in right.split(" / ") if o.strip()]
                    key = set()
                    for o in opts:
                        key |= set(_tokens(_norm(o)))
                else:
                    # 删除型/改写型：考点词 = 正确句与题干错句的词汇差异部分
                    full_toks = set(_tokens(_norm(full)))
                    key = stem_toks.symmetric_difference(full_toks)
                if _sentence_close(user_toks, _tokens(_norm(full)), key):
                    return True
            return False
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


def undo_attempt(student: str, topic_id: str, was_correct: bool) -> None:
    """撤销一次判分记录（用于"重答"）：attempted 减 1，若上次判对则 correct 也减 1。"""
    stats = load_stats(student)
    rec = stats.get(topic_id)
    if not rec:
        return
    rec["attempted"] = max(0, rec.get("attempted", 0) - 1)
    if was_correct:
        rec["correct"] = max(0, rec.get("correct", 0) - 1)
    if rec["attempted"] == 0:
        stats.pop(topic_id, None)  # 没有作答记录则移除该专题，避免掌握度显示 0%
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
