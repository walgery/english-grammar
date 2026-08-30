"""LLM 助教：动态出题与错题讲解（复用生词造句项目的配置与调用模式）。"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / "llm_config.json"

TIMEOUT = 120.0


def load_config() -> dict:
    """读取配置：本地 llm_config.json 优先，其次 st.secrets 的 [llm] 段。"""
    data: dict = {}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            data = loaded
    except (OSError, ValueError):
        pass
    if not any(str(data.get(k) or "").strip() for k in ("api_key", "base_url", "model")):
        try:
            import streamlit as st

            sec = st.secrets["llm"]
            for k in ("api_key", "base_url", "model"):
                v = sec.get(k)
                if v and not str(data.get(k) or "").strip():
                    data[k] = v
        except Exception:
            pass
    return {k: str(data.get(k) or "") for k in ("api_key", "base_url", "model")}


def is_configured() -> bool:
    cfg = load_config()
    return bool(cfg["api_key"])


def _client():
    from openai import OpenAI

    cfg = load_config()
    api_key = cfg["api_key"] or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("未配置 API 密钥（请在侧边栏填写并保存）")
    base_url = cfg["base_url"]
    # 密钥/接口地址含非 ASCII 字符（中文、全角符号等）时，HTTP 头编码会直接失败
    try:
        api_key.encode("ascii")
        (base_url or "").encode("ascii")
    except UnicodeEncodeError:
        raise RuntimeError("大模型参数不正确，请联系作者")
    kwargs: dict = {"api_key": api_key, "timeout": TIMEOUT}
    if base_url:
        kwargs["base_url"] = base_url
    model = cfg["model"] or os.getenv("LLM_MODEL", "gpt-4o-mini")
    extra_body = None
    if base_url and "bigmodel" in base_url:
        extra_body = {"thinking": {"type": "enabled", "effort": "low"}}
    return OpenAI(**kwargs), model, extra_body


def _extract_json(text: str) -> list:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        pass
    m = re.search(r"\[[\s\S]*\]", text)
    if m:
        try:
            data = json.loads(m.group(0))
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            pass
    rows = []
    for obj in re.findall(r"\{[^{}]*\}", text):
        try:
            row = json.loads(obj)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _chat(system: str, user: str) -> str:
    client, model, extra_body = _client()
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0.6,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            extra_body=extra_body,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        # 认证 / 参数 / 地址类错误统一转为友好提示（401 密钥无效、404 模型名错误、400 请求不合法等）
        if type(e).__name__ in ("AuthenticationError", "NotFoundError", "BadRequestError", "PermissionDeniedError"):
            raise RuntimeError("大模型参数不正确，请联系作者") from e
        raise


def _level_label(level: str) -> str:
    return "初中（人教版七~九年级）" if level == "middle" else "高中（人教版必修~选修）"


def gen_questions(level: str, topic: str, n: int = 5, avoid: list[str] | None = None) -> list[dict]:
    """让 LLM 针对语法专题出 n 道新题，返回与题库同 schema 的题目列表。"""
    avoid_text = ""
    if avoid:
        avoid_text = "\n以下题目或考点已出现过，请出不同的：\n" + "\n".join(f"- {a}" for a in avoid[:10])
    system = "你是一名严谨的中国英语语法老师，为初中/高中学生出题。只输出合法 JSON 数组，不要任何其他文字。"
    user = f"""请针对语法专题「{topic}」（{_level_label(level)}）出 {n} 道练习题，覆盖不同考查角度。

题型规则：
- choice：单选题。stem 为含空格 ___ 的题干，options 为 4 个选项，answer 为正确选项序号（0-3 整数）
- fill：用所给词的适当形式填空。stem 内用括号标注原形词，如 "She ___ (go) to school every day."
- correct：改错。stem 为含一处错误的句子，answer 为 "错误词 → 正确词"
- translate：汉译英。stem 为中文句子

每个元素格式：{{"type": "choice|fill|correct|translate", "stem": "...", "options": [...], "answer": ..., "explain": "用初中/高中生能听懂的中文解析"}}

要求：句子词汇量控制在该学段课标范围内；题目之间考查点不重复；答案唯一且明确。{avoid_text}"""
    content = _chat(system, user)
    out: list[dict] = []
    for row in _extract_json(content):
        if not isinstance(row, dict):
            continue
        if row.get("type") not in ("choice", "fill", "correct", "translate"):
            continue
        if not str(row.get("stem") or "").strip():
            continue
        if row.get("type") == "choice":
            opts = row.get("options")
            if not isinstance(opts, list) or len(opts) != 4:
                continue
        if row.get("answer") in (None, ""):
            continue
        row["explain"] = str(row.get("explain") or "").strip()
        out.append(row)
        if len(out) >= n:
            break
    if not out:
        raise ValueError("模型未返回有效题目，请重试")
    return out


def explain_mistake(level: str, topic: str, question: dict, user_answer: str) -> str:
    """针对一道错题，解释为什么错、正确答案为什么对。"""
    correct = question.get("answer")
    if question.get("type") == "choice":
        try:
            idx = int(correct)
            opts = question.get("options") or []
            correct = f"{chr(65 + idx)}. {opts[idx] if 0 <= idx < len(opts) else ''}"
        except (TypeError, ValueError):
            pass
    system = "你是一名耐心的中国英语语法老师，用初中/高中生能听懂的中文讲解，简明扼要，不超过 150 字。"
    user = f"""学生在学习语法专题「{topic}」（{_level_label(level)}）时做错了这道题：

题目：{question.get("stem")}
学生的答案：{user_answer or "（未作答）"}
正确答案：{correct}

请讲解：1) 考的语法点是什么；2) 学生为什么错（可能错在哪）；3) 正确答案为什么对。"""
    return _chat(system, user).strip() or "（模型未返回内容，请重试）"
