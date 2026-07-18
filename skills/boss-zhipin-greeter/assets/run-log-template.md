---
run_id: "{{run_id}}"
started_at: "{{started_at}}"
ended_at: ""
job_query: "{{job_query}}"
job_library_id: "{{job_library_id}}"
job_library_name: "{{job_library_name}}"
job_library_version: "{{job_library_version}}"
job_context_files: "jd.md,persona.md,screening-criteria.md,business-feedback.md"
job_context_loaded: true
screening_mode: "codex_subagent"
computer_extraction_mode: "visible_state"
computer_extraction_verified: false
boss_job: "{{boss_job}}"
scroll_count: {{scroll_count}}
computer_scrolls_completed: 0
computer_candidate_count: 0
computer_dataset_hash: ""
screening_subagent_dispatched: false
screening_subagent_completed: false
screening_handoff_verified: false
candidate_limit: {{candidate_limit}}
status: running
correction_count: 0
recommended_count: 0
greeted_count: 0
contacted_skipped_count: 0
not_found_count: 0
identity_mismatch_count: 0
unconfirmed_count: 0
failed_count: 0
---

# 本轮执行摘要

- BOSS 页面：推荐牛人｜{{boss_job}}
- 岗位知识：{{job_library_id}}｜v{{job_library_version}}｜job_context_loaded=true
- 筛选模式：codex_subagent
- Computer Use 提取：visible_state｜待填写
- Codex 推荐：待填写
- 成功打招呼：待填写
- 已联系跳过：待填写
- 未定位：待填写
- 身份不一致：待填写
- 未确认：待填写
- 异常：无

## Computer Use 滚动提取记录

- 页面：{{BOSS 推荐牛人｜同一已视觉确认标签页与岗位}}
- 滚动：{{requested=scroll_count｜completed=0}}
- 提取：{{candidate_count=0｜dataset_sha256=未生成}}
- 提取阶段禁止动作：card_click=false｜button_click=false｜input=false｜navigation=false

## Codex 筛选交接记录

- 调度：screening_subagent_dispatched=false
- 完成：screening_subagent_completed=false
- 输入：candidate_count=0｜job_context_loaded=true
- 输出：shortlist_count=0｜screening_handoff_verified=false

## 候选人记录

### 1. {{页面显示姓名}}

- Codex 选择理由：{{只写岗位相关理由}}
- 页面证据：{{只写冻结候选人数据中的证据}}
- 处理状态：{{locating | needs_recheck | greeted | contacted_skipped | not_found | identity_mismatch | unconfirmed | failed}}
- 查找证据：{{查询名｜Result n of m 或 0/0｜Command-F + Return；暂态时写缺失项}}
- 页面核验信息：{{职位｜公司或工作年限｜城市；仅写必要字段}}
- 执行结果：{{暂态时留空；终态填写 greeted | contacted_skipped | not_found | identity_mismatch | unconfirmed | failed}}
- 执行时间：{{YYYY-MM-DD HH:mm:ss}}
- 备注：{{可选；不得写联系方式或非岗位相关敏感信息}}

## 中断记录

- 中断步骤：{{仅在 status 为 interrupted 时填写}}
- 中断原因：{{仅在 status 为 interrupted 时填写}}
- 建议人工动作：{{仅在需要用户处理时填写}}

## 同轮纠错记录

- 纠错时间：{{仅在本轮发生恢复或复核时填写}}
- 纠错原因：{{误判来源与缺失证据}}
- 修正范围：{{候选人条目与汇总字段}}
