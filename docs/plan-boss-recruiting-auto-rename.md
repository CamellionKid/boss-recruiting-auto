# `boss-recruiting-auto` Rename 与恢复维护计划

## 目标

将仓库从 `boss-auto-greeter-system` 重命名为 `boss-recruiting-auto`，撤销 README 的“已弃用/仅作历史存档”定位，并补齐能够解释项目演进、当前边界和升级理由的迭代文档。

本次只重命名仓库与项目展示名称，保留两个现有 Skill 的稳定调用接口：

- `hr-job-profile-library`：岗位 JD、人才画像、筛选标准、业务反馈和版本管理；
- `boss-zhipin-greeter`：读取冻结的岗位上下文后，执行有边界的候选人提取、筛选、定位和默认打招呼。

## 当前状态与基线证据

- GitHub 仓库当前公开、未归档，默认分支为 `main`。
- 2026-08-06 的提交 `1e8d3fe` 只在 `README.md` 新增了弃用说明，没有删除或削弱两个 Skill。
- `hr-job-profile-library` 当前包含岗位模板、岗位索引、组织背景、版本化 CLI 和契约测试。
- `boss-zhipin-greeter` 当前包含 Computer Use 工作流、Codex screening subagent 提示词、运行日志模板及校验器。
- 变更前基线验证：岗位画像 Skill 32 项测试通过，操作 Skill 14 项测试通过，BOSS 工作流契约校验通过。

## 实施范围

### 1. 恢复项目维护状态

- 删除 README 顶部的 `DEPRECATED（已弃用）` 和“仅作历史存档”表述。
- 改写项目定位，明确它是由“岗位画像 Skill + BOSS 操作 Skill”组成的自动招聘工作流。
- 保留自动化边界说明：单轮、有候选人数上限、严格岗位上下文、Computer Use 页面操作、默认招呼语和可审计日志。
- 将此前关于命中率、Token 成本和半自动替代方案的判断移入迭代文档，作为历史决策而非当前状态。

### 2. Rename

- GitHub 仓库：`CamellionKid/boss-auto-greeter-system` → `CamellionKid/boss-recruiting-auto`。
- README 标题与项目内仓库名引用统一改为 `BOSS Recruiting Auto` / `boss-recruiting-auto`。
- 更新 GitHub description，使其同时覆盖岗位画像管理与自动筛选触达。
- 重命名完成后更新本地 `origin`，验证旧 URL 的 GitHub 重定向和新 URL 的默认分支。
- 不重命名 `hr-job-profile-library` 与 `boss-zhipin-greeter`，避免破坏用户现有命令、Skill 依赖、测试和已下载的 `.skill` 包。

### 3. 迭代文档

- 新增根目录 `CHANGELOG.md`，以版本为主线记录：
  - `v0.1.0`：双 Skill 的隐私安全初版；
  - `2026-08-06`：基于命中率和成本的暂停/弃用判断；
  - `v0.2.0`：恢复维护、仓库 rename、重新确认自动化边界。
- 新增 `docs/iterations/v0.2.0-reactivation-and-rename.md`，写清：
  - 为什么恢复，而不是抹掉之前的判断；
  - 哪些核心资产一直保留；
  - 仓库名为什么从 `auto-greeter-system` 调整为 `recruiting-auto`；
  - 本次未改变的兼容接口与安全边界；
  - 后续迭代应该用什么证据判断自动化是否继续扩展。
- README 只保留简明的当前状态、架构、安装、使用和文档入口，详细历史放入迭代文档。

### 4. 验证与发布

- 运行两个 Skill 的全部单元测试和 BOSS 契约校验。
- 检查仓库名、标题、链接和状态描述是否一致，确保没有残留的当前态 `deprecated` 表述。
- 检查 `.skill` 分发包与两个 Skill 目录仍存在；本次不因仓库 rename 改动包内稳定 Skill 名。
- 自查最终 diff，只提交本次文档和 rename 相关改动。
- 在 `main` 创建一次清晰提交并推送，然后执行 GitHub 仓库 rename 与远端元数据更新。

## 不在本次范围

- 不改变 BOSS 实际页面操作协议或筛选算法。
- 不导入真实岗位、候选人、组织资料或运行日志。
- 不重命名两个 Skill，也不引入旧名称兼容层。
- 不创建自动发布、定时任务或新的外部触达能力。

## 完成标准

1. 新仓库 URL 为 `https://github.com/CamellionKid/boss-recruiting-auto`，公开、未归档，默认分支仍为 `main`。
2. README 不再将项目标为弃用，并准确展示两个核心 Skill 及其边界。
3. `CHANGELOG.md` 和 `docs/iterations/v0.2.0-reactivation-and-rename.md` 能独立解释初版、暂停判断和恢复维护三段历史。
4. 两个 Skill 的名称、目录、分发包及调用关系保持稳定。
5. 32 项岗位画像测试、14 项操作测试和契约校验全部通过。
