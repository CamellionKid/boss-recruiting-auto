# BOSS Recruiting Auto

一套可移植、可审计的招聘自动化 Skills：用岗位画像约束筛选判断，再在 BOSS 推荐牛人页面完成一次有边界的候选人提取、筛选与默认打招呼。

> **项目状态：维护中。** 本项目保留自动执行能力，但不是无人值守的批量触达器。每轮都需要显式调用，并受岗位匹配、候选人数、页面证据、平台风控和运行日志约束。

## 核心组成

### `hr-job-profile-library`

岗位画像 Skill，负责管理：

- 岗位 JD；
- 人才画像与筛选标准；
- 匿名业务反馈与证据等级；
- 岗位版本、历史快照和归档状态。

它为操作 Skill 提供只读的岗位上下文。公开分发版不包含真实组织、岗位或候选人数据。

### `boss-zhipin-greeter`

BOSS 操作 Skill，负责在一次显式授权的运行中：

1. 精确解析并冻结岗位画像；
2. 使用 Computer Use 核验岗位和页面状态；
3. 在限定滚动次数内提取可见候选人；
4. 将冻结的岗位上下文与候选人数据交给 Codex screening subagent；
5. 对入选候选人重新定位、核验身份并点击默认“打招呼”；
6. 写入可验证的单轮运行日志。

两个 Skill 需要配套使用：画像 Skill 决定“按什么标准判断”，操作 Skill 负责“如何在页面上安全执行”。

## 自动化边界

- 只在用户显式调用后运行，不后台轮询或自动开启下一轮；
- 每轮最多处理 `candidate_limit=1—8` 名入选候选人；
- 岗位只能精确匹配一个启用中的画像，歧义或未找到时停止；
- BOSS 页面观察与动作只使用 Computer Use，不调用 DOM、CDP、Playwright 或平台接口；
- 只点击平台默认“打招呼”，不生成或改写招呼语；
- 登录失效、验证码、风控、岗位不明或证据不完整时停止；
- 候选人身份数据不会写入岗位画像库，公开仓库也不包含真实运行日志。

## 安装

将 `skills/` 下的两个目录复制到 Agent Skills 目录，或创建指向它们的符号链接。两个 Skill 需要一起安装。

也可以从 `dist/` 安装对应的 `.skill` 文件：

- `dist/hr-job-profile-library.skill`
- `dist/boss-zhipin-greeter.skill`

## 使用

先录入岗位资料：

```text
$hr-job-profile-library 新建一个岗位
```

完成岗位库维护后，用已登记的岗位名称运行一轮 BOSS 触达：

```text
$boss-zhipin-greeter 示例岗位
```

可选参数包括 `scroll_count=3—5` 和 `candidate_limit=1—8`。缺少岗位名称时，Skill 只询问岗位名，不要求重复提供 JD 或画像。

## 日志与隐私

默认日志写入 `./logs`；如需自定义位置，请设置 `BOSS_GREETER_LOG_DIR`。

不要把真实组织资料、岗位 JD、候选人信息、运行日志、账号凭据或本机绝对路径提交到公开仓库。

## 项目演进

- [CHANGELOG.md](CHANGELOG.md)：按版本查看主要变化；
- [v0.2.0 恢复维护与 Rename](docs/iterations/v0.2.0-reactivation-and-rename.md)：了解为何恢复维护、哪些能力保持不变，以及 `boss-recruiting-auto` 的命名理由。

2026-08-06 的暂停判断没有被删除或改写；它作为一次真实的成本与风险评估保留在迭代记录中。恢复维护表示继续改进这套有边界的自动工作流，不代表取消人工监督或平台安全限制。
