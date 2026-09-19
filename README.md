# 英语语法学习助手（人教版 · 初中 / 高中）

帮助初中和高中生系统学习英语语法的 Streamlit 应用。
教材依据**人教版（PEP）**，覆盖初中 18 个 + 高中 15 个共 **33 个语法专题**、**300 道预写精题**。

## 功能

- **语法地图**：按专题浏览，显示学习掌握度与错题数
- **学习卡**：规则讲解 + 例句结构高亮 + 标志词 + 易错点 + 易混对比
- **专项练习**：单选 / 填空 / 改错 / 翻译四种题型，即时判分 + 逐题解析
- **错题本**：自动收集错题，答对后自动移除，支持错题重练
- **AI 助教**（可选）：动态出题、错题讲解（配置大模型后可用）
- **学段切换**：初中（七~九年级）/ 高中（必修~选修）任意切换

## 本地运行

```bash
cd english-grammar
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py --server.headless true
```

浏览器打开 http://localhost:8501

## 启用 AI 助教（可选）

侧边栏填入 OpenAI 兼容接口的 API 密钥（如智谱 `https://open.bigmodel.cn/api/paas/v4` + `glm-5.3-flash`），
点「保存配置」。也可以在云端 Secrets 中配置 `[llm]` 段（与生词造句项目相同格式）。

配置会写入本地 `llm_config.json`（已被 .gitignore 排除，不会提交到 GitHub）。

## 部署到自有服务器

本项目通过 `sync.sh` 一条命令同时同步到 GitHub 和自有服务器（rsync + 自动重启服务）。

服务器上以 **systemd 原生进程**运行（非 Docker）：

```ini
# /etc/systemd/system/english-grammar.service
[Service]
User=<运行用户>
WorkingDirectory=<项目目录>
ExecStart=<项目目录>/.venv/bin/streamlit run app.py \
    --server.port=8501 --server.address=127.0.0.1 \
    --server.baseUrlPath=/study/english-grammar --server.headless=true
Restart=always
```

前端用 Nginx/OpenResty 反代到 `127.0.0.1:8501`，需配置 WebSocket 透传
（`proxy_set_header Upgrade $http_upgrade;` 等，注意 Host 用 `$http_host` 保留端口）。

`sync.sh` 会用 rsync 排除 `.git/`、`data/`、`llm_config.json`，
所以服务器上的运行数据和 API Key 不会被同步覆盖。

## 数据结构

`grammar_data/middle/` 与 `grammar_data/high/` 下每个专题一个 JSON 文件：

```json
{
  "id": "m01", "level": "middle", "grade": "七年级上", "unit": "...", "topic": "...",
  "summary": "...",
  "rules": [{"title": "...", "detail": "...", "examples": [{"en": "...", "zh": "...", "highlight": "..."}]}],
  "signals": ["every day", ...],
  "pitfalls": ["..."],
  "compare": {"left": "...", "right": "...", "rows": [...]},
  "questions": [
    {"type": "choice", "stem": "...", "options": [...], "answer": 1, "explain": "..."},
    {"type": "fill", "stem": "... (have)", "answer": ["has"], "explain": "..."},
    {"type": "correct", "stem": "...", "answer": "like → likes", "explain": "..."},
    {"type": "translate", "stem": "...", "answer": ["多答案数组"], "explain": "..."}
  ]
}
```

想扩充题库，直接仿照格式添加 JSON 文件即可（文件名 = 专题 id + 名称）。

## 判分规则

- **全部题型**：忽略大小写、多空格、首尾标点
- **翻译题**：另忽略句中标点；本地判错时自动调用 AI 批改兜底（同义词/近义表达/语序不同判对）
- **改错题**：需写出完整正确句子，考点词必须精确，句子其余部分容忍笔误
- **填空题**：保持严格（考查的就是词形变化）

## 初中专题（18）

be 动词与一般现在时 · 人称代词与物主代词 · 名词复数与可数不可数 · there be 句型 · 特殊疑问句 · 现在进行时 · 一般过去时 · 一般将来时 · 情态动词 · 比较级最高级 · 过去进行时 · 现在完成时 · 不定式与动名词 · 宾语从句 · 状语从句 · 被动语态 · 定语从句 · 感叹句与祈使句

## 高中专题（15）

过去完成时 · 过去将来时 · 现在完成进行时 · 被动语态进阶 · 不定式 · 动名词 · 分词 · 定语从句进阶 · 名词性从句 · 状语从句进阶 · 虚拟语气 · 倒装句 · 强调句与 it 句型 · 主谓一致 · 情态动词表推测

## 部署到 Streamlit Cloud（可选，演示用）

与生词造句项目相同：推送到 GitHub → share.streamlit.io 选择本仓库 `app.py` 部署。
私享使用可在 Secrets 配置 `[llm]` 段启用 AI 助教。

> 注意：Streamlit Cloud 上的数据（错题本、进度）存于容器临时目录，重启即丢失。
> 长期自用请用上面的「部署到自有服务器」。
