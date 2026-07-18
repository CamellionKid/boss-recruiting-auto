---
name: hr-job-profile-library
description: Manual-only for direct use. Use when explicitly invoked as $hr-job-profile-library, "use hr-job-profile-library", or "使用 HR 招聘岗位 JD 与画像库 Skill"; also use for read-only screening-context delegation from an explicitly invoked $boss-zhipin-greeter carrying job_query. Do not infer or start from ordinary recruiting, JD, candidate, resume, or interview topics.
---

# HR 招聘岗位 JD 与画像库

## Overview

管理招聘岗位的 JD、人才画像、筛选标准、匿名业务反馈与完整历史版本。使用自然语言判断和整理资料，使用 `scripts/job_library.py` 执行确定性的匹配、预览、写入、版本和校验。

## 0. 显式调用与受控委派硬门槛

在读取任何岗位库文件前，先确认满足“直接显式调用”或“受控委派”之一。

直接显式调用包括：

- `$hr-job-profile-library`
- `use hr-job-profile-library`
- `使用 HR 招聘岗位 JD 与画像库 Skill`
- 明确点名“组织岗位职责”并要求调用该 Skill

受控委派仅在以下条件全部成立时有效：

1. 用户当前消息显式调用 `$boss-zhipin-greeter`；
2. 调用方明确声明 `**REQUIRED SUB-SKILL:** Use hr-job-profile-library`；
3. 调用方传入非空 `job_query`；
4. 委派目的仅为只读加载当前招聘轮次的岗位筛选上下文。

若当前请求未显式调用且受控委派条件也不成立：立即停止。不得读取 `references/job-index.json`、组织背景或任何岗位文件；不得把普通招聘话题视为受控委派，也不得因为普通 JD、候选人、简历或面试讨论而推断启动。

## 1. 硬规则

1. 先匹配岗位，再读取文件；只加载当前任务需要的内容。
2. 所有新建、更新和归档必须执行：预览 → 用户确认 → 携带同一 `plan_hash` 应用 → `validate` → 读回。
3. 不得直接编辑索引或岗位文件；始终通过 `scripts/job_library.py` 写入。
4. 信息缺失时写“未提供”，不得补写推测事实。
5. 岗位 ID 和标准名称必须唯一；别名命中多个岗位时必须让用户选择。
6. 非精确匹配只作为建议，永不自动选择或写入。
7. L1/L2 业务反馈只能保存为反馈，禁止进入正式 JD、画像或筛选标准；只有 L3/L4 可在用户确认后升级。
8. 不保存候选人姓名、电话、邮箱、身份证号或其他敏感个人信息；业务反馈必须匿名化。
9. 不执行物理删除。删除、停用或岗位取消统一走可追溯归档。
10. 发现索引损坏、必需文件缺失或版本不一致时停止写入，不自动重建或覆盖。

## 2. 意图路由

| 意图 | 典型表达 | 动作 |
|---|---|---|
| 新建 | 新增、建立、录入岗位 | 结构化资料并运行 `create` |
| 调用 | 调用、加载、读取岗位 | 运行 `resolve` 后按需读文件 |
| 更新 | 修改、补充、校准、加入反馈 | 加载当前岗位并运行 `update` |
| 列表 | 有哪些岗位、列出岗位 | 运行 `list`，不加载岗位正文 |
| 历史 | 修改记录、之前版本 | 运行 `history` |
| 归档 | 停用、归档、岗位取消、删除 | 运行 `archive`，不删除目录 |

一个请求包含多个动作时，按“匹配 → 加载 → 分析 → 预览 → 用户确认 → 应用”执行。

## 3. 按需加载

先运行：

```bash
python3 "$SKILL_DIR/scripts/job_library.py" resolve --query "岗位名" --json
```

只有 `status: resolved` 才可继续。`ambiguous` 或 `suggested` 必须把候选岗位列给用户选择。

| 任务 | 默认加载 |
|---|---|
| 了解岗位 | `jd.md`、`persona.md` |
| 为其他 Skill 提供筛选上下文 | `jd.md`、`persona.md`、`screening-criteria.md`、`business-feedback.md` |
| 候选人沟通准备 | `jd.md`、`persona.md`、`references/organization-context.md` |
| 更新岗位 | 当前全部岗位文件、`job.json`、`changelog.md` |
| 查看历史 | `changelog.md` 和指定 `history/vX.Y.Z/` |

本 Skill 只提供岗位上下文，不自行筛选简历、生成招聘话术或访问招聘平台。

### 3.1 BOSS Skill 受控委派读取

当受控委派硬门成立时，按以下只读流程执行：

1. 使用 `job_query` 运行 `resolve --json`。
2. 只有结果为唯一精确匹配的 `status: resolved` 才继续；不得自动采用 `suggested`，`ambiguous`、`suggested` 或 `not-found` 直接返回调用方处理。
3. 检查匹配岗位为 `status: active`，并运行 `validate --json`；归档岗位、索引损坏、版本不一致或必需文件缺失均停止。
4. 读取 `job.json` 以及 `jd.md`、`persona.md`、`screening-criteria.md`、`business-feedback.md`，把岗位 ID、标准名称、当前版本、文件清单与四份原文返回给主 Agent。
5. 主 Agent 必须冻结岗位快照；如需下游 screening subagent 判断候选人，由主 Agent 在本 Skill 返回后另行组合岗位快照与候选人数据。岗位库 Skill 不接收候选人身份信息，候选人数据不得回传本 Skill。
6. 委派模式不得执行 `create`、`update`、`archive`，不得写入索引、岗位文件、历史版本或业务反馈，也不得接收候选人身份信息。

调用方必须在开始页面操作前冻结本轮岗位上下文；本 Skill 不负责下游 Codex 筛选、候选人判断或 BOSS 页面操作。

## 4. 新建岗位

1. 运行 `list --status all --json` 和 `resolve` 检查现有岗位。
2. 读取 [references/job-schema.md](references/job-schema.md)，将用户资料整理成 create JSON；缺失字段使用“未提供”。
3. 不把原始 JD 与模型整理内容混成无来源结论；在 `source` 中保留事实来源。
4. 默认执行预览：

```bash
python3 "$SKILL_DIR/scripts/job_library.py" create --input "$INPUT_FILE"
```

5. 向用户展示岗位 ID、标准名称、保存文件、缺失项、版本和 `plan_hash`，等待用户确认。
6. 用户确认后使用预览返回的原哈希：

```bash
python3 "$SKILL_DIR/scripts/job_library.py" create \
  --input "$INPUT_FILE" --apply --plan-hash "$PLAN_HASH"
```

7. 运行 `validate --json`，再读回 `job.json`、索引和相关 Markdown。任何失败均按实际结果报告。

## 5. 更新岗位

1. 精确匹配岗位并加载当前全部文件。
2. 区分更新类型：`wording`、`correction`、`feedback`、`metadata`、`persona`、`screening`、`standard`、`role-scope`。
3. 将新反馈分为 L1–L4。L1/L2 即使用户要求也不得设置 `promote_to_formal: true`。
4. 在 update JSON 中填写当前 `expected_version`、修改原因、来源、完整的新文件内容及匿名反馈。
5. 运行 `update --input "$INPUT_FILE"`，向用户展示版本变化和差异，等待用户确认。
6. 用户确认后携带同一 `plan_hash` 运行 `--apply`。
7. 运行 `validate --json`，读回当前文件、索引、`changelog.md` 及新建的旧版快照。

版本规则由脚本强制执行：表述、纠错、反馈和普通元数据递增补丁版本；画像、筛选和任职标准递增次版本；岗位定位或核心职责递增主版本。

## 6. 列表、历史与归档

```bash
python3 "$SKILL_DIR/scripts/job_library.py" list --status all --json
python3 "$SKILL_DIR/scripts/job_library.py" history --job-id "sample-role"
python3 "$SKILL_DIR/scripts/job_library.py" history --job-id "sample-role" --version "1.0.0"
python3 "$SKILL_DIR/scripts/job_library.py" archive \
  --job-id "sample-role" --reason "暂停招聘"
```

归档同样必须先预览、等待用户确认，再使用 `--apply --plan-hash`。归档后岗位目录和历史快照必须保留。

## 7. 输出契约

每次结束时按此顺序报告：

1. 本次操作与目标岗位；
2. 已加载或修改的文件；
3. 原版本与当前版本；
4. 主要结果；
5. 冲突、缺失或待确认项；
6. 是否产生文件变更。

调用岗位时优先输出可用岗位上下文，不展示冗长的底层读取过程。未完成 `validate` 与读回时，不声称写入成功。

## 8. 资源

- [references/job-schema.md](references/job-schema.md)：数据结构、输入 JSON、证据、版本和隐私契约。
- [references/organization-context.md](references/organization-context.md)：组织背景；首版字段均为“未提供”。
- `references/job-index.json`：轻量岗位索引；不要直接编辑。
- `assets/job-template/`：新岗位文件模板。
- `scripts/job_library.py --help`：稳定 CLI 接口。
