from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_gemini_is_removed_from_runtime_contract(self) -> None:
        paths = [
            ROOT / "SKILL.md",
            ROOT / "assets" / "run-log-template.md",
            ROOT / "agents" / "openai.yaml",
        ]
        for path in paths:
            self.assertNotIn("gemini", path.read_text(encoding="utf-8").lower(), path)
        self.assertFalse((ROOT / "assets" / "gemini-screening-prompt.md").exists())

    def test_computer_use_owns_extraction_and_scroll(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for phrase in (
            "Computer Use 页面提取",
            "用 Computer Use 滚动并提取",
            "只滚动，不点击卡片或按钮",
            "滚动 `scroll_count` 次",
            "不得使用 browser-use CLI",
            "每次滚动后的岗位文本一致",
            "整批候选人数据作废",
            "computer_extraction_verified=true",
        ):
            self.assertIn(phrase, skill)
        self.assertNotIn("Browser Use 只读提取", skill)

    def test_codex_screening_subagent_handoff_is_explicit(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for phrase in (
            "派出一个 screening subagent",
            "冻结岗位上下文",
            "候选人只读数据集",
            "完整物化",
            "不得只引用主 Agent 的变量、上文或工具输出",
            "候选人数量和 SHA-256",
            "全部分片",
            "返回主 Agent",
            "screening_handoff_verified=true",
        ):
            self.assertIn(phrase, skill)

    def test_computer_use_owns_find_and_click(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for phrase in (
            "Command-F",
            "键名大小写敏感",
            "`Return`，不得使用 `RETURN`",
            "关闭 Find 栏",
            "同一候选人卡片块",
            "只从该卡片块",
            "只用 Computer Use 点击",
            "页面显示的“打招呼”",
        ):
            self.assertIn(phrase, skill)

    def test_subagent_prompt_exists_and_has_required_inputs(self) -> None:
        prompt_path = ROOT / "assets" / "codex-screening-subagent-prompt.md"
        self.assertTrue(prompt_path.is_file())
        prompt = prompt_path.read_text(encoding="utf-8")
        for placeholder in (
            "{{job_library_id}}",
            "{{job_library_version}}",
            "{{jd}}",
            "{{persona}}",
            "{{screening_criteria}}",
            "{{business_feedback}}",
            "{{candidate_count}}",
            "{{candidate_dataset_hash}}",
            "{{candidate_dataset}}",
            "{{candidate_limit}}",
        ):
            self.assertIn(placeholder, prompt)
        self.assertIn("INPUT_INCOMPLETE", prompt)
        self.assertIn("Markdown 信息表", prompt)


if __name__ == "__main__":
    unittest.main()
