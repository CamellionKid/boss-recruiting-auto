---
name: boss-zhipin-greeter
description: Use when the user explicitly asks to run or repeat one bounded BOSS直聘“推荐牛人” screening and greeting workflow in the current Chrome tab for a named registered job. Uses Computer Use for page verification, bounded scrolling, visible candidate extraction, Command-F location, and default greeting clicks, with a Codex screening subagent for job matching.
---

# BOSS 推荐牛人筛选与打招呼

执行一次有边界的招聘触达闭环：先从HR 招聘岗位 JD 与画像库加载并冻结岗位上下文，再由主 Agent 用 Computer Use 核验页面、滚动并提取当前 BOSS 推荐页可见的候选人数据，派出一个 screening subagent 完成岗位匹配判断，最后仍由主 Agent 使用 Command-F 定位并点击 BOSS 默认“打招呼”。

**REQUIRED SUB-SKILL:** Use hr-job-profile-library。该委派只允许读取当前岗位筛选上下文，不授权修改岗位库，也不得把候选人身份数据传入岗位库 Skill。

**核心原则：职责分离，证据闭环。** Computer Use 负责全部 BOSS 页面观察和动作；screening subagent 只允许判断并返回主 Agent。候选人提取阶段只滚动，不点击卡片或按钮；执行阶段只依据已核验的筛选表进行 Command-F、身份复核和默认“打招呼”。没有最新查找计数和卡片核验，不得写入 `not_found`；没有点击后的明确反馈，不得写入 `greeted`。

## 输入

- `job_query`：必填，岗位标准名称、岗位 ID 或岗位库别名，例如“示例岗位”。
- `scroll_count`：可选，取值 `3`—`5`，默认 `4`。
- `candidate_limit`：可选，取值 `1`—`8`，默认 `8`。

缺少 `job_query` 时，只询问岗位名。不要要求用户提供 JD、筛选条件、人才画像或额外模型配置。

## 一次性执行授权

- 用户显式调用本 Skill 并提供 `job_query`，即视为授权 Agent 在 `candidate_limit` 内完成“岗位库预检 → 页面核验 → 只读提取 → Codex 筛选 → 身份核验 → 默认打招呼 → 写日志”的单轮闭环。
- 不要自行请求计划批准、名单批准或逐人批准。若宿主平台存在不可绕过的行动时确认，在第一名即将点击“打招呼”前请求一次覆盖本轮名单的批量确认；确认后不再逐人询问。
- 一次性授权不扩大边界：不得开始第二轮、修改招呼语、打开完整简历、采集联系方式或绕过登录、验证码和风控。

## 固定边界

### Computer Use 页面提取

- BOSS 页面核验、岗位切换、候选人列表滚动、页面信息读取、Command-F 和打招呼都只使用 Computer Use；不得使用 browser-use CLI、Codex Chrome 插件、Chrome extension browser、Playwright、CDP、DOM 脚本或网络接口。
- 提取阶段只允许观察最新截图/无障碍树并在候选人列表内向下滚动 `scroll_count` 次；禁止点击候选人卡片、按钮或链接，禁止输入、导航、刷新、返回、打开完整简历或触发沟通。
- 每次滚动后取得最新状态，重新核对页面岗位文本并读取当前已加载卡片；不得复用旧 `element_index`、旧截图、旧坐标或滚动前状态。
- 岗位文本一旦与冻结岗位或滚动前基线不一致，立即将本轮全部候选人数据作废并标记 `interrupted`。完成规定次数后停止，不返回顶部、不加载第二批。

### Codex screening subagent

- 主 Agent 先冻结岗位上下文，再冻结候选人只读数据集；二者冻结后才派出一个 screening subagent。
- screening subagent 只接收冻结岗位上下文和候选人只读数据集，不访问浏览器、不调用岗位库、不修改文件、不生成招呼语、不执行招聘平台操作。
- 派出前把岗位快照、候选人数量和 SHA-256、候选人只读数据集完整物化为可发送文本；不得只引用主 Agent 的变量、上文或工具输出，因为 subagent 不保证继承这些临时状态。
- 岗位库 Skill 本身不得接收候选人姓名或其他身份信息；由主 Agent 把已经取得的岗位快照与候选人数据分别组合后交给 subagent。
- subagent 只依据页面已加载的岗位相关字段判断；不得使用或推断性别、年龄、民族、籍贯、婚育、健康、宗教等敏感特征。

### Computer Use 执行

- 当前岗位、登录状态、推荐页、可见筛选提示和候选人卡片状态由主 Agent 使用 Computer Use 视觉核验。
- 岗位切换、“应用上次的筛选”、Command-F、身份辅助核验和“打招呼”点击只能由 Computer Use 完成。
- 任何 UI 变化后重新取得最新状态；旧 `element_index` 和旧坐标失效。坐标只能依据最新截图。
- Computer Use 键名大小写敏感：回车使用 `Return`，不得使用 `RETURN`；退格使用 `BackSpace`。
- 主 Agent 必须用 Computer Use 发送真实 `Command-F`，在最新 Find 输入框中写入精确姓名，再发送 `Return`。
- 只用 Computer Use 点击页面显示的“打招呼”，且只点击一次。不要生成、填写或修改招呼语。

## 执行流程

### 1. 岗位库预检

在打开 Chrome、创建日志或读取候选人信息前：

1. 通过 `hr-job-profile-library` 受控委派，使用 `job_query` 运行 `scripts/job_library.py resolve --query "<job_query>" --json`。
2. 只接受唯一精确匹配的 `status: resolved`；`ambiguous`、`suggested`、`not-found` 均停止，不自动采用相似岗位。
3. 确认岗位为 `status: active`，再运行 `validate --json`。归档岗位、索引损坏、版本不一致或必需文件缺失时停止。
4. 读取 `job.json`、`jd.md`、`persona.md`、`screening-criteria.md`、`business-feedback.md`。
5. 冻结岗位 ID、标准名称、当前版本、四份文件名和四份原文，令 `job_context_loaded=true`、`screening_mode=codex_subagent`。同轮恢复和复核不得重新读取岗位库。
6. 预检失败时不创建运行日志、不触碰 BOSS，也不派出 subagent。

### 2. 建立日志

根据 [assets/run-log-template.md](assets/run-log-template.md) 创建：

```text
${BOSS_GREETER_LOG_DIR:-./logs}/YYYY-MM/YYYY-MM-DD_HHmmss__<job-id>.md
```

可通过 `BOSS_GREETER_LOG_DIR` 指定日志根目录；未设置时使用当前工作目录下的 `./logs`。

每轮只创建一个新日志，先写 `status: running`。记录岗位库 ID/名称/版本、四份资料清单、`job_context_loaded=true`、`screening_mode=codex_subagent`、Computer Use 提取字段、subagent 交接字段和候选人汇总；不要复制完整 JD、完整候选人数据集或联系方式。

同轮恢复、复核和纠错只回写原日志。只要存在 `locating` 或 `needs_recheck`，不得标记 `completed`。结束前运行 `scripts/validate_run_log.py <本轮日志路径>`。

### 3. 用 Computer Use 核验页面与岗位

1. 检查当前 Chrome 是否为 BOSS 企业端“推荐牛人”页；必要时用可见导航进入。
2. 使用冻结的岗位标准名称、别名和 `job_query` 核验当前招聘岗位；明显不匹配时，通过可见岗位选择器切换。相似岗位无法区分时停止询问用户。
3. 确认页面有多张候选人卡片、“打招呼”或已联系状态，且没有登录、验证码、风控或加载错误。
4. 只检查一次“应用上次的筛选”：出现时用 Computer Use 点击一次并等待稳定；没有出现则跳过，不自行打开筛选面板。
5. 记录已视觉确认的 BOSS 标签页、岗位与页面状态，之后进入同一标签页的 Computer Use 滚动提取阶段。

### 4. 用 Computer Use 滚动并提取

1. 保持在主 Agent 已视觉确认的同一 BOSS 标签页；精确核对页面为“推荐牛人”、岗位文本一致。无法唯一确认时停止。
2. 用 Computer Use 取得一次最新完整状态，读取当前已加载候选人卡片作为基线；不点击任何页面元素。
3. 只在候选人列表内向下滚动 `scroll_count` 次。每次滚动后等待页面稳定，重新取得最新状态，先核对岗位文本，再读取当前已加载卡片。
4. 提取字段限于：页面显示姓名、当前/期望职位、公司、工作年限、城市、教育背景、技能关键词、卡片优势、沟通状态及页面已有稳定候选人标识。忽略联系方式、头像地址、非岗位敏感字段和完整简历正文。
5. 最新页面状态若已包含过去点开卡片后留下的岗位相关信息，可以读取；不得为了补充信息点击卡片，也不得把“页面未提供”解释为“不具备”。
6. 优先按页面稳定候选人标识去重；没有稳定标识时使用“姓名 + 当前职位 + 最近公司”组合去重，并保留 `source_order`。
7. 生成规范化候选人只读数据集，计算 SHA-256；日志只记录 `computer_candidate_count`、`computer_dataset_hash`、请求/完成滚动次数和提取阶段禁止动作证据。
8. 只有确认滚动前及每次滚动后的岗位文本一致，且提取阶段 `card_click=false`、`button_click=false`、`input=false`、`navigation=false` 后才令 `computer_extraction_verified=true`。岗位漂移、发生越界动作或滚动次数不可信时，整批候选人数据作废并标记 `interrupted`。

### 5. 派出 Codex screening subagent

1. 读取 [assets/codex-screening-subagent-prompt.md](assets/codex-screening-subagent-prompt.md)，填入冻结岗位上下文、`candidate_limit`、`candidate_count`、`candidate_dataset_hash` 和规范化候选人只读数据集。
2. 把填充后的提示词完整物化到给 screening subagent 的消息中；不得写“使用上文数据”“读取主 Agent 变量”或只提供变量名。只发送冻结输入，不发送实现结论、预选名单或浏览器访问能力。派出后令 `screening_subagent_dispatched=true`。
3. 若单条消息过大，把同一份冻结数据集按 `part i/n` 编号发给同一 subagent；每片都携带同一候选人数量和 SHA-256。等待 subagent 确认收到全部分片后才允许筛选，不得让多个 agent 各筛一部分再合并。
4. subagent 返回 `INPUT_INCOMPLETE` 时，只把同一冻结数据集补发一次，不重新读取岗位库或 BOSS。仍不完整则中断。
5. 要求 subagent 返回主 Agent：`无推荐候选人`，或一张按匹配度排序的 Markdown 信息表，包含 `序号｜姓名｜选择理由｜页面证据｜定位信息｜风险或信息缺口`。
6. subagent 完成后令 `screening_subagent_completed=true`。主 Agent 逐项校验：
   - 姓名精确存在于冻结数据集；
   - 页面证据可在该候选人输入记录中逐字或等义找到；
   - 定位信息至少一项且来自输入记录；
   - 没有新增事实、敏感推断或联系方式；
   - 人数不超过 `candidate_limit`，不足 3 人不凑数，0 人可正常返回。
7. 全部通过后令 `screening_handoff_verified=true`，冻结有序执行名单。校验失败时只向同一 subagent 返回具体协议错误并允许纠正一次；仍失败则中断。

### 6. 主 Agent 用 Computer Use 定位与点击

按筛选表顺序处理每名候选人：

1. 保持在同一 BOSS 推荐页；不刷新、不继续滚动、不打开完整简历。
2. 使用 Computer Use 发送真实 `Command-F`，重新取得最新状态，确认焦点位于 Chrome Find，并取得最新 Find 输入框索引。
3. 用该最新输入框索引把值设为精确姓名；重新取得最新状态并确认 `Value` 完全一致，再发送大小写敏感的 `Return`。再次取得最新状态后才读取 `Result n of m`；不要把写值后、提交前的 `No results` 当作最终计数。只以总结果数 `m` 判断是否命中，`Result 0 of 1` 表示有 1 个命中。
4. 若计数未更新，执行一次哨兵字符回退：姓名后加一个字符、重新取得状态、用 `BackSpace` 删除、再发送 `Return`。仍无可信计数时标记 `needs_recheck`，不得判定 `not_found`。
5. 有命中时，用最新索引关闭 Find 栏，再重新取得完整页面状态；Find 聚焦期间只返回查找栏状态属于正常现象，不得在该状态下寻找候选人按钮。
6. 在完整页面状态中定位同一候选人卡片块，把姓名与筛选表的定位信息比对；除姓名外至少核验职位、公司、工作年限或城市中的一项。只从该卡片块读取沟通状态和按钮索引，不得使用全页第 n 个“打招呼”或旧索引。
7. 状态处理：
   - 显示“打招呼”：在宿主行动时确认满足后，只用 Computer Use 点击一次；
   - 显示“已沟通”“继续沟通”或等效状态：记录 `contacted_skipped`；
   - 未找到、同名无法区分、定位信息冲突或按钮不存在：跳过并记录对应状态。
8. 点击后等待并重新取得最新状态，再检查同一候选人卡片块。只有该卡片按钮变为“继续沟通”“已沟通”或同一卡片出现发送成功反馈时，才记录 `greeted`；否则再观察一次，不重复点击，记录 `unconfirmed`。
9. 每处理一人立即把查找计数、辅助核验、处理结果和时间写入原日志。

### 7. 结束本轮

出现以下任一条件时结束：名单处理完、subagent 返回 0 人、达到 `candidate_limit`，或触发停止条件。不要自动开始第二轮。

- `completed`：Computer Use 提取证据、subagent 交接和候选人终态全部完整；0 人推荐也可完成。
- `interrupted`：登录/验证码/风控、岗位不明、Computer Use 提取证据失败、subagent 两次协议失败、Computer Use 页面操作连续两次无法恢复。

补全结束时间和汇总，运行日志校验。校验失败且证据不可重建时改为 `interrupted`，不得宣告完成。

## 证据门槛

| 结论 | 最新证据 |
|---|---|
| `computer_extraction_verified` | 同一 BOSS 推荐页和岗位；滚动次数完整；提取阶段 `card_click/button_click/input/navigation=false` |
| `screening_handoff_verified` | subagent 表中每个姓名、页面证据和定位信息均可回溯到冻结数据集 |
| `greeted` | 姓名与至少一项定位信息匹配；点击后出现已沟通类反馈 |
| `contacted_skipped` | 匹配卡片已显示已联系状态 |
| `not_found` | 当前姓名经过真实提交和一次哨兵回退，最终总结果数均为 0 |
| `identity_mismatch` | 有命中，但同名无法区分或定位信息冲突 |
| `needs_recheck` | Find 计数空白、陈旧、未更新或不可读 |

## 常见错误

- **混用其他浏览器控制通道**：本 Skill 的 BOSS 页面观察与动作全部使用 Computer Use；不得接入 browser-use CLI、Chrome 插件、Playwright 或 CDP。
- **在提取阶段点击卡片或按钮**：提取阶段只观察与滚动；任何页面点击均越界并中断。
- **滚动后未复核岗位**：每次滚动先核对岗位文本；一旦回退或漂移，当前数据集全部作废。
- **调用接口或 DOM 脚本补全数据**：不得调用网络接口、Playwright 或页面脚本；只使用 Computer Use 最新截图和无障碍树中已显示的信息。
- **把岗位库 Skill 与候选人数据混在同一委派**：岗位库只返回岗位上下文；主 Agent 冻结后再与候选人数据组合给 screening subagent。
- **只告诉 subagent 去读“上文”或临时变量**：subagent 不保证继承主 Agent 的工具输出；必须发送完整物化的数据、候选人数量和 SHA-256，分片时等待全部分片确认。
- **让 subagent 直接操作页面**：subagent 只返回信息表；主 Agent 承担全部 UI 动作和日志。
- **使用 `RETURN` 或在提交前读取结果**：Computer Use 键名大小写敏感；必须使用 `Return`，并在写值、提交后分别重新取得状态。
- **Find 栏未关闭就寻找按钮**：Find 聚焦时页面状态可能只包含查找栏；先用最新索引关闭 Find 栏，再从命中候选人的卡片块读取按钮。
- **把未展示当成不具备**：未展示只写入风险或信息缺口，不作为自动淘汰证据。
- **仅凭姓名点击**：至少再核验一项定位信息，并确认当前按钮状态。
- **把 `Result 0 of 1` 当成未找到**：存在性看总数 `m`；此时 `m=1`。

## 调用示例

```text
运行 $boss-zhipin-greeter 示例岗位
```

```text
运行 $boss-zhipin-greeter
岗位：示例岗位
滚动次数：4
本轮最多：8 人
```
