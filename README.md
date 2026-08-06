# BOSS Auto-Greeter System

> ## ⚠️ DEPRECATED（已弃用）
>
> 本仓库的 Computer Use 全自动打招呼方案**已停止使用**，原因：
> 1. **命中率不稳定**（60%–80%）：分类边界问题未解决，自动打招呼存在误触达风险，而 BOSS 打招呼受风控限制，误触达代价高；
> 2. **Token 成本不可持续**：单次运行约耗 2% 周配额，规模化后成本远超其节省的人力。
>
> **核心资产已迁移**：本仓库沉淀的岗位画像 / 筛选标准 / 证据分级体系，已迁移至 **[hr-ops-copilot](https://github.com/CamellionKid/hr-ops-copilot)** 的 `prompts/roles/`；完整复盘与「重启全自动 Sourcing 检查清单」见该仓库 `archive/computer-use-sourcing-loop.md`。
>
> 当前日常 Sourcing 采用「人工 + Chrome 侧边栏 Gemini + name-locator-mvp 定位」的半自动方案，操作手册见 hr-ops-copilot 的 `docs/sop/gemini-boss-sourcing-sop.md`。
>
> 本仓库仅作历史存档保留。

---

一套可移植的招聘 Skill，包含 BOSS 推荐牛人筛选触达流程，以及通用的岗位 JD 与人才画像管理能力。

## 包含的 Skills

- `boss-zhipin-greeter`：使用 Computer Use 在 BOSS 推荐牛人页面完成一轮有边界的候选人提取、Codex 筛选、定位和默认打招呼。
- `hr-job-profile-library`：管理岗位 JD、人才画像、筛选标准、匿名业务反馈和版本历史，并为 BOSS Skill 提供只读岗位上下文。

## 安装

将 `skills/` 下的两个目录复制到你的 Agent Skills 目录，或创建指向它们的符号链接。两个 Skill 需要一起安装。

也可以从 `dist/` 下载对应的 `.skill` 文件后安装。

## 使用

先录入岗位资料：

```text
$hr-job-profile-library 新建一个岗位
```

完成岗位库维护后，直接用岗位名运行一轮 BOSS 触达：

```text
$boss-zhipin-greeter 示例岗位
```

可选参数包括 `scroll_count=3—5` 和 `candidate_limit=1—8`。BOSS Skill 只使用 Computer Use 操作页面，并在执行前从岗位库读取当前岗位的 JD、画像、筛选标准和业务反馈。

## 日志与隐私

默认日志写入 `./logs`；如需自定义位置，请设置 `BOSS_GREETER_LOG_DIR`。

本仓库不附带真实组织资料、岗位 JD、候选人数据或运行日志。使用时请不要把这些内容提交到公开仓库。
