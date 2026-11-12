# 普鲁斯特问卷 · 个人侧写

生成可填写的中文普鲁斯特问卷（36 题 / 6 维度），填完引导保存至资料库或本地，默认出具带观察与侧写的解读版分析报告，并支持多次填写的本地归档、历史记录查询与任意两次答案的文本比对。

## 快速开始

**阶段 A · 生成问卷**

```bash
python scripts/build_questionnaire.py \
  --questions assets/questions.json \
  --template templates/questionnaire.html \
  --output "普鲁斯特问卷.html"
```

问卷页底部带「填完之后，把答案存起来」引导卡片，填完会高亮提示，列出三条保存去向：下载答案 JSON 到本地、回对话保存到 WorkBuddy 资料库、存进历史档案。问卷页本身不联网，资料库上传需经对话由 WorkBuddy 完成。

**阶段 B · 生成报告（默认解读版）**

```bash
python scripts/build_report.py \
  --answers answers.json \
  --questions assets/questions.json \
  --template templates/report.html \
  --insights insights.md \
  --output "普鲁斯特问卷_分析报告.html"
```

带 `--insights` 时产出**解读版分析报告**（主观报告）：观察与侧写排在概览之后作为主体，并完整保留逐题原文。解读稿按 `references/analysis-framework.md` 撰写。

仅当明确要求「只要事实版 / 不要解读 / 精简版」时省略 `--insights`，脚本自动产出**精简事实版**：不渲染解读区块、不展开 36 题原文，只保留统计与各维度已作答题号索引，篇幅约为解读版的六成。

答案 JSON 格式为 `{"answers": {"1": "…", "2": "…"}}`。

**阶段 C · 归档、查询与比对**

```bash
python scripts/archive.py save \
  --archive "普鲁斯特档案" --answers answers.json \
  --questions assets/questions.json --label "2026 秋"

python scripts/archive.py list   --archive "普鲁斯特档案"
python scripts/archive.py search --archive "普鲁斯特档案" --query "海边"
python scripts/archive.py compare --archive "普鲁斯特档案" \
  --questions assets/questions.json --output "比对结果.json" --md "比对摘要.md"

python scripts/build_history.py \
  --archive "普鲁斯特档案" --questions assets/questions.json \
  --template templates/history.html --output "历史记录.html"
```

`compare` 省略 `--a` / `--b` 时默认比对「上一次 → 最新一次」，摘要表头显示两条记录的具体日期。档案库结构为 `index.json` + `records/*.json`，全部为本地文件。

## 目录

| 路径 | 内容 |
| --- | --- |
| `SKILL.md` | 触发条件、三阶段工作流、保存规则、输出规范与硬规则 |
| `assets/questions.json` | 36 题题库、6 维度定义、填写提示 |
| `templates/questionnaire.html` | 问卷页模板（单文件、离线、本地草稿、保存引导） |
| `templates/report.html` | 报告页模板（解读版 / 精简事实版共用，可打印为 PDF） |
| `templates/history.html` | 历史查询与比对页模板（检索、展开、任意两条比对） |
| `scripts/build_questionnaire.py` | 注入题库，产出独立问卷 HTML |
| `scripts/build_report.py` | 统计与原文渲染，注入解读稿产出报告；共享判定函数 |
| `scripts/archive.py` | 档案库 save / list / show / search / compare |
| `scripts/build_history.py` | 读取档案库，产出历史查询与比对 HTML |
| `references/analysis-framework.md` | 解读稿的框架、措辞边界与禁用项 |

`archive.py` 与 `build_history.py` 复用 `build_report.py` 的作答判定与关键词提取，保证三处口径一致。

## 比对口径

逐题差异分五类：改写、新作答、改为略过、保持原样、两次均未作答。同时给出已作答题数、完成度、字数变化，各维度作答数变化（A / B 并排条形），以及高频表达的新增 / 消失 / 保留。比对只描述文本变化，不作价值判断或心理推断。

## 设计约束

- 问卷、报告、历史页均为 UTF-8 单文件 HTML，不引用 CDN、字体或任何外部资源，不发起网络请求。
- 问卷草稿存本机浏览器 `localStorage`；历史档案存本机文件系统；保存到资料库必须经用户确认目标位置（我的文档 / 团队空间）后由 WorkBuddy 执行，团队空间涉及共享需明确确认。
- 不收集姓名、手机号等身份信息。
- 默认出解读版报告；精简事实版仅在明确要求时生成。解读版只依据实际答案，未作答题不推测、不补写；不输出人格类型、分数、评级或临床判断。
- 历史页为只读视图，不提供写入或删除入口。
- 题库为中性化改编版本：删去按性别区分品质评价、以及要求公开贬低特定在世人物的题目，适配团队破冰与公开发布场景。

## 边界

普鲁斯特问卷是文学性的自我问答传统，不是心理测评量表。报告与历史比对不构成医疗、心理、法律、投资或人事决策依据，也不评价变化的好坏。「主观报告」仅指基于原文的文学性观察，不等于可以脱离原文自由发挥。

版本 1.2.2 · 需 Python 3.8+
