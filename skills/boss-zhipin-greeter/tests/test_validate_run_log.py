from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_run_log.py"


def render_log(
    *,
    status: str = "completed",
    job_context_loaded: bool = True,
    screening_mode: str = "codex_subagent",
    computer_extraction_verified: bool = True,
    scroll_count: int = 4,
    computer_scrolls_completed: int = 4,
    computer_candidate_count: int = 12,
    computer_dataset_hash: str = "a" * 64,
    subagent_dispatched: bool = True,
    subagent_completed: bool = True,
    handoff_verified: bool = True,
    recommended_count: int = 1,
    candidate_status: str = "greeted",
) -> str:
    candidate_block = "无推荐候选人。"
    if recommended_count:
        candidate_block = f'''### 1. 王某

- Codex 选择理由：已展示经历与岗位要求匹配
- 页面证据：卡片显示示例岗位、PCB 与调试经验
- 处理状态：{candidate_status}
- 查找证据：王某｜Result 0 of 1｜Command-F + Return
- 页面核验信息：示例岗位｜3 年
- 执行结果：{candidate_status if candidate_status not in {"locating", "needs_recheck"} else ""}
- 执行时间：2026-07-18 19:00:00
'''
    return f'''---
status: {status}
job_query: "示例岗位"
job_library_id: "sample-role"
job_library_name: "示例岗位"
job_library_version: "1.0.0"
job_context_files: "jd.md,persona.md,screening-criteria.md,business-feedback.md"
job_context_loaded: {str(job_context_loaded).lower()}
screening_mode: "{screening_mode}"
computer_extraction_mode: "visible_state"
computer_extraction_verified: {str(computer_extraction_verified).lower()}
scroll_count: {scroll_count}
computer_scrolls_completed: {computer_scrolls_completed}
computer_candidate_count: {computer_candidate_count}
computer_dataset_hash: "{computer_dataset_hash}"
screening_subagent_dispatched: {str(subagent_dispatched).lower()}
screening_subagent_completed: {str(subagent_completed).lower()}
screening_handoff_verified: {str(handoff_verified).lower()}
candidate_limit: 8
recommended_count: {recommended_count}
greeted_count: {recommended_count if candidate_status == "greeted" else 0}
contacted_skipped_count: 0
not_found_count: 0
identity_mismatch_count: 0
unconfirmed_count: 0
failed_count: 0
---

## Computer Use 滚动提取记录

- 页面：BOSS 推荐牛人｜同一已视觉确认标签页与岗位
- 滚动：requested={scroll_count}｜completed={computer_scrolls_completed}
- 提取：candidate_count={computer_candidate_count}｜dataset_sha256={computer_dataset_hash}
- 提取阶段禁止动作：card_click=false｜button_click=false｜input=false｜navigation=false

## Codex 筛选交接记录

- 调度：screening_subagent_dispatched={str(subagent_dispatched).lower()}
- 完成：screening_subagent_completed={str(subagent_completed).lower()}
- 输入：candidate_count={computer_candidate_count}｜job_context_loaded={str(job_context_loaded).lower()}
- 输出：shortlist_count={recommended_count}｜screening_handoff_verified={str(handoff_verified).lower()}

## 候选人记录

{candidate_block}
'''


class ValidateRunLogTests(unittest.TestCase):
    def validate(self, text: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "run.md"
            path.write_text(text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), str(path)],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_completed_codex_subagent_run_passes(self) -> None:
        result = self.validate(render_log())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_completed_run_requires_loaded_job_context(self) -> None:
        result = self.validate(render_log(job_context_loaded=False))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("job_context_loaded=true", result.stdout)

    def test_completed_run_requires_verified_computer_extraction(self) -> None:
        result = self.validate(render_log(computer_extraction_verified=False))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("computer_extraction_verified=true", result.stdout)

    def test_completed_run_requires_all_requested_scrolls(self) -> None:
        result = self.validate(render_log(computer_scrolls_completed=3))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("computer_scrolls_completed", result.stdout)

    def test_completed_run_requires_dataset_hash(self) -> None:
        result = self.validate(render_log(computer_dataset_hash="not-a-hash"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("computer_dataset_hash", result.stdout)

    def test_completed_run_requires_screening_subagent_handoff(self) -> None:
        result = self.validate(render_log(subagent_completed=False, handoff_verified=False))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("screening_subagent_completed=true", result.stdout)
        self.assertIn("screening_handoff_verified=true", result.stdout)

    def test_legacy_gemini_fields_are_forbidden(self) -> None:
        text = render_log().replace(
            'screening_mode: "codex_subagent"',
            'screening_mode: "codex_subagent"\ngemini_prompt_submitted: false',
        )
        result = self.validate(text)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden Gemini field", result.stdout)

    def test_interrupted_pre_subagent_run_is_valid(self) -> None:
        result = self.validate(
            render_log(
                status="interrupted",
                computer_extraction_verified=False,
                computer_scrolls_completed=0,
                computer_candidate_count=0,
                computer_dataset_hash="",
                subagent_dispatched=False,
                subagent_completed=False,
                handoff_verified=False,
                recommended_count=0,
            )
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_completed_run_rejects_temporary_candidate_status(self) -> None:
        result = self.validate(render_log(candidate_status="needs_recheck"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("temporary candidate status", result.stdout)


if __name__ == "__main__":
    unittest.main()
