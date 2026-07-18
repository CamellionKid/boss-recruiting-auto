#!/usr/bin/env python3
"""Validate final run-log gates for boss-zhipin-greeter."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("unterminated YAML frontmatter") from exc

    values: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"\'')
    return values


def parse_bool(value: str, key: str) -> bool:
    normalized = value.lower()
    if normalized not in {"true", "false"}:
        raise ValueError(f"{key} must be true or false")
    return normalized == "true"


def parse_int(value: str, key: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{key} must be an integer") from exc


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_run_log.py <run-log.md>")
        return 2

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"Run-log validation failed: file not found: {path}")
        return 1

    text = path.read_text(encoding="utf-8")
    errors: list[str] = []

    try:
        values = parse_frontmatter(text)
        for key in sorted(key for key in values if key.lower().startswith("gemini_")):
            errors.append(f"forbidden Gemini field: {key}")

        required = {
            "status",
            "job_query",
            "job_library_id",
            "job_library_name",
            "job_library_version",
            "job_context_files",
            "job_context_loaded",
            "screening_mode",
            "computer_extraction_mode",
            "computer_extraction_verified",
            "scroll_count",
            "computer_scrolls_completed",
            "computer_candidate_count",
            "computer_dataset_hash",
            "screening_subagent_dispatched",
            "screening_subagent_completed",
            "screening_handoff_verified",
            "candidate_limit",
            "recommended_count",
        }
        missing = sorted(required - values.keys())
        errors.extend(f"missing frontmatter field: {key}" for key in missing)

        if not missing:
            status = values["status"]
            job_context_loaded = parse_bool(
                values["job_context_loaded"], "job_context_loaded"
            )
            computer_extraction_verified = parse_bool(
                values["computer_extraction_verified"],
                "computer_extraction_verified",
            )
            scroll_count = parse_int(values["scroll_count"], "scroll_count")
            computer_scrolls_completed = parse_int(
                values["computer_scrolls_completed"], "computer_scrolls_completed"
            )
            computer_candidate_count = parse_int(
                values["computer_candidate_count"], "computer_candidate_count"
            )
            subagent_dispatched = parse_bool(
                values["screening_subagent_dispatched"],
                "screening_subagent_dispatched",
            )
            subagent_completed = parse_bool(
                values["screening_subagent_completed"],
                "screening_subagent_completed",
            )
            handoff_verified = parse_bool(
                values["screening_handoff_verified"],
                "screening_handoff_verified",
            )
            candidate_limit = parse_int(values["candidate_limit"], "candidate_limit")
            recommended_count = parse_int(
                values["recommended_count"], "recommended_count"
            )

            if status not in {"completed", "interrupted"}:
                errors.append("final status must be completed or interrupted")
            if not values["job_query"]:
                errors.append("job_query must not be empty")
            if not re.fullmatch(
                r"[a-z0-9]+(?:-[a-z0-9]+)*", values["job_library_id"]
            ):
                errors.append("job_library_id must be a non-empty canonical job id")
            if not values["job_library_name"]:
                errors.append("job_library_name must not be empty")
            if not re.fullmatch(r"\d+\.\d+\.\d+", values["job_library_version"]):
                errors.append("job_library_version must be a semantic version")

            expected_context_files = {
                "jd.md",
                "persona.md",
                "screening-criteria.md",
                "business-feedback.md",
            }
            actual_context_files = {
                item.strip()
                for item in values["job_context_files"].split(",")
                if item.strip()
            }
            if actual_context_files != expected_context_files:
                errors.append(
                    "job_context_files must list the four screening context files"
                )
            if values["screening_mode"] != "codex_subagent":
                errors.append("screening_mode must be codex_subagent")
            if values["computer_extraction_mode"] != "visible_state":
                errors.append("computer_extraction_mode must be visible_state")
            if not 3 <= scroll_count <= 5:
                errors.append("scroll_count must be between 3 and 5")
            if computer_scrolls_completed < 0:
                errors.append("computer_scrolls_completed cannot be negative")
            if computer_candidate_count < 0:
                errors.append("computer_candidate_count cannot be negative")
            if not 1 <= candidate_limit <= 8:
                errors.append("candidate_limit must be between 1 and 8")
            if recommended_count < 0 or recommended_count > candidate_limit:
                errors.append("recommended_count must be within candidate_limit")
            if recommended_count > computer_candidate_count:
                errors.append("recommended_count cannot exceed computer_candidate_count")

            extraction_match = re.search(
                r"^## Computer Use 滚动提取记录\s*$([\s\S]*?)(?=^## Codex 筛选交接记录\s*$)",
                text,
                re.MULTILINE,
            )
            handoff_match = re.search(
                r"^## Codex 筛选交接记录\s*$([\s\S]*?)(?=^## 候选人记录\s*$)",
                text,
                re.MULTILINE,
            )
            if not extraction_match:
                errors.append("missing Computer Use extraction ledger")
            if not handoff_match:
                errors.append("missing Codex screening handoff ledger")

            if status == "completed":
                if not job_context_loaded:
                    errors.append("completed run requires job_context_loaded=true")
                if not computer_extraction_verified:
                    errors.append(
                        "completed run requires computer_extraction_verified=true"
                    )
                if computer_scrolls_completed != scroll_count:
                    errors.append(
                        "completed run requires computer_scrolls_completed=scroll_count"
                    )
                if not re.fullmatch(
                    r"[0-9a-f]{64}", values["computer_dataset_hash"]
                ):
                    errors.append(
                        "completed run requires a valid computer_dataset_hash"
                    )
                if not subagent_dispatched:
                    errors.append(
                        "completed run requires screening_subagent_dispatched=true"
                    )
                if not subagent_completed:
                    errors.append(
                        "completed run requires screening_subagent_completed=true"
                    )
                if not handoff_verified:
                    errors.append(
                        "completed run requires screening_handoff_verified=true"
                    )
                if extraction_match:
                    extraction = extraction_match.group(1)
                    required_extraction_evidence = (
                        "BOSS 推荐牛人",
                        "同一已视觉确认标签页与岗位",
                        f"requested={scroll_count}",
                        f"completed={computer_scrolls_completed}",
                        f"candidate_count={computer_candidate_count}",
                        f"dataset_sha256={values['computer_dataset_hash']}",
                        "card_click=false",
                        "button_click=false",
                        "input=false",
                        "navigation=false",
                    )
                    for phrase in required_extraction_evidence:
                        if phrase not in extraction:
                            errors.append(
                                f"Computer Use extraction evidence missing: {phrase}"
                            )
                if handoff_match:
                    handoff = handoff_match.group(1)
                    required_handoff_evidence = (
                        "screening_subagent_dispatched=true",
                        "screening_subagent_completed=true",
                        f"candidate_count={computer_candidate_count}",
                        f"shortlist_count={recommended_count}",
                        "screening_handoff_verified=true",
                    )
                    for phrase in required_handoff_evidence:
                        if phrase not in handoff:
                            errors.append(
                                f"Codex screening handoff evidence missing: {phrase}"
                            )
                if re.search(
                    r"^- 处理状态：(locating|needs_recheck)\s*$",
                    text,
                    re.MULTILINE,
                ):
                    errors.append("completed run contains temporary candidate status")
    except ValueError as exc:
        errors.append(str(exc))

    if errors:
        print("Run-log validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Run-log validation passed: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
