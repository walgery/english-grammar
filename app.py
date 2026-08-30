"""
英语语法学习助手（人教版 · 初中/高中）
- 语法地图：按专题浏览讲解卡
- 学练闭环：讲解 → 逐题练习（即时判分解析）→ 错题本
- LLM 助教：动态加题、错题讲解
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import streamlit as st

from src import content, llm, practice

ROOT = Path(__file__).resolve().parent
CONFIG_FILE = ROOT / "llm_config.json"

st.set_page_config(
    page_title="英语语法学习助手",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&family=Source+Serif+4:opsz,wght@8..60,500;8..60,700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans SC', sans-serif; -webkit-text-size-adjust: 100%; }
.main-title { font-family: 'Source Serif 4', serif; font-size: 1.8rem; font-weight: 700; margin-bottom: 0.2rem; }
.sub-title { color: #5a6570; margin-bottom: 1.2rem; }
.rule-card {
  background: linear-gradient(145deg, #f7fafc 0%, #eef4f8 100%);
  border-left: 4px solid #4a7d5b;
  border-radius: 0 12px 12px 0;
  padding: 1rem 1.2rem; margin: 0.7rem 0;
}
.example-en { font-family: 'Source Serif 4', Georgia, serif; font-size: 1.1rem; color: #1a2330; margin: 0.2rem 0; }
.example-zh { font-size: 0.95rem; color: #5a6a78; }
mark.grammar-hl { background: #ffd9a0; color: #1a2330; padding: 0 0.15em; border-radius: 3px; font-weight: 700; }
.signal-tag { display: inline-block; background: #e8f0e4; color: #2f6142; padding: 0.12rem 0.55rem; border-radius: 4px; margin: 0.15rem 0.2rem 0.15rem 0; font-size: 0.88rem; }
.pitfall-item { background: #fdf3f0; border-left: 3px solid #d07050; padding: 0.5rem 0.8rem; border-radius: 0 8px 8px 0; margin: 0.4rem 0; font-size: 0.95rem; }
.q-card { background: #fff; border: 1px solid #dde5ec; border-radius: 12px; padding: 1rem 1.2rem; margin: 0.8rem 0; }
.badge-ok { color: #2e7d4f; font-weight: 700; }
.badge-no { color: #c4442a; font-weight: 700; }
@media (max-width: 820px) {
  .main-title { font-size: 1.45rem; }
  .example-en { font-size: 1rem; }
  .stButton > button { min-height: 2.9rem; }
  .q-card { padding: 0.8rem 0.9rem; }
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

EXTRA_CSS = """
<style>
/* Hero 横幅 */
.hero {
  background: linear-gradient(135deg, #16324a 0%, #24523f 55%, #4a7d5b 100%);
  border-radius: 20px; padding: 26px 30px; margin-bottom: 20px;
  box-shadow: 0 10px 26px rgba(22, 50, 74, 0.25);
}
.hero h1 { color: #fff; font-size: 1.75rem; font-weight: 700; margin: 0 0 6px; letter-spacing: .02em; }
.hero p { color: #d7e6dd; margin: 0 0 10px; font-size: 1rem; }
.hero .pill {
  display: inline-block; background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.28);
  padding: .28rem .85rem; border-radius: 999px; margin: .18rem .45rem .18rem 0;
  font-size: .86rem; color: #eaf4ee;
}
/* 年级分组标题 */
.grade-title {
  display: flex; align-items: center; gap: .5rem;
  font-size: 1.02rem; font-weight: 700; color: #2f6142;
  margin: 1.4rem 0 .55rem;
}
.grade-title::after { content: ""; flex: 1; height: 1px; background: linear-gradient(90deg, #cfe0d4, transparent); }
/* 全局按钮卡片化 */
div[data-testid="stButton"] > button {
  border-radius: 12px;
  border: 1px solid #dfe9e2;
  box-shadow: 0 2px 6px rgba(30, 58, 76, .07);
  transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease;
}
div[data-testid="stButton"] > button:hover {
  transform: translateY(-2px);
  border-color: #4a7d5b;
  box-shadow: 0 8px 18px rgba(30, 58, 76, .14);
}
div[data-testid="stButton"] > button[kind="primary"] {
  background: linear-gradient(135deg, #4a7d5b, #2f6142);
  border: none;
}
/* 顶部用户栏 */
.user-bar {
  display: flex; align-items: center; gap: .5rem;
  background: #fff; border: 1px solid #dfe9e2; border-radius: 999px;
  padding: .38rem 1rem; margin-bottom: .8rem;
  font-size: .92rem; color: #2a3b47;
  box-shadow: 0 1px 4px rgba(30, 58, 76, .06);
}
.ub-avatar { font-size: 1rem; }
.ub-hint { color: #8a97a5; font-size: .82rem; margin-left: auto; }
@media (max-width: 640px) { .ub-hint { display: none; } }
/* 专题学习页横幅 */
.study-hero {
  background: linear-gradient(135deg, #16324a 0%, #24523f 55%, #4a7d5b 100%);
  border-radius: 20px; padding: 24px 30px; margin-bottom: 20px;
  box-shadow: 0 10px 26px rgba(22, 50, 74, 0.25);
}
.study-hero .sh-tag {
  font-size: .82rem; letter-spacing: .14em; color: #cfe0d4;
  text-transform: uppercase; margin-bottom: 4px; font-weight: 500;
}
.study-hero h1 { color: #fff; font-size: 1.7rem; font-weight: 700; margin: 0 0 8px; }
.study-hero p { color: #d7e6dd; font-size: .98rem; margin: 0; line-height: 1.7; }
/* 小节标题（各小节不同功能色） */
.sec-title {
  display: flex; align-items: center; gap: .5rem;
  font-size: 1.06rem; font-weight: 700; color: #24523f;
  margin: 1.6rem 0 .7rem;
}
.sec-title::before {
  content: ""; width: 5px; height: 1.05em; border-radius: 3px;
  background: linear-gradient(180deg, #4a7d5b, #2f6142);
}
.sec-title::after { content: ""; flex: 1; height: 1px; background: linear-gradient(90deg, #cfe0d4, transparent); }
.sec-title.blue::before { background: linear-gradient(180deg, #3a7ca5, #1d5a8a); }
.sec-title.amber::before { background: linear-gradient(180deg, #e8a13c, #c47d1a); }
.sec-title.red::before { background: linear-gradient(180deg, #d07050, #b34a35); }
.sec-title.purple::before { background: linear-gradient(180deg, #7c5cbf, #5a3d94); }
/* 术语 + 释义：蓝色英文强调，灰色括号释义弱化 */
.term { white-space: nowrap; }
.term-en { color: #1d5a8a; font-weight: 700; font-family: 'Source Serif 4', Georgia, serif; }
.term-zh { color: #8a97a5; font-size: .88em; }
/* 易错点染色 */
.pitfall-item {
  background: #fdf3f0; border-left: 4px solid #d07050;
  border-radius: 0 10px 10px 0; padding: .65rem 1rem; margin: .5rem 0;
  font-size: .97rem; line-height: 1.75;
}
.pit-wrong { color: #c4442a; }
.pit-right { color: #2e7d4f; font-weight: 700; }
/* 对比表（双色表头：左绿右蓝） */
table.cmp { width: 100%; border-collapse: separate; border-spacing: 0; border: 1px solid #dfe9e2; border-radius: 12px; overflow: hidden; margin: .4rem 0; }
table.cmp th { padding: .6rem 1rem; text-align: left; font-size: .98rem; color: #fff; }
table.cmp th.l { background: linear-gradient(135deg, #4a7d5b, #2f6142); }
table.cmp th.r { background: linear-gradient(135deg, #3a7ca5, #1d5a8a); }
table.cmp td { padding: .6rem 1rem; border-top: 1px solid #e6eee8; font-size: .96rem; line-height: 1.6; }
table.cmp tbody tr:nth-child(even) td { background: #f4f9f6; }
/* 标志词标签：琥珀色系（覆盖早前定义） */
.signal-tag {
  display: inline-block; background: #fff7e8; border: 1px solid #ecd3a1;
  color: #8a5a12; padding: .3rem .85rem; border-radius: 999px;
  font-size: .92rem; font-weight: 500; margin: .15rem .35rem .15rem 0;
  box-shadow: 0 1px 3px rgba(30, 58, 76, .08);
}
@media (max-width: 820px) {
  .study-hero { padding: 18px; border-radius: 14px; }
  .study-hero h1 { font-size: 1.4rem; }
}
/* 规则块：编号徽章 + 标题 + 细节 */
.rule-block { margin: 1.1rem 0; }
.rule-head { display: flex; align-items: center; gap: .6rem; margin-bottom: .45rem; }
.rule-no {
  flex-shrink: 0; width: 30px; height: 30px; border-radius: 50%;
  background: linear-gradient(135deg, #3a7ca5, #1d5a8a); color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: .95rem;
}
.rule-title { font-size: 1.12rem; font-weight: 700; color: #16324a; line-height: 1.4; }
.rule-detail { line-height: 1.8; color: #2a3b47; font-size: 1rem; margin: .2rem 0 .5rem 0; }
/* 语法变化胶囊：go → goes */
.g-chip {
  display: inline-block; background: #e8f4ec; border: 1px solid #b7d6c3;
  color: #1f5c38; border-radius: 6px; padding: .02em .45em; margin: 0 .08em;
  font-family: 'Source Serif 4', Georgia, serif; font-weight: 600; font-size: .95em;
  white-space: nowrap;
}
/* 例句卡 */
.rule-card {
  background: #fff; border: 1px solid #e3ece6; border-left: 4px solid #3a7ca5;
  border-radius: 0 10px 10px 0; padding: .65rem 1rem; margin: .45rem 0;
}
.example-en { font-family: 'Source Serif 4', Georgia, serif; font-size: 1.12rem; font-weight: 500; color: #1a2330; margin: 0.1rem 0; }
.ex-no {
  display: inline-flex; width: 1.4em; height: 1.4em; border-radius: 50%;
  background: #e3f0f7; color: #1d5a8a; align-items: center; justify-content: center;
  font-size: .72em; font-weight: 600; margin-right: .5em; vertical-align: 2px;
  font-family: 'Noto Sans SC', sans-serif;
}
.example-zh { color: #7a8a95; font-size: .92rem; margin: 2px 0 0 0; }
/* 专题卡片按钮 */
div[data-testid="stButton"] > button.topic-btn {
  text-align: left;
  width: 100%;
  min-height: 108px;
  padding: 14px 16px;
  background: linear-gradient(160deg, #ffffff 0%, #f2f8f4 100%);
  font-size: .95rem;
}
div[data-testid="stButton"] > button.topic-btn p { line-height: 1.55; margin: 0 0 3px; }
@media (max-width: 820px) {
  .hero { padding: 18px 18px; border-radius: 14px; }
  .hero h1 { font-size: 1.35rem; }
  div[data-testid="stButton"] > button.topic-btn { min-height: 92px; }
}
</style>
"""
st.markdown(EXTRA_CSS, unsafe_allow_html=True)

# 框架英文界面中文化（同生词项目）
UI_JS = """
<script>
(function () {
  const map = [["Running","运行中"],["STOP","停止"],["Rerun","重新运行"],["Settings","设置"],["Print","打印"],["About","关于"],["Clear cache","清除缓存"],["Deploy","部署"],["Theme","主题"],["Wide mode","宽屏模式"],["OK","正常"]];
  function t(root){ if(!root)return; const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null); let n;
    while((n=w.nextNode())){ let v=n.nodeValue; if(!v||!v.trim())continue; let c=false;
      for(const [e,z] of map){ if(v.includes(e)){v=v.split(e).join(z);c=true;} } if(c)n.nodeValue=v; } }
  const ob=new MutationObserver(ms=>{for(const m of ms){ if(m.type==="characterData")t(m.target.parentElement); else if(m.addedNodes.length)t(m.target);}});
  function s(){ ob.observe(document.body,{childList:true,subtree:true,characterData:true}); t(document.body); }
  if(document.body)s(); else document.addEventListener("DOMContentLoaded",s);
})();
</script>
"""
st.markdown(UI_JS, unsafe_allow_html=True)

CONFIG_FILE = ROOT / "llm_config.json"

_LEVEL_LABEL = {"middle": "初中", "high": "高中"}


def load_llm_config() -> dict:
    data: dict = {}
    try:
        loaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            data = loaded
    except (OSError, ValueError):
        pass
    if not any(str(data.get(k) or "").strip() for k in ("api_key", "base_url", "model")):
        try:
            sec = st.secrets["llm"]
            for k in ("api_key", "base_url", "model"):
                v = sec.get(k)
                if v and not str(data.get(k) or "").strip():
                    data[k] = v
        except Exception:
            pass
    return {k: str(data.get(k) or "") for k in ("api_key", "base_url", "model")}


def save_llm_config(api_key: str, base_url: str, model: str) -> None:
    CONFIG_FILE.write_text(
        json.dumps({"api_key": api_key, "base_url": base_url, "model": model}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def init_state() -> None:
    defaults = {
        "level": "middle",
        "student": "",           # 学生姓名/学号，进度按学生分别保存
        "topic_id": "",
        "mode": "map",           # map / study / practice / result / wrong / wrong_practice
        "q_index": 0,
        "practice_qs": [],
        "practice_answers": [],
        "practice_checked": [],
        "practice_source": "bank",
        "wrong_practice_keys": [],
        "explain_cache": {},
        "show_export": False,
        "show_import": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _persist() -> None:
    """把练习现场保存到当前学生的数据目录（每提交/翻页后调用）。"""
    if not st.session_state.student or not st.session_state.practice_qs:
        return
    practice.save_practice(st.session_state.student, {
        "topic_id": st.session_state.topic_id,
        "mode": st.session_state.mode,
        "q_index": st.session_state.q_index,
        "practice_qs": st.session_state.practice_qs,
        "practice_answers": st.session_state.practice_answers,
        "practice_checked": st.session_state.practice_checked,
        "practice_source": st.session_state.practice_source,
        "wrong_practice_keys": st.session_state.wrong_practice_keys,
    })


def _restore_practice(student: str) -> bool:
    """恢复该学生的练习现场，返回是否成功。"""
    saved = practice.load_practice(student)
    if not saved:
        return False
    st.session_state.topic_id = saved.get("topic_id", "")
    st.session_state.mode = saved.get("mode", "map")
    st.session_state.q_index = saved.get("q_index", 0)
    st.session_state.practice_qs = saved.get("practice_qs", [])
    st.session_state.practice_answers = saved.get("practice_answers", [])
    st.session_state.practice_checked = saved.get("practice_checked", [])
    st.session_state.practice_source = saved.get("practice_source", "bank")
    st.session_state.wrong_practice_keys = saved.get("wrong_practice_keys", [])
    return True


def _student_gate() -> None:
    """学生身份入口：输入姓名/学号后按学生分别加载进度。"""
    st.markdown('<div class="hero"><h1>📐 英语语法学习助手</h1>'
                '<p>输入你的姓名或学号，进度会自动保存，下次接着学</p></div>',
                unsafe_allow_html=True)
    with st.container(border=True):
        name = st.text_input("姓名 / 学号", placeholder="例如：李明 或 20230101", max_chars=30)
        c1, _ = st.columns([1, 2])
        go = c1.button("开始学习", type="primary", use_container_width=True)
        if not go:
            return
        name = name.strip()
        if not name:
            st.error("请输入姓名或学号")
            return
        st.session_state.student = name
        if _restore_practice(name):
            st.toast(f"欢迎回来，{name}！已恢复上次的练习进度")
        else:
            st.toast(f"欢迎，{name}！")
        st.rerun()


def highlight_example(en: str, hl: str) -> str:
    """在例句中高亮语法结构/标志词（hl 支持逗号分隔多个片段）。"""
    import html as html_mod

    safe = html_mod.escape(en)
    if not hl:
        return safe
    for frag in [f.strip() for f in hl.split(",") if f.strip()]:
        if not frag:
            continue
        esc = html_mod.escape(frag)
        safe = safe.replace(esc, f'<mark class="grammar-hl">{esc}</mark>')
    return safe


def grammar_chips(text: str) -> str:
    """规则细节智能高亮（两条规则，互不干扰）：
    ① 箭头链「tall → taller → tallest」（两段或多段）→ 整体一个绿色胶囊；
    ② 「英文 + 全角括号中文释义」（如 what（什么））→ 蓝色术语 + 灰色释义。
    括号内是纯英文时不算释义，保持原样。
    """
    import html as html_mod

    s = html_mod.escape(text, quote=False)
    # 1) 箭头链（支持多段）
    s = re.sub(
        r"[A-Za-z][A-Za-z'’\-]*(?:\s*→\s*[A-Za-z][A-Za-z'’\-]*)+",
        lambda m: f'<span class="g-chip">{m.group(0)}</span>',
        s,
    )
    # 1b) more/most + 多音节词（比较级/最高级形式）
    s = re.sub(
        r"\b(?:more|most)\s+[A-Za-z][A-Za-z'’\-]*",
        lambda m: f'<span class="g-chip">{m.group(0)}</span>',
        s,
    )
    # 2) 术语 + 全角括号中文释义（括号内必须含中文，避免误吞纯英文括号）
    s = re.sub(
        r"([A-Za-z][A-Za-z0-9 '\-]*?)（([^（）]*[\u4e00-\u9fff][^（）]*)）",
        lambda m: (
            f'<span class="term"><span class="term-en">{m.group(1).strip()}</span>'
            f'<span class="term-zh">（{m.group(2)}）</span></span>'
        ),
        s,
    )
    return s


# —— 页面：语法地图 ——


def page_map() -> None:
    level = st.session_state.level
    student = st.session_state.student
    topics = content.load_level(level)
    stats = practice.load_stats(student)
    book = practice.load_book(student)
    if not topics:
        st.warning("暂无该学段内容")
        return

    # 统计
    wrong_by_topic: dict[str, int] = {}
    for k in book:
        tid = k.split(":")[0]
        wrong_by_topic[tid] = wrong_by_topic.get(tid, 0) + 1
    progs = [content.topic_progress(t["id"], stats) for t in topics]
    learned = sum(1 for p in progs if p >= 0)
    mastered = sum(1 for p in progs if p >= 0.8)
    total_wrong = sum(wrong_by_topic.values())
    total_q = sum(len(t["questions"]) for t in topics)

    # Hero 横幅
    pills = (
        f'<span class="pill">📘 {len(topics)} 个专题</span>'
        f'<span class="pill">📝 {total_q} 道精题</span>'
        f'<span class="pill">🎯 已学 {learned} / {len(topics)}</span>'
        f'<span class="pill">⭐ 已掌握 {mastered}</span>'
        f'<span class="pill">📕 错题 {total_wrong}</span>'
    )
    st.markdown(
        f"""<div class="hero">
            <h1>📐 英语语法学习助手</h1>
            <p>人教版{_LEVEL_LABEL[level]} · 学 → 练 → 错题复盘</p>
            <div>{pills}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    # 按分类渲染（由易到难），类内按难度排序；当前学段没有的专题自动隐藏
    all_topics = {t["id"]: t for t in topics}
    for cat_icon, cat_name, cat_desc, ids in content.CATEGORIES:
        ts = [all_topics[i] for i in ids if i in all_topics]
        if not ts:
            continue
        st.markdown(
            f'<div class="grade-title">{cat_icon} {cat_name}'
            f'<span style="font-weight:400;font-size:.88rem;color:#8a97a5;margin-left:.3rem;">{cat_desc}</span></div>',
            unsafe_allow_html=True,
        )
        cols_per_row = 3
        for row_start in range(0, len(ts), cols_per_row):
            cols = st.columns(cols_per_row)
            for i, t in enumerate(ts[row_start : row_start + cols_per_row]):
                with cols[i]:
                    prog = content.topic_progress(t["id"], stats)
                    if prog < 0:
                        prog_text = "未开始"
                    else:
                        prog_text = f"掌握度 {int(prog * 100)}%"
                    wrong_n = wrong_by_topic.get(t["id"], 0)
                    wrong_text = f" · ⚠️ 错题 {wrong_n}" if wrong_n else ""
                    icon = content.topic_icon(t["id"])
                    if st.button(
                        f"{icon} **{t['topic']}**\n\n"
                        f"{len(t['questions'])} 题 · {prog_text}{wrong_text}",
                        key=f"map_{t['id']}",
                        use_container_width=True,
                    ):
                        st.session_state.topic_id = t["id"]
                        st.session_state.mode = "study"
                        st.session_state.q_index = 0
                        st.session_state.practice_qs = []
                        st.rerun()


# —— 页面：学习卡 + 练习入口 ——


def _pitfall_html(text: str) -> str:
    """易错点上色：→ 左侧（错误写法）红色，右侧（正确写法）绿色加粗。"""
    import html as html_mod

    s = html_mod.escape(text, quote=False)
    if "→" in s and ("❌" in s or "✗" in s):
        left, right = s.split("→", 1)
        left = left.strip()
        right = right.strip()
        # 原文已带 ✓ 的去掉，避免染色后再加一个变成双勾
        if right.startswith(("✓", "✔")):
            right = right[1:].strip()
        return (
            f'<span class="pit-wrong">{left} →</span> '
            f'<span class="pit-right">✓ {right}</span>'
        )
    return s


def page_study(topic: dict) -> None:
    if st.button("← 返回语法地图", key="back_map"):
        st.session_state.mode = "map"
        st.rerun()

    # 专题横幅：图标 + 标题 + 摘要 + 教材单元
    icon = content.topic_icon(topic["id"])
    unit = topic.get("unit", "")
    summary = topic.get("summary", "")
    st.markdown(
        f"""<div class="study-hero">
            <div class="sh-tag">{icon} 语法专题{(" · " + unit) if unit else ""}</div>
            <h1>{topic["topic"]}</h1>
            {f'<p>{summary}</p>' if summary else ""}
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sec-title blue">📖 规则讲解</div>', unsafe_allow_html=True)
    for i, rule in enumerate(topic.get("rules", []), start=1):
        detail_html = grammar_chips(rule.get("detail", "")) if rule.get("detail") else ""
        block = (
            f'<div class="rule-block">'
            f'<div class="rule-head"><span class="rule-no">{i}</span>'
            f'<span class="rule-title">{rule.get("title", "")}</span></div>'
        )
        if detail_html:
            block += f'<div class="rule-detail">{detail_html}</div>'
        block += "</div>"
        st.markdown(block, unsafe_allow_html=True)
        for j, ex in enumerate(rule.get("examples", []), start=1):
            st.markdown(
                f'<div class="rule-card">'
                f'<div class="example-en"><span class="ex-no">{j}</span>{highlight_example(ex.get("en", ""), ex.get("highlight", ""))}</div>'
                f'<div class="example-zh">{ex.get("zh", "")}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="sec-title amber">🔍 标志词（看到它们优先想到这个时态/结构）</div>', unsafe_allow_html=True)
    st.markdown("".join(f'<span class="signal-tag">{s}</span>' for s in topic["signals"]), unsafe_allow_html=True)

    if topic.get("pitfalls"):
        st.markdown('<div class="sec-title red">⚠️ 易错点</div>', unsafe_allow_html=True)
        for p in topic["pitfalls"]:
            st.markdown(f'<div class="pitfall-item">{_pitfall_html(p)}</div>', unsafe_allow_html=True)

    cmp = topic.get("compare")
    if cmp:
        st.markdown('<div class="sec-title purple">📊 易混对比</div>', unsafe_allow_html=True)
        rows_html = "".join(
            f'<tr><td>{row.get("l", "")}</td><td>{row.get("r", "")}</td></tr>'
            for row in cmp.get("rows", [])
        )
        st.markdown(
            f'<table class="cmp"><thead><tr><th class="l">{cmp.get("left", "")}</th><th class="r">{cmp.get("right", "")}</th></tr></thead>'
            f"<tbody>{rows_html}</tbody></table>",
            unsafe_allow_html=True,
        )

    st.markdown('<div class="sec-title">✍️ 开始练习</div>', unsafe_allow_html=True)
    col1, col2, _ = st.columns([2, 2, 3])
    with col1:
        if st.button("📝 开始练习（题库）", type="primary", use_container_width=True):
            st.session_state.practice_qs = [dict(q) for q in topic["questions"]]
            st.session_state.practice_source = "bank"
            st.session_state.q_index = 0
            st.session_state.practice_answers = [""] * len(topic["questions"])
            st.session_state.practice_checked = [False] * len(topic["questions"])
            st.session_state.mode = "practice"
            st.rerun()
    with col2:
        ai_on = llm.is_configured()
        if st.button(
            "🤖 AI 出 5 道新题",
            use_container_width=True,
            disabled=not ai_on,
            help="由大模型针对本专题动态出题" if ai_on else "请先在侧边栏配置大模型",
        ):
            with st.spinner("AI 正在出题…"):
                try:
                    bank_stems = [q["stem"] for q in topic["questions"]]
                    new_qs = llm.gen_questions(st.session_state.level, topic["topic"], 5, avoid=bank_stems)
                except Exception as e:
                    st.error(f"AI 出题失败：{e}")
                    return
            merged = [dict(q) for q in topic["questions"]] + new_qs
            st.session_state.practice_qs = merged
            st.session_state.practice_source = "bank+ai"
            st.session_state.q_index = 0
            st.session_state.practice_answers = [""] * len(merged)
            st.session_state.practice_checked = [False] * len(merged)
            st.session_state.mode = "practice"
            st.rerun()


# —— 页面：练习 ——


def render_question(topic: dict, idx: int, q: dict) -> None:
    n = len(st.session_state.practice_qs)
    type_name = practice.QUESTION_TYPES.get(q.get("type", ""), q.get("type", ""))
    ai_mark = ""
    if st.session_state.practice_source in ("bank+ai", "more") and idx >= n - 5 and st.session_state.practice_source != "wrong":
        ai_mark = " · 🤖 AI 出题"
    st.markdown(
        f'<div class="q-card" style="border:none;padding:0;margin:0;">'
        f'<div style="color:#6a7a88;font-size:0.88rem;margin-bottom:0.3rem;">第 {idx + 1} / {n} 题 · {type_name}{ai_mark}</div>'
        f'<div style="font-size:1.12rem;font-weight:500;">{q["stem"]}</div></div>',
        unsafe_allow_html=True,
    )
    checked = st.session_state.practice_checked[idx]
    user = st.session_state.practice_answers[idx]

    if q.get("type") == "choice":
        opts = q.get("options") or []
        labels = [f"{chr(65 + i)}. {o}" for i, o in enumerate(opts)]
        chosen = st.radio(
            "选项",
            labels,
            index=int(user) if checked and user.isdigit() and int(user) < len(labels) else None,
            label_visibility="collapsed",
            disabled=checked,
        )
        if not checked and chosen is not None:
            st.session_state.practice_answers[idx] = str(labels.index(chosen))
    else:
        new_val = st.text_input(
            "你的答案" if q.get("type") != "translate" else "英文翻译",
            value=user,
            disabled=checked,
            key=f"ans_{st.session_state.practice_source}_{idx}",
        )
        if not checked:
            st.session_state.practice_answers[idx] = new_val

    if not checked:
        if st.button("提交本题", key=f"check_{idx}", type="primary"):
            ok = practice.check_answer(q, st.session_state.practice_answers[idx])
            st.session_state.practice_checked[idx] = True
            practice.record_attempt(st.session_state.student, topic["id"], ok)
            if not ok:
                practice.record_wrong(st.session_state.student, topic["id"], idx, q, st.session_state.practice_answers[idx])
            _persist()
            st.rerun()
        return

    correct = practice.check_answer(q, st.session_state.practice_answers[idx])
    correct_text = q.get("answer")
    if q.get("type") == "choice" and str(correct_text).isdigit():
        i2 = int(correct_text)
        opts = q.get("options") or []
        correct_text = f"{chr(65 + i2)}. {opts[i2] if i2 < len(opts) else ''}"
    if correct:
        st.markdown('<span class="badge-ok">✓ 回答正确</span>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<span class="badge-no">✗ 回答错误</span>　你的答案：{user or "（空）"}　｜　正确答案：<b>{correct_text}</b>',
            unsafe_allow_html=True,
        )
        cache_key = f"{topic['id']}:{idx}:{st.session_state.practice_answers[idx]}"
        if cache_key in st.session_state.explain_cache:
            st.info(st.session_state.explain_cache[cache_key])
        elif llm.is_configured():
            if st.button("🤖 问老师：我为什么错了", key=f"explain_{idx}"):
                with st.spinner("老师思考中…"):
                    try:
                        exp = llm.explain_mistake(
                            st.session_state.level, topic["topic"], q, st.session_state.practice_answers[idx]
                        )
                    except Exception as e:
                        st.error(f"讲解失败：{e}")
                        return
                st.session_state.explain_cache[cache_key] = exp
                st.rerun()
    if q.get("explain"):
        with st.expander("📖 题目解析"):
            st.write(q["explain"])

    nav1, nav2, _ = st.columns([1, 1, 3])
    with nav1:
        if idx > 0 and st.button("← 上一题", key=f"prev_{idx}"):
            st.session_state.q_index = idx - 1
            _persist()
            st.rerun()
    with nav2:
        if idx < n - 1 and st.button("下一题 →", key=f"next_{idx}"):
            st.session_state.q_index = idx + 1
            _persist()
            st.rerun()
    if idx == n - 1:
        if st.button("✅ 完成本组练习，查看结果", type="primary", use_container_width=True):
            st.session_state.mode = "result"
            practice.clear_practice(st.session_state.student)  # 本组已完成，无需再恢复现场
            st.rerun()


def page_practice(topic: dict) -> None:
    qs = st.session_state.practice_qs
    idx = st.session_state.q_index
    if not qs or idx >= len(qs):
        st.session_state.mode = "study"
        st.rerun()
    if st.button("← 返回讲解", key="back_study"):
        st.session_state.mode = "study"
        st.rerun()
    done = sum(1 for c in st.session_state.practice_checked if c)
    st.progress(done / len(qs), text=f"已完成 {done}/{len(qs)} 题")
    render_question(topic, idx, qs[idx])


def page_result(topic: dict) -> None:
    qs = st.session_state.practice_qs
    total = len(qs)
    correct = sum(
        1 for i, q in enumerate(qs)
        if st.session_state.practice_checked[i] and practice.check_answer(q, st.session_state.practice_answers[i])
    )
    st.markdown('<div class="main-title">练习结果</div>', unsafe_allow_html=True)
    pct = int(correct / total * 100) if total else 0
    emoji = "🏆" if pct >= 90 else "👍" if pct >= 70 else "💪" if pct >= 50 else "📖"
    st.success(f"{emoji} {topic['topic']}：答对 **{correct} / {total}**（{pct}%）")
    if pct == 100:
        st.balloons()
    st.markdown("**逐题回顾**")
    for i, q in enumerate(qs):
        ok = st.session_state.practice_checked[i] and practice.check_answer(q, st.session_state.practice_answers[i])
        mark = "✓" if ok else "✗"
        st.markdown(f"- {mark} {q['stem']}" + ("" if ok else f"　正确答案：**{q.get('answer')}**"))
    c1, c2, c3, _ = st.columns([2, 2, 2, 2])
    with c1:
        if st.button("🔄 再练一遍", use_container_width=True):
            st.session_state.q_index = 0
            st.session_state.practice_answers = [""] * len(qs)
            st.session_state.practice_checked = [False] * len(qs)
            st.session_state.mode = "practice"
            st.rerun()
    with c2:
        ai_on = llm.is_configured()
        if st.button("🤖 AI 再出 5 题", use_container_width=True, disabled=not ai_on):
            with st.spinner("AI 正在出题…"):
                try:
                    new_qs = llm.gen_questions(
                        st.session_state.level, topic["topic"], 5, avoid=[q["stem"] for q in qs]
                    )
                except Exception as e:
                    st.error(f"AI 出题失败：{e}")
                    return
            st.session_state.practice_qs = qs + new_qs
            st.session_state.practice_source = "more"
            st.session_state.q_index = len(qs)
            st.session_state.practice_answers += [""] * len(new_qs)
            st.session_state.practice_checked += [False] * len(new_qs)
            st.session_state.mode = "practice"
            practice.clear_practice(st.session_state.student)
            st.rerun()
    with c3:
        if st.button("📚 返回语法地图", use_container_width=True):
            st.session_state.mode = "map"
            st.rerun()


# —— 页面：错题本 ——


def _choice_text(q: dict, val) -> str:
    """choice 题的序号答案转成「A. 选项」友好文本；其他情况原样返回。"""
    if val is None or val == "":
        return ""
    s = str(val)
    if q.get("type") == "choice" and s.isdigit():
        i = int(s)
        opts = q.get("options") or []
        if 0 <= i < len(opts):
            return f"{chr(65 + i)}. {opts[i]}"
    return s


def _book_to_markdown(book: dict, topic_map: dict) -> str:
    """导出为 Markdown 复习文档：人读内容 + 每题内嵌可再导入的数据块。"""
    lines = [
        "# 英语错题本\n",
        "> 本文档可直接重新导入本应用（每题附带「数据」折叠块，导入时请勿删除）。\n",
    ]
    for key, rec in sorted(book.items(), key=lambda kv: kv[0]):
        q = rec.get("question", {})
        t = topic_map.get(rec.get("topic_id", ""))
        tname = t["topic"] if t else rec.get("topic_id", "未知专题")
        ans = q.get("answer")
        if q.get("type") == "choice" and str(ans).isdigit():
            i4 = int(ans)
            opts = q.get("options") or []
            ans = f"{chr(65 + i4)}. {opts[i4] if i4 < len(opts) else ''}"
        lines.append(f"## {tname}")
        lines.append(f"- **题目**：{q.get('stem', '')}")
        lines.append(f"- **正确答案**：{_choice_text(q, ans)}")
        lines.append(f"- **错误次数**：{rec.get('wrong_times', 1)}")
        if rec.get("last_user_answer"):
            lines.append(f"- **上次答案**：{_choice_text(q, rec['last_user_answer'])}")
        if q.get("explain"):
            lines.append(f"- **解析**：{q['explain']}")
        meta = json.dumps({
            "key": key,
            "topic_id": rec.get("topic_id", ""),
            "question": q,
            "wrong_times": rec.get("wrong_times", 1),
            "last_user_answer": rec.get("last_user_answer", ""),
        }, ensure_ascii=False)
        lines.append("")
        lines.append("<details><summary>▸ 数据（供导入使用）</summary>\n")
        lines.append("```json")
        lines.append(meta)
        lines.append("```")
        lines.append("\n</details>\n")
    return "\n".join(lines)


def _book_to_html(book: dict, topic_map: dict) -> str:
    """导出为自包含 HTML 复习网页：排版精美、可直接打印，内嵌可再导入的数据。"""
    import html as html_mod

    cards: list[str] = []
    datas: list[str] = []
    for i, (key, rec) in enumerate(sorted(book.items(), key=lambda kv: kv[0]), start=1):
        q = rec.get("question", {})
        t = topic_map.get(rec.get("topic_id", ""))
        tname = html_mod.escape(t["topic"] if t else rec.get("topic_id", "未知专题"))
        ans = _choice_text(q, q.get("answer"))
        extra = ""
        if rec.get("last_user_answer"):
            extra += f'<p class="muted">上次答案：{html_mod.escape(_choice_text(q, rec["last_user_answer"]))}</p>'
        if q.get("explain"):
            extra += f'<p class="explain">解析：{html_mod.escape(str(q["explain"]))}</p>'
        cards.append(
            f'<div class="card"><div class="tag">{i}. {tname} · 错 {rec.get("wrong_times", 1)} 次</div>'
            f'<p class="stem">{html_mod.escape(str(q.get("stem", "")))}</p>'
            f'<p class="ans"><b>正确答案</b>：{ans}</p>{extra}</div>'
        )
        datas.append(
            '<script type="application/json" class="qd">'
            + json.dumps({
                "key": key,
                "topic_id": rec.get("topic_id", ""),
                "question": q,
                "wrong_times": rec.get("wrong_times", 1),
                "last_user_answer": rec.get("last_user_answer", ""),
            }, ensure_ascii=False)
            + "</script>"
        )
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>英语错题本</title>
<style>
body {{ font-family: 'Noto Sans SC', 'PingFang SC', sans-serif; max-width: 860px; margin: 0 auto; padding: 24px; color: #1a2330; background: #f6f8fa; }}
h1 {{ font-size: 1.6rem; }}
.card {{ background: #fff; border: 1px solid #dde5ec; border-left: 4px solid #2f6f8f; border-radius: 10px; padding: 14px 18px; margin: 14px 0; }}
.tag {{ font-size: 0.85rem; color: #6a7a88; margin-bottom: 6px; }}
.stem {{ font-size: 1.05rem; font-weight: 500; }}
.ans {{ margin: 6px 0 2px; }}
.muted {{ color: #8a97a5; font-size: 0.9rem; margin: 2px 0; }}
.explain {{ background: #f0f6f1; padding: 8px 12px; border-radius: 8px; font-size: 0.92rem; }}
@media print {{ body {{ background: #fff; }} .card {{ page-break-inside: avoid; }} }}
</style></head><body>
<h1>📐 英语错题本</h1>
{''.join(cards)}
{''.join(datas)}
</body></html>"""


def _parse_import_book(filename: str, text: str) -> dict:
    """按文件类型解析导入的错题本：JSON / Markdown / HTML。"""
    name = (filename or "").lower()
    if name.endswith(".json"):
        data = json.loads(text)
        if not isinstance(data, dict) or not data:
            raise ValueError("JSON 内容应为非空错题本对象")
        return data
    if name.endswith((".md", ".markdown")):
        out: dict = {}
        for m in re.finditer(r"```json\s*(\{[\s\S]*?\})\s*```", text):
            try:
                rec = json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
            key = rec.get("key")
            q = rec.get("question")
            if key and isinstance(q, dict) and q.get("stem"):
                out[str(key)] = {
                    "topic_id": rec.get("topic_id", ""),
                    "question": q,
                    "wrong_times": rec.get("wrong_times", 1),
                    "last_user_answer": rec.get("last_user_answer", ""),
                }
        if not out:
            raise ValueError("未在 Markdown 中找到题目数据（导入时请使用本应用导出的文件，并保留每题的「数据」折叠块）")
        return out
    if name.endswith(".html"):
        import html as html_mod

        out2: dict = {}
        for m in re.finditer(r'<script type="application/json" class="qd">([\s\S]*?)</script>', text):
            try:
                rec = json.loads(html_mod.unescape(m.group(1)))
            except (json.JSONDecodeError, ValueError):
                continue
            key = rec.get("key")
            q = rec.get("question")
            if key and isinstance(q, dict) and q.get("stem"):
                out2[str(key)] = {
                    "topic_id": rec.get("topic_id", ""),
                    "question": q,
                    "wrong_times": rec.get("wrong_times", 1),
                    "last_user_answer": rec.get("last_user_answer", ""),
                }
        if not out2:
            raise ValueError("未在 HTML 中找到题目数据（导入时请使用本应用导出的文件）")
        return out2
    raise ValueError("不支持的格式。请使用本应用导出的 JSON / Markdown / HTML 文件。")


def _import_export_block(book: dict, student: str) -> None:
    """错题本导入导出：一个导出按钮 → 选择格式 → 下载；导入同样按钮切换。"""
    topic_map = {t["id"]: t for lvl in ("middle", "high") for t in content.load_level(lvl)}
    colE, colI, _ = st.columns([1, 1, 2])
    with colE:
        if st.button("📤 导出错题本", use_container_width=True, disabled=not book,
                     help=("" if book else "错题本为空")):
            st.session_state.show_export = not st.session_state.show_export
            st.session_state.show_import = False
            st.rerun()
    with colI:
        if st.button("📥 导入错题本", use_container_width=True):
            st.session_state.show_import = not st.session_state.show_import
            st.session_state.show_export = False
            st.rerun()

    if st.session_state.show_export:
        if not book:
            st.info("错题本为空，先去练习攒些错题吧。")
        else:
            st.markdown("**选择导出格式**")
            fmt = st.radio(
                "导出格式",
                [
                    "Markdown — 复习文档，可重新导入",
                    "HTML — 精美网页，可重新导入 / 打印",
                ],
                label_visibility="collapsed",
            )
            if fmt.startswith("Markdown"):
                data, fname, mime = _book_to_markdown(book, topic_map), "wrong_book.md", "text/markdown"
            else:
                data, fname, mime = _book_to_html(book, topic_map), "wrong_book.html", "text/html"
            st.download_button("⬇ 下载文件", data=data, file_name=fname, mime=mime, type="primary", use_container_width=True)
            st.caption("提示：文件内含每题的隐藏数据块，之后可直接导回本应用恢复错题。")

    if st.session_state.show_import:
        st.markdown("**导入错题本文件**（支持 JSON / Markdown / HTML；重复题目保留错得更多的记录）")
        with st.form("import_book_form", clear_on_submit=True):
            f = st.file_uploader(
                "选择错题本文件",
                type=["json", "md", "markdown", "html"],
                label_visibility="collapsed",
            )
            mode = st.radio(
                "导入方式",
                ["合并到现有错题本（推荐）", "覆盖现有错题本"],
                horizontal=True,
            )
            submitted = st.form_submit_button("开始导入", use_container_width=True)
        if submitted and f is not None:
            try:
                imported = _parse_import_book(f.name, f.getvalue().decode("utf-8-sig"))
            except UnicodeDecodeError:
                st.error("导入失败：文件编码无法识别（请使用 UTF-8 编码的导出文件）")
                return
            except ValueError as e:
                st.error(f"导入失败：{e}")
                return
            except Exception as e:
                st.error(f"导入失败：{type(e).__name__}: {e}")
                return
            if mode.startswith("覆盖"):
                merged, n = imported, len(imported)
            else:
                merged, n = practice.merge_book(book, imported)
            practice.save_book(merged, student)
            st.success(f"导入完成：共 {len(merged)} 条错题（本次新增/更新 {n} 条）")
            st.rerun()


def page_wrong() -> None:
    st.markdown('<div class="main-title">📕 错题本</div>', unsafe_allow_html=True)
    student = st.session_state.student
    book = practice.load_book(student)
    _import_export_block(book, student)
    if not book:
        st.success("还没有错题，保持下去！")
        return
    level = st.session_state.level
    prefix = "m" if level == "middle" else "h"
    topic_map = {t["id"]: t for t in content.load_level(level)}
    entries = sorted(
        ((k, v) for k, v in book.items() if k.startswith(prefix)),
        key=lambda kv: -kv[1].get("wrong_times", 0),
    )
    if not entries:
        st.info("当前学段暂无错题")
        return

    remove_key = ""
    for key, rec in entries:
        q = rec.get("question", {})
        t = topic_map.get(rec.get("topic_id", ""))
        tname = t["topic"] if t else rec.get("topic_id", "")
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"**[{tname}]** {q.get('stem', '')}")
                ua = _choice_text(q, rec.get("last_user_answer", ""))
                ans = _choice_text(q, q.get("answer"))
                st.caption(f"上次答案：{ua or '（空）'} ｜ 正确答案：{ans} ｜ 错过 {rec.get('wrong_times', 1)} 次")
                if q.get("explain"):
                    st.caption(f"解析：{q['explain']}")
            with c2:
                if st.button("移除", key=f"rm_{key}"):
                    remove_key = key
    if remove_key:
        practice.remove_wrong(student, remove_key)
        st.rerun()

    st.markdown("---")
    if st.button("🔁 重练全部错题（当前学段）", type="primary", use_container_width=True):
        qs: list[dict] = [rec["question"] for _, rec in entries]
        idx_list = [k for k, _ in entries]
        st.session_state.practice_qs = qs
        st.session_state.practice_source = "wrong"
        st.session_state.wrong_practice_keys = idx_list
        st.session_state.q_index = 0
        st.session_state.practice_answers = [""] * len(qs)
        st.session_state.practice_checked = [False] * len(qs)
        st.session_state.mode = "wrong_practice"
        st.rerun()


def page_wrong_practice() -> None:
    qs = st.session_state.practice_qs
    idx = st.session_state.q_index
    keys = st.session_state.wrong_practice_keys
    if not qs or idx >= len(qs):
        st.session_state.mode = "wrong"
        st.rerun()
    if st.button("← 返回错题本", key="back_wrong"):
        st.session_state.mode = "wrong"
        st.rerun()
    done = sum(1 for c in st.session_state.practice_checked if c)
    st.progress(done / len(qs), text=f"错题重练 {done}/{len(qs)}")

    q = qs[idx]
    key = keys[idx] if idx < len(keys) else ""
    topic_id = key.split(":")[0]
    real_topic = content.get_topic(st.session_state.level, topic_id) or {"id": "wrong", "topic": "错题重练"}
    render_question(real_topic, idx, q)
    if st.session_state.practice_checked[idx] and practice.check_answer(q, st.session_state.practice_answers[idx]):
        practice.remove_wrong(st.session_state.student, key)


def sidebar() -> None:
    with st.sidebar:
        st.markdown("### 设置")
        level = st.radio(
            "学段（人教版）",
            options=["middle", "high"],
            format_func=lambda x: "初中" if x == "middle" else "高中",
            index=0 if st.session_state.level == "middle" else 1,
        )
        st.session_state.level = level

        st.markdown("---")
        st.markdown("### 大模型（AI 出题 / 讲解）")
        cfg = load_llm_config()
        has_cfg = bool(cfg["api_key"])
        st.caption("配置来源：" + ("已保存 ✓" if has_cfg else "未配置（可选功能）"))
        api_key_input = st.text_input(
            "API 密钥",
            value="",
            type="password",
            placeholder=("已保存 ✓ 留空沿用" if has_cfg else "输入密钥"),
            key="llm_key_input",
        )
        base_url = st.text_input(
            "接口地址（可选）",
            value=cfg["base_url"],
            placeholder="如 https://open.bigmodel.cn/api/paas/v4",
            key="llm_base_input",
        )
        model = st.text_input(
            "模型名",
            value=cfg["model"] or "gpt-4o-mini",
            key="llm_model_input",
        )
        c1, c2 = st.columns(2)
        if c1.button("保存配置", use_container_width=True):
            save_llm_config(
                api_key_input.strip() or cfg["api_key"],
                base_url.strip() or cfg["base_url"],
                model.strip() or cfg["model"],
            )
            st.toast("已保存")
        if c2.button("清除", disabled=not has_cfg, use_container_width=True):
            try:
                os.remove(CONFIG_FILE)
            except OSError:
                pass
            st.toast("已清除")
        st.caption("AI 出题 / 讲解为可选功能，不配置也能使用题库练习。")
        st.markdown("---")
        st.caption("人教版教材 · 初中 / 高中语法全覆盖")


def main() -> None:
    init_state()
    if not st.session_state.student:
        _student_gate()
        return

    # 顶部用户栏：所有页面可见
    st.markdown(
        f'<div class="user-bar"><span class="ub-avatar">👤</span>'
        f'<span>当前学生：<b>{st.session_state.student}</b></span>'
        f'<span class="ub-hint">进度已自动保存，下次登录输入同一姓名即可继续</span></div>',
        unsafe_allow_html=True,
    )
    sidebar()

    page = st.radio(
        "导航",
        ["语法地图", "错题本"],
        horizontal=True,
        label_visibility="collapsed",
    )
    if page == "错题本":
        page_wrong()
        return

    topic = content.get_topic(st.session_state.level, st.session_state.topic_id)
    mode = st.session_state.mode
    if mode == "practice" and topic:
        page_practice(topic)
    elif mode == "result" and topic:
        page_result(topic)
    elif mode == "wrong_practice" and st.session_state.practice_qs:
        page_wrong_practice()
    elif mode == "study" and topic:
        page_study(topic)
    else:
        page_map()


if __name__ == "__main__":
    main()
