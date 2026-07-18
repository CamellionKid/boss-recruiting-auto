# 岗位库数据契约

## 目录

- [存储结构](#存储结构)
- [索引与岗位元数据](#索引与岗位元数据)
- [Create 输入](#create-输入)
- [Update 输入](#update-输入)
- [版本规则](#版本规则)
- [反馈证据](#反馈证据)
- [隐私与安全](#隐私与安全)
- [预览与应用](#预览与应用)

## 存储结构

```text
references/
├── organization-context.md
├── job-index.json
└── jobs/
    └── <job-id>/
        ├── job.json
        ├── jd.md
        ├── persona.md
        ├── screening-criteria.md
        ├── business-feedback.md
        ├── changelog.md
        └── history/
            └── v1.0.0/
                └── 上一版全部六个文件
```

`history/vX.Y.Z/` 是不可覆盖的完整旧版快照。当前文件只代表当前版本。

## 索引与岗位元数据

`job-index.json` 只保存路由所需信息：

```json
{
  "schema_version": "1.0",
  "company": "未提供",
  "updated_at": "2026-07-18",
  "jobs": [
    {
      "id": "sample-role",
      "name": "示例岗位",
      "aliases": ["示例岗位别名"],
      "family": "示例职能",
      "status": "active",
      "current_version": "1.0.0",
      "updated_at": "2026-07-18",
      "path": "references/jobs/sample-role"
    }
  ]
}
```

`job.json` 另保存 `english_name`、`department`、`location`、创建时间和更新时间。ID 必须是小写英文、数字和单连字符。ID 与标准名称必须唯一；别名可以重复，但重复命中时不得自动选择。

## Create 输入

将用户资料写入临时 JSON 文件。未提供的字段使用字符串 `未提供`，不得虚构。

```json
{
  "actor": "tester",
  "reason": "首次建立岗位",
  "source": "用户提供的原始 JD 与业务画像",
  "job": {
    "id": "sample-role",
    "name": "示例岗位",
    "english_name": "Sample Role",
    "aliases": ["示例岗位别名"],
    "family": "示例职能",
    "department": "未提供",
    "location": "未提供",
    "status": "active"
  },
  "files": {
    "jd": "# 正式 JD\n...",
    "persona": "# 招聘画像\n...",
    "screening-criteria": "# 筛选标准\n...",
    "business-feedback": "# 业务反馈\n未提供"
  }
}
```

`files` 可不完整；脚本会用模板补齐缺失文件，并明确写入“未提供”。已有 ID 或标准名称会被拒绝，不能覆盖。

## Update 输入

```json
{
  "job_id": "sample-role",
  "expected_version": "1.0.0",
  "change_type": "screening",
  "actor": "tester",
  "reason": "用人经理确认新的筛选口径",
  "source": "2026-07-18 用人经理确认",
  "files": {
    "screening-criteria": "# 筛选标准\n...完整新内容..."
  },
  "job_updates": {},
  "feedback": [
    {
      "id": "fb-20260718-001",
      "date": "2026-07-18",
      "level": "L3",
      "context": "用人经理确认的匿名面试口径",
      "content": "能够清楚说明岗位相关方案取舍。",
      "promote_to_formal": true,
      "promotion_targets": ["screening-criteria"]
    }
  ]
}
```

`expected_version` 必须等于当前版本。更新正式文件时提交该文件的完整新内容，而非任意路径或局部 shell 补丁。`job_updates` 只允许 `name`、`english_name`、`aliases`、`department`、`family`、`location`。

## 版本规则

| change_type | 递增 | 示例 |
|---|---|---|
| `wording`、`correction`、`feedback`、`metadata` | 补丁 | `1.0.0 → 1.0.1` |
| `persona`、`screening`、`standard` | 次版本 | `1.0.0 → 1.1.0` |
| `role-scope` | 主版本 | `1.0.0 → 2.0.0` |

每次更新或归档先把当前 `job.json` 和五个 Markdown 文件复制到 `history/v<旧版本>/`，再写当前版本和 append-only `changelog.md`。

## 反馈证据

- L1：单个候选人的单次反馈。
- L2：多个候选人的重复反馈，但尚未形成负责人确认口径。
- L3：用人经理明确确认的筛选口径。
- L4：正式 JD、制度或公司确认要求。

L1/L2 只能追加到 `business-feedback.md`，`promote_to_formal` 必须为 `false`。L3/L4 可以设置为 `true`，但必须同时提交 `promotion_targets` 对应正式文件的完整新内容，并经过用户预览确认。

## 隐私与安全

禁止在任何输入中使用候选人身份字段，包括：

- `candidate_name`
- `candidate_full_name`
- `candidate_phone`
- `candidate_email`
- `candidate_id` 或 `candidate_id_number`
- `resume_name`

脚本还会拒绝常见中国手机号、邮箱和身份证号。自动检测不是完整匿名化工具；整理输入时仍须移除姓名、公司内部人员敏感信息和能重新识别候选人的细节。

不支持物理删除。岗位停用只将 `status` 改为 `archived` 并生成新版本和旧版快照。

## 预览与应用

`create`、`update`、`archive` 默认只读，返回 `result: preview` 与 `plan_hash`。向用户展示预览并获得明确确认后，重新运行同一命令并加入：

```text
--apply --plan-hash <预览返回的 plan_hash>
```

脚本会重新计算输入和当前文件状态。输入、索引或岗位文件发生任何变化时，旧 `plan_hash` 失效，必须重新预览。应用完成后必须运行 `validate --json` 并读回实际文件。
