from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillContractTest(unittest.TestCase):
    def test_frontmatter_is_manual_only_and_explicit(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", skill, re.DOTALL)
        self.assertIsNotNone(match)
        frontmatter = match.group(1)
        self.assertIn("name: hr-job-profile-library", frontmatter)
        self.assertIn("$hr-job-profile-library", frontmatter)
        self.assertIn("Manual-only", frontmatter)
        self.assertIn("do not infer", frontmatter.lower())

    def test_skill_body_contains_execution_gates(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        required = (
            "未显式调用",
            "不得读取",
            "新建",
            "调用",
            "更新",
            "列表",
            "历史",
            "归档",
            "plan_hash",
            "预览",
            "用户确认",
            "validate",
            "读回",
            "L1/L2",
            "敏感个人信息",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)
        self.assertLessEqual(len(skill.splitlines()), 500)
        self.assertNotIn("[TODO", skill)

    def test_openai_metadata_disables_implicit_invocation(self) -> None:
        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "HR 招聘岗位 JD 与画像库"', metadata)
        self.assertIn("$hr-job-profile-library", metadata)
        self.assertIn("policy:", metadata)
        self.assertIn("allow_implicit_invocation: false", metadata)

    def test_explicit_boss_delegation_allows_read_only_screening_context(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        required = (
            "boss-zhipin-greeter",
            "受控委派",
            "只读",
            "job_query",
            "status: resolved",
            "status: active",
            "jd.md",
            "persona.md",
            "screening-criteria.md",
            "business-feedback.md",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)

    def test_delegated_mode_cannot_mutate_or_auto_select_suggestions(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for phrase in (
            "不得执行 `create`、`update`、`archive`",
            "不得自动采用 `suggested`",
            "不得把普通招聘话题视为受控委派",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)

    def test_downstream_codex_screening_keeps_candidate_data_outside_library(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for phrase in (
            "返回给主 Agent",
            "冻结岗位快照",
            "下游 screening subagent",
            "岗位库 Skill 不接收候选人身份信息",
            "候选人数据不得回传本 Skill",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)

    def test_public_library_starts_empty_and_generic(self) -> None:
        index = json.loads((ROOT / "references" / "job-index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["schema_version"], "1.0")
        self.assertEqual(index["company"], "未提供")
        self.assertEqual(index["jobs"], [])
        context = (ROOT / "references" / "organization-context.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("未提供", context)
        jobs_dir = ROOT / "references" / "jobs"
        self.assertFalse(jobs_dir.exists() and any(jobs_dir.iterdir()))

    def test_templates_and_schema_cover_all_job_files(self) -> None:
        template_dir = ROOT / "assets" / "job-template"
        expected = {
            "job.json",
            "jd.md",
            "persona.md",
            "screening-criteria.md",
            "business-feedback.md",
            "changelog.md",
        }
        self.assertEqual({path.name for path in template_dir.iterdir() if path.is_file()}, expected)
        for filename in expected - {"job.json", "changelog.md"}:
            self.assertIn("未提供", (template_dir / filename).read_text(encoding="utf-8"))
        schema = (ROOT / "references" / "job-schema.md").read_text(encoding="utf-8")
        for phrase in ("1.0.0", "L1", "L4", "history/v", "plan_hash", "candidate_name"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, schema)

    def test_distribution_contains_no_source_specific_identity_or_role(self) -> None:
        forbidden = (
            "mam" + "motion",
            "库" + "犸",
            "hardware" + "-engineer",
            "硬件" + "工程师",
            "/" + "Users/",
            "camel" + "lionkid",
            "Dar" + "ren",
        )
        for path in ROOT.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for phrase in forbidden:
                with self.subTest(path=path, phrase=phrase):
                    self.assertNotIn(phrase, text)

    def test_changelog_template_does_not_leave_a_false_empty_state(self) -> None:
        template = (ROOT / "assets" / "job-template" / "changelog.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("岗位创建时由脚本写入首条记录", template)


if __name__ == "__main__":
    unittest.main()
