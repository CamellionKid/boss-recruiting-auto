# Changelog

本文件记录 `boss-recruiting-auto` 的主要迭代。版本号描述仓库内两套 Skills 的整体交付状态，不替代各岗位画像自身的版本历史。

## [0.2.0] - 2026-08-15

### Changed

- 将项目从 `boss-auto-greeter-system` 重命名为 `boss-recruiting-auto`，使名称覆盖“岗位画像 + 自动筛选触达”的完整闭环，而不只强调打招呼动作。
- 将 README 从“已弃用/历史存档”恢复为“维护中”，并补充当前自动化边界、双 Skill 分工和项目演进入口。
- 新增本 Changelog 和 v0.2.0 迭代说明，区分“暂停将全自动 Sourcing 作为日常默认方案”与“废弃仓库核心能力”。

### Kept stable

- `hr-job-profile-library` 和 `boss-zhipin-greeter` 的名称及调用方式保持不变。
- 岗位上下文只读委派、Computer Use 页面操作、候选人数上限、默认招呼语和可审计日志等安全契约保持不变。
- 公开分发版仍为空岗位库，不包含真实组织、岗位、候选人或运行日志数据。

## 2026-08-06 - 自动化方案暂停判断

- README 曾将仓库标记为 deprecated，并把它定位为历史存档。
- 当时记录的主要原因是筛选命中率波动和单轮 Token 成本偏高；日常工作因此转向人工主导的半自动 Sourcing。
- 该次变更只修改 README，没有删除、迁移或降级两个 Skills 的代码、模板、测试和分发包。
- v0.2.0 保留这次判断作为历史证据，但修正了“暂停某种使用方式等同于整个项目弃用”的状态表达。

## [0.1.0] - 2026-07-18

### Added

- 发布隐私安全的 `hr-job-profile-library`，支持岗位 JD、人才画像、筛选标准、匿名业务反馈、版本快照与归档。
- 发布 `boss-zhipin-greeter`，支持单轮 BOSS 推荐牛人提取、Codex screening subagent 筛选、Computer Use 定位和默认打招呼。
- 建立两个 Skills 之间的只读岗位上下文委派：精确匹配一个启用岗位，冻结版本与四份上下文后再进入浏览器阶段。
- 提供空岗位索引、通用模板、测试、契约校验器和 `.skill` 分发包。

[0.2.0]: https://github.com/CamellionKid/boss-recruiting-auto/compare/985ca26...main
[0.1.0]: https://github.com/CamellionKid/boss-recruiting-auto/commit/985ca260ad8c553956c00eb7a75261a378c03af3
