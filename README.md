# BOSS Auto-Greeter System

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
