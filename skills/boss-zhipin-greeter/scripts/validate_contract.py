#!/usr/bin/env python3
"""Validate high-risk workflow invariants for boss-zhipin-greeter."""

from __future__ import annotations

import sys
from pathlib import Path


def require_phrases(text: str, phrases: dict[str, str], errors: list[str], prefix: str) -> None:
    for name, phrase in phrases.items():
        if phrase not in text:
            errors.append(f"{prefix}:{name}")


def main() -> int:
    skill_path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).resolve().parents[1] / "SKILL.md"
    )
    root = skill_path.parent
    text = skill_path.read_text(encoding="utf-8")
    errors: list[str] = []

    require_phrases(
        text,
        {
            "job query input": "`job_query`：必填",
            "delegated job library": "**REQUIRED SUB-SKILL:** Use hr-job-profile-library",
            "exact resolution": "`status: resolved`",
            "active job gate": "`status: active`",
            "four-file context": "`jd.md`、`persona.md`、`screening-criteria.md`、`business-feedback.md`",
            "frozen context": "冻结岗位上下文",
            "screening mode": "`screening_mode=codex_subagent`",
            "computer extraction": "Computer Use 页面提取",
            "computer scroll extraction": "用 Computer Use 滚动并提取",
            "computer extraction click gate": "只滚动，不点击卡片或按钮",
            "bounded scroll": "滚动 `scroll_count` 次",
            "other channels forbidden": "不得使用 browser-use CLI",
            "same page": "同一 BOSS 标签页",
            "extraction state": "`computer_extraction_verified=true`",
            "dataset hash": "SHA-256",
            "screening subagent": "派出一个 screening subagent",
            "candidate dataset": "候选人只读数据集",
            "materialized handoff": "完整物化",
            "no context reference": "不得只引用主 Agent 的变量、上文或工具输出",
            "handoff count hash": "候选人数量和 SHA-256",
            "chunk completion": "全部分片",
            "return to main": "返回主 Agent",
            "handoff gate": "`screening_handoff_verified=true`",
            "subagent correction bound": "允许纠正一次",
            "find trigger": "Command-F",
            "case sensitive key": "键名大小写敏感",
            "correct return key": "`Return`，不得使用 `RETURN`",
            "close find bar": "关闭 Find 栏",
            "same candidate block": "同一候选人卡片块",
            "button in candidate block": "只从该卡片块",
            "computer click": "只用 Computer Use 点击",
            "default greeting": "页面显示的“打招呼”",
            "result count semantics": "`Result 0 of 1` 表示有 1 个命中",
            "sentinel fallback": "哨兵字符回退",
            "run log validator": "scripts/validate_run_log.py <本轮日志路径>",
        },
        errors,
        "skill",
    )

    if "gemini" in text.lower():
        errors.append("skill:legacy Gemini runtime content")
    if len(text.splitlines()) > 500:
        errors.append("skill:SKILL.md exceeds 500 lines")

    prompt_path = root / "assets" / "codex-screening-subagent-prompt.md"
    if not prompt_path.is_file():
        errors.append("prompt:missing codex-screening-subagent-prompt.md")
    else:
        prompt = prompt_path.read_text(encoding="utf-8")
        require_phrases(
            prompt,
            {
                "job id": "{{job_library_id}}",
                "job name": "{{job_library_name}}",
                "job version": "{{job_library_version}}",
                "candidate limit": "{{candidate_limit}}",
                "candidate count": "{{candidate_count}}",
                "dataset hash": "{{candidate_dataset_hash}}",
                "jd": "{{jd}}",
                "persona": "{{persona}}",
                "criteria": "{{screening_criteria}}",
                "feedback": "{{business_feedback}}",
                "dataset": "{{candidate_dataset}}",
                "incomplete input": "INPUT_INCOMPLETE",
                "table": "Markdown 信息表",
                "missing is not absent": "未展示",
                "no padding": "不要凑数",
                "feedback boundary": "不得单独作为硬性淘汰标准",
            },
            errors,
            "prompt",
        )
    if (root / "assets" / "gemini-screening-prompt.md").exists():
        errors.append("prompt:legacy prompt asset still exists")

    template_path = root / "assets" / "run-log-template.md"
    if not template_path.is_file():
        errors.append("template:missing run-log-template.md")
    else:
        template = template_path.read_text(encoding="utf-8")
        require_phrases(
            template,
            {
                "job context": "job_context_loaded: true",
                "screening mode": 'screening_mode: "codex_subagent"',
                "extraction mode": 'computer_extraction_mode: "visible_state"',
                "extraction verified": "computer_extraction_verified:",
                "scrolls": "computer_scrolls_completed:",
                "candidate count": "computer_candidate_count:",
                "dataset hash": "computer_dataset_hash:",
                "subagent dispatched": "screening_subagent_dispatched:",
                "subagent completed": "screening_subagent_completed:",
                "handoff": "screening_handoff_verified:",
                "extraction ledger": "## Computer Use 滚动提取记录",
                "handoff ledger": "## Codex 筛选交接记录",
                "forbidden actions": "card_click=false｜button_click=false｜input=false｜navigation=false",
            },
            errors,
            "template",
        )
        if "gemini" in template.lower():
            errors.append("template:legacy Gemini fields")

    validator_path = root / "scripts" / "validate_run_log.py"
    if not validator_path.is_file():
        errors.append("validator:missing validate_run_log.py")
    else:
        validator = validator_path.read_text(encoding="utf-8")
        require_phrases(
            validator,
            {
                "screening mode": 'values["screening_mode"] != "codex_subagent"',
                "extraction verified": "computer_extraction_verified=true",
                "scroll equality": "computer_scrolls_completed=scroll_count",
                "hash": "computer_dataset_hash",
                "subagent complete": "screening_subagent_completed=true",
                "handoff": "screening_handoff_verified=true",
                "legacy fields": "forbidden Gemini field",
                "temporary status": 'r"^- 处理状态：(locating|needs_recheck)',
            },
            errors,
            "validator",
        )

    openai_yaml_path = root / "agents" / "openai.yaml"
    if not openai_yaml_path.is_file():
        errors.append("interface:missing agents/openai.yaml")
    else:
        openai_yaml = openai_yaml_path.read_text(encoding="utf-8")
        require_phrases(
            openai_yaml,
            {
                "invocation": "$boss-zhipin-greeter",
                "job": "示例岗位",
                "job library": "岗位知识库",
                "computer extraction": "全程只用 Computer Use",
                "subagent": "screening subagent",
                "find": "Command-F",
                "computer use": "Computer Use",
            },
            errors,
            "interface",
        )
        if "gemini" in openai_yaml.lower():
            errors.append("interface:legacy Gemini content")

    ordered = [
        ("### 1. 岗位库预检", "### 2. 建立日志"),
        ("### 2. 建立日志", "### 3. 用 Computer Use 核验页面与岗位"),
        ("### 3. 用 Computer Use 核验页面与岗位", "### 4. 用 Computer Use 滚动并提取"),
        ("### 4. 用 Computer Use 滚动并提取", "### 5. 派出 Codex screening subagent"),
        ("### 5. 派出 Codex screening subagent", "### 6. 主 Agent 用 Computer Use 定位与点击"),
    ]
    for first, second in ordered:
        if first in text and second in text and text.index(first) >= text.index(second):
            errors.append(f"order:{first} -> {second}")

    if errors:
        print("Contract validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Contract validation passed: {skill_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
