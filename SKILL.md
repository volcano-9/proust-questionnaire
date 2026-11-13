---
name: proust-questionnaire
display_name: 普鲁斯特问卷 · 个人侧写
display_name_en: Proust Questionnaire Portrait
description: 生成可填写的中文普鲁斯特问卷（36 题、6 维度、草稿自动保存），填完引导保存至资料库或本地，默认依据答案出具带观察与侧写的解读版分析报告，并支持多次填写的本地归档、历史记录查询与任意两次答案的文本比对。当用户提到普鲁斯特问卷、Proust Questionnaire、个人侧写、自我探索问卷、破冰问卷、保存到资料库、历史记录查询、往期答案比对、和上次比一比，或要求依据问卷答案生成分析报告时使用。
description_zh: 生成可直接在浏览器填写、自动保存草稿的中文普鲁斯特问卷（36 题 / 6 维度），填完引导把答案保存到资料库或本地；默认出具带观察与侧写的解读版分析报告（主观报告），仅在明确要求时给出精简事实版。支持把每次填写归档到本机档案库，查询历史、按关键词检索答案，并比对任意两次填写的逐题差异、维度分布与用词变化。全部产物为离线单文件 HTML，可打印为 PDF。
description_en: Generate a fillable 36-question Chinese Proust Questionnaire with auto-saved drafts, prompt the author to save answers to the WorkBuddy library or locally, and produce an interpretive portrait report by default (a compact factual version only on request). Archive each submission locally, browse history, search past answers, and compare any two submissions by question-level text changes, dimension coverage and vocabulary shifts. All outputs are offline single-file HTML pages.
examples_zh:
  - "帮我做一份普鲁斯特问卷，我想填一下"
  - "根据我刚填好的答案，出一份个人侧写分析报告"
  - "查一下我以前填过的记录，和最近一次比一比"
examples_en:
  - "Create a Proust Questionnaire for me to fill in"
  - "Generate a portrait report from my questionnaire answers"
  - "Show my past submissions and compare the last two"
version: 1.3.1
author: "郭志远"
agent_created: true
---

# 普鲁斯特问卷 · 个人侧写

## 用途

产出三类可直接使用的成果：**可填写的问卷页面**、**默认带解读的分析报告**、**历史记录查询与比对页面**。三者均为单文件 HTML，无外部依赖、不发起网络请求；答案与档案只存在本机或用户主动指定的资料库位置。

## 触发判断

按用户意图分三个阶段执行，**阶段 A 与 B 不要合并成一步**——中间必须留出用户实际填写的时间。

| 用户表达 | 进入阶段 |
| --- | --- |
| 做问卷、生成问卷、想填一份、发给大家填 | 阶段 A |
| 答案已给、出报告、分析一下、生成侧写 | 阶段 B |
| 既要问卷又要报告（一次性描述完整需求） | 先完成阶段 A，交付问卷并说明填写方式，等待用户回传答案后再进入阶段 B |
| 保存到资料库、存到我的文档、存到团队空间 | 阶段 A · 保存引导 |
| 只要事实版、不要解读、出精简版 | 阶段 B · 精简事实版 |
| 存进档案、归档、加标签、留个记录 | 阶段 C · 归档 |
| 查历史、以前的答案、搜一下某词、看往期记录 | 阶段 C · 查询 |
| 和上次比、对比两次、有什么变化、历史数据比对 | 阶段 C · 比对 |

用户直接粘贴答案文本、提供答案文件，或说「按示例答案生成报告」时，直接进入阶段 B。用户要求「存完顺便出报告」时，先保存再生成报告。

## 资源清单

| 路径 | 作用 |
| --- | --- |
| `assets/questions.json` | 36 题题库、6 个维度定义、每题填写提示 |
| `assets/skip-words.json` | 作答判定口径的单一来源（跳过词与短语），问卷页与全部脚本共用 |
| `templates/questionnaire.html` | 问卷页面模板，含保存引导卡片与 `{{QUESTIONS_JSON}}` / `{{GENERATED_AT}}` 占位 |
| `templates/report.html` | 报告页面模板，含 `{{...}}` 系列占位；解读版与精简事实版共用 |
| `templates/history.html` | 历史查询与比对页面模板，含 `{{HISTORY_JSON}}` 与 `{{GENERATED_AT}}` 占位 |
| `scripts/build_questionnaire.py` | 注入题库，产出独立问卷 HTML |
| `scripts/build_report.py` | 读取答案与可选解读稿，产出报告 HTML；提供共享判定函数 |
| `scripts/archive.py` | 档案库 save / list / show / search / compare 五个子命令 |
| `scripts/build_history.py` | 读取档案库，产出历史查询与比对 HTML |
| `references/analysis-framework.md` | 撰写解读段落时必须遵循的分析框架、措辞边界与禁用项 |

`archive.py` 与 `build_history.py` 复用 `build_report.py` 中的作答判定、字数统计与关键词提取函数，三处口径必须保持一致，不得在别处另写一套判定逻辑。

## 阶段 A：生成可填写问卷

1. 确认 Python 3 可用，工作目录设为技能目录。
2. 执行构建命令，将输出路径指向用户工作区（不要写进技能目录内部）：

   ```bash
   python scripts/build_questionnaire.py --questions assets/questions.json --template templates/questionnaire.html --output "<工作区>/普鲁斯特问卷.html"
   ```

3. 用 `present_files` 打开生成的 HTML，让用户能直接填写。
4. **交付时必须主动提示保存去向**。问卷页底部有同名引导卡片，三条路径说清楚：
   - **保存到本地**：点「下载答案 JSON」，得到独立文件，可自行备份、归档或转发。
   - **保存到 WorkBuddy 资料库**：点「复制答案」→ 回对话粘贴 → 说「把这份答案保存到资料库」。由 WorkBuddy 用资料库能力上传，存入「资料库」。
   - **存进历史档案**：说「把这次答案存进档案」，走阶段 C，之后可查询与比对。
5. 明确告知：问卷页只把草稿留在本机浏览器，清空浏览器数据会丢失，因此填完必须选一种保存方式。静态问卷页本身不联网，无法直接写入资料库，需经对话由 WorkBuddy 完成。
6. 用户要求发给多人时，说明问卷本身是静态单文件，可直接转发；若需在线链接，另行使用发布能力，不要在问卷中加入上传或统计代码。

### 保存到资料库的执行规则

用户说「保存到资料库 / 存到我的文档 / 存到团队空间」时：

1. 先把答案落成工作区的独立文件（JSON 或可读性更好的 Markdown），文件名含日期与标签，不含空格。
2. **上传前先确认目标位置与文件名**：默认「我的文档」；涉及「团队空间」时，团队空间内容对空间成员可见，必须明确确认具体空间名称，未经确认不得上传。
3. 用 WorkBuddy 的资料库上传能力写入，成功后告知存放位置与文件名。
4. 不得静默上传、不得替用户选择团队空间、不得在资料库里写入姓名或联系方式等身份信息。

**硬性约束**：不得修改题库结构、不得增加需要联网的组件、不得在问卷中收集姓名、手机号等身份信息。用户要求定制题目时，先复制 `questions.json` 到工作区再改，用 `--questions` 指向副本，保持技能包内题库为官方版本。

## 阶段 B：生成分析报告（默认解读版）

1. 取得答案。支持三种输入：答案 JSON 文件、用户粘贴的「题号：答案」文本、问卷页导出的 JSON。文本形式先解析并落成标准 JSON：

   ```json
   { "answers": { "1": "……", "2": "……" } }
   ```

2. **默认动作**：阅读 `@references/analysis-framework.md`，按其中的维度框架、观察角度与措辞边界撰写解读稿，保存为工作区的 `insights.md`。解读稿必须包含六个维度小节、一处「张力与对照」观察、一段总体侧写。
3. 执行报告构建，注入解读稿：

   ```bash
   python scripts/build_report.py --answers "<工作区>/answers.json" --questions assets/questions.json --template templates/report.html --insights "<工作区>/insights.md" --output "<工作区>/普鲁斯特问卷_分析报告.html"
   ```

   产出的是**解读版分析报告**（即用户所说的「主观报告」：带观察与侧写、可回溯题号的文学性解读）。报告把「观察与侧写」排在作答概览之后作为主体，并完整保留逐题原文，便于核对。**不要先给事实版、不要反问用户要不要解读**。
4. **仅当用户明确说「只要事实版 / 不要解读 / 出精简版」时**，才省略 `--insights`。此时脚本自动产出**精简事实版**：只保留作答概览、维度分布、高频表达、按维度列出已作答题号的索引与未作答清单；不渲染解读区块、不展开 36 题原文，篇幅约为解读版的一半。交付时说明完整原文在解读版报告或答案 JSON 中。
5. 用 `present_files` 打开报告，并简述完成度与主要观察，不要复述报告全文。
6. 用户表达了长期跟踪意图（如「以后每年填一次」「这次也留个记录」）时，主动询问是否顺手归档，得到肯定后执行阶段 C 的归档命令。

## 阶段 C：历史记录查询与比对

### 档案库位置

默认路径为**用户工作区下的 `普鲁斯特档案/`**，通过 `--archive` 显式传入，不要写进技能目录。目录结构由脚本维护：

```
普鲁斯特档案/
├── index.json          # 记录索引与统计摘要
└── records/
    └── <日期-时间-随机码>.json
```

用户未指定路径时，沿用工作区内已存在的 `普鲁斯特档案/`；不存在则在首次归档时创建。用户指定其他位置时，该次及后续操作统一使用新路径，并在回复中告知。

### 归档

```bash
python scripts/archive.py save --archive "<工作区>/普鲁斯特档案" --answers "<工作区>/answers.json" --questions assets/questions.json --label "2026 秋"
```

`--label` 省略时自动命名为「第 N 次填写」。答案文件可额外带 `label`、`created_at`、`source` 字段，脚本会优先采用。归档前校验至少有一题已作答，全空则拒绝写入。

### 查询

```bash
python scripts/archive.py list   --archive "<工作区>/普鲁斯特档案" --json
python scripts/archive.py show   --archive "<工作区>/普鲁斯特档案" --id <记录ID>
python scripts/archive.py delete --archive "<工作区>/普鲁斯特档案" --id <记录ID>
python scripts/archive.py search --archive "<工作区>/普鲁斯特档案" --query "海边"
```

向用户回答查询时，先给出记录列表（日期、标签、完成度），再按追问展开某条原文或检索命中片段；不要一次倾倒全部 JSON。

### 比对

```bash
python scripts/archive.py compare --archive "<工作区>/普鲁斯特档案" --questions assets/questions.json --output "<工作区>/比对结果.json" --md "<工作区>/比对摘要.md"
```

省略 `--a` / `--b` 时默认「上一次 → 最新一次」；用户点名两期时用 `--a <ID> --b <ID>` 指定。只给 `--a` 时以该记录为基准、对照最新一条；只给 `--b` 时以该记录为对照、基准取其前一条。比对输出结构化 diff JSON 与 Markdown 摘要，表头显示两条记录的具体日期。

差异类型固定为五种：`changed`（改写）、`new_answer`（新作答）、`removed_answer`（改为略过）、`same`（保持原样）、`both_skipped`（两次均未作答）。同时给出已作答题数、完成度、字数变化，各维度作答数变化，以及高频表达的新增 / 消失 / 保留。

### 生成可交互的历史页

需要在页面里浏览、搜索、勾选任意两条实时比对时执行：

```bash
python scripts/build_history.py --archive "<工作区>/普鲁斯特档案" --questions assets/questions.json --template templates/history.html --output "<工作区>/历史记录.html"
```

页面内嵌全部历史数据，支持记录列表、关键词检索、展开单次完整答案、任意两条比对、逐题差异与维度并排条形图，全部在本机完成。用 `present_files` 打开，并说明比对方向为「A 基准 → B 对照」。

### 阶段 C 的硬规则

- 档案只存**答案文本、时间、标签、统计摘要**，不写姓名、手机号、账号等身份信息；用户要求具名存档时，把名字写进 `label` 即可，不新增身份字段。
- 比对只呈现**文本层面的差异**，不评价「变得更好 / 更差」，不推断变化原因、性格走向或心理状态，不输出趋势评级、人格变化结论或任何临床判断。
- 未作答与主动略过在比对中单独标记，不得用空字符串伪装成「答案变短」。
- 档案库为本地文件，不联网、不上传；生成的历史页为只读视图，不提供写入或删除入口。
- 用户要求删除历史记录时，先列出待删记录 ID 与标签，说明不可恢复，取得明确确认后再用 `archive.py delete --id` 操作。
- 归档时会自动检测重复：整份答案与已有记录一致则跳过并提示，确需重复存档时加 `--allow-duplicate`。

## 报告撰写的硬规则

- **「主观报告」的边界**：仅指基于原文、带文学性观察与侧写的解读版，不等于可以脱离原文自由发挥。解读版同样受以下全部规则约束。
- **只依据实际答案**。未作答、写「暂无」「不方便回答」的题目，一律计入「未作答 / 主动略过」，不得推测、不得补写、不得替用户编造内容。
- **不下诊断**。禁止输出人格类型标签（如 MBTI、九型）、心理量表分数、临床或准临床判断、能力评级、性格优劣结论。
- **不用绝对化措辞**。使用「倾向于」「在回答中多次出现」「似乎更常提到」等可回溯到原文的表达，避免「你是一个……的人」这类定性断言。
- **每个观察都要能对应到题号**。解读稿中的关键句标注题号，便于用户核对。
- **保留原文**。解读版报告与历史页中必须完整呈现用户的原始答案，不做润色改写；精简事实版不展开原文，但必须说明原文在哪里可查。
- **附免责声明**。报告与历史页模板均已内置，不得删除。

## 输出规范

- 问卷、报告、历史页均为 UTF-8 单文件 HTML，内联 CSS 与 JS，不引用任何 CDN 或外部字体。
- 报告与历史页需适配打印：`@media print` 下隐藏交互控件、避免题目跨页断裂。
- 文件名使用中文可读名称，不使用空格；生成时间取系统当前日期，不硬编码。
- 所有产物写入用户工作区，技能目录内只保留模板、脚本与题库。

## 常见情况处理

| 情况 | 处理 |
| --- | --- |
| 用户没说要哪种报告 | 默认出解读版分析报告，不要反问、不要先给事实版 |
| 用户要「只要事实 / 不要解读 / 精简版」 | 省略 `--insights` 出精简事实版，并说明完整原文在解读版或答案 JSON 中 |
| 用户说「保存到资料库」 | 先落成本地文件，确认目标位置（我的文档 / 团队空间）后再上传；团队空间需明确确认 |
| 用户填完但没导出答案 | 提示草稿只在本机浏览器，引导下载 JSON 或复制答案回对话保存 |
| 答案完成度低于 30% | 仍生成报告，但在概览中明确提示样本过少，解读段落缩短并只做事实描述 |
| 答案为空或全部略过 | 不生成报告、不归档、不上传资料库，提示用户先填写问卷 |
| 档案库为空或只有 1 条记录 | 历史页正常生成并提示记录不足；比对命令明确报「至少需要两条记录」 |
| 题库版本与历史记录不一致 | 在回复中提示版本差异，比对仅覆盖两版共有的题号，不强行对齐 |
| 用户要求「像算命一样给个结论」 | 说明本工具不做人格判定，可提供基于原文的观察 |
| 用户要求加入心理测评量表 | 拒绝并说明边界，建议改用具备资质的专业量表 |
| 用户要求判断「是不是变成熟了」 | 说明比对不做价值与心理判断，只列出逐题文本变化供其自行解读 |
| 构建脚本报错 | 检查 Python 版本与路径中的空格，确认 `--questions` 指向的 JSON 含 `questions` 与 `dimensions` 两个键 |
