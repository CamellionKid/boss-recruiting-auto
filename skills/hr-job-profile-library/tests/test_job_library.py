from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "job_library.py"


def load_module():
    spec = importlib.util.spec_from_file_location("job_library", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load job_library.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class JobLibraryCLITest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "references" / "jobs").mkdir(parents=True)
        (self.root / "references" / "job-index.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "company": "未提供",
                    "updated_at": "2026-07-18",
                    "jobs": [],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_cli(self, *args: str, expect: int = 0) -> tuple[subprocess.CompletedProcess[str], dict]:
        command = [sys.executable, str(SCRIPT), "--root", str(self.root), *args]
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(
            completed.returncode,
            expect,
            msg=f"command: {command}\nstdout: {completed.stdout}\nstderr: {completed.stderr}",
        )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"CLI did not return JSON: {exc}\nstdout={completed.stdout!r}")
        return completed, payload

    def write_payload(self, name: str, payload: dict) -> Path:
        path = self.root / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def create_payload(self, job_id: str = "sample-role", name: str = "示例岗位") -> dict:
        return {
            "actor": "tester",
            "reason": "首次建立岗位",
            "source": "用户提供资料",
            "job": {
                "id": job_id,
                "name": name,
                "english_name": "Sample Role",
                "aliases": ["示例岗位别名", "Sample Role"],
                "family": "示例职能",
                "department": "未提供",
                "location": "未提供",
                "status": "active",
            },
            "files": {
                "jd": "# 正式 JD\n\n## 岗位职责\n\n- 负责示例岗位的核心流程。\n",
                "persona": "# 招聘画像\n\n## 核心人才特征\n\n未提供\n",
                "screening-criteria": "# 筛选标准\n\n## 硬性条件\n\n未提供\n",
            },
        }

    def seed_job(self, payload: dict | None = None) -> dict:
        payload = payload or self.create_payload()
        input_path = self.write_payload("create.json", payload)
        _, preview = self.run_cli("create", "--input", str(input_path))
        _, applied = self.run_cli(
            "create",
            "--input",
            str(input_path),
            "--apply",
            "--plan-hash",
            preview["plan_hash"],
        )
        return applied

    def test_script_exists(self) -> None:
        self.assertTrue(SCRIPT.exists(), "scripts/job_library.py is missing")

    def test_empty_library_validates_and_lists(self) -> None:
        _, validated = self.run_cli("validate", "--json")
        self.assertTrue(validated["ok"])
        self.assertEqual(validated["job_count"], 0)

        _, listed = self.run_cli("list", "--status", "all", "--json")
        self.assertTrue(listed["ok"])
        self.assertEqual(listed["jobs"], [])

    def test_create_preview_is_non_mutating_and_apply_requires_matching_hash(self) -> None:
        input_path = self.write_payload("create.json", self.create_payload())
        before = (self.root / "references" / "job-index.json").read_bytes()

        _, preview = self.run_cli("create", "--input", str(input_path))
        self.assertEqual(preview["result"], "preview")
        self.assertFalse(preview["applied"])
        self.assertTrue(preview["plan_hash"])
        self.assertFalse((self.root / "references" / "jobs" / "sample-role").exists())
        self.assertEqual((self.root / "references" / "job-index.json").read_bytes(), before)

        _, rejected = self.run_cli(
            "create",
            "--input",
            str(input_path),
            "--apply",
            "--plan-hash",
            "stale-hash",
            expect=2,
        )
        self.assertFalse(rejected["ok"])
        self.assertFalse((self.root / "references" / "jobs" / "sample-role").exists())

        _, applied = self.run_cli(
            "create",
            "--input",
            str(input_path),
            "--apply",
            "--plan-hash",
            preview["plan_hash"],
        )
        self.assertTrue(applied["ok"])
        self.assertTrue(applied["applied"])
        self.assertEqual(applied["version"]["to"], "1.0.0")

    def test_preview_hash_expires_when_index_state_changes(self) -> None:
        input_path = self.write_payload("create.json", self.create_payload())
        _, preview = self.run_cli("create", "--input", str(input_path))
        index_file = self.root / "references" / "job-index.json"
        index = json.loads(index_file.read_text(encoding="utf-8"))
        index["updated_at"] = "2026-07-19"
        index_file.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")

        _, result = self.run_cli(
            "create",
            "--input",
            str(input_path),
            "--apply",
            "--plan-hash",
            preview["plan_hash"],
            expect=2,
        )
        self.assertIn("plan_hash", result["error"])
        self.assertFalse((self.root / "references" / "jobs" / "sample-role").exists())

    def test_preview_hash_binds_rendered_templates(self) -> None:
        payload = self.create_payload()
        payload["files"].pop("persona")
        input_path = self.write_payload("create.json", payload)
        _, preview = self.run_cli("create", "--input", str(input_path))
        template_dir = self.root / "assets" / "job-template"
        template_dir.mkdir(parents=True)
        (template_dir / "persona.md").write_text(
            "# {{JOB_NAME}}｜招聘画像\n\n模板在预览后发生变化。\n",
            encoding="utf-8",
        )

        _, result = self.run_cli(
            "create",
            "--input",
            str(input_path),
            "--apply",
            "--plan-hash",
            preview["plan_hash"],
            expect=2,
        )
        self.assertIn("plan_hash", result["error"])

    def test_create_preview_includes_rendered_content(self) -> None:
        input_path = self.write_payload("create.json", self.create_payload())
        _, preview = self.run_cli("create", "--input", str(input_path))
        self.assertEqual(preview["preview"]["metadata"]["id"], "sample-role")
        self.assertIn("示例岗位的核心流程", preview["preview"]["files"]["jd.md"])
        self.assertIn("未提供", preview["preview"]["files"]["business-feedback.md"])

    def test_create_fills_missing_markdown_sections_without_inventing(self) -> None:
        payload = self.create_payload()
        payload["files"].pop("persona")
        self.seed_job(payload)
        job_dir = self.root / "references" / "jobs" / "sample-role"
        self.assertIn("未提供", (job_dir / "persona.md").read_text(encoding="utf-8"))
        self.assertIn("未提供", (job_dir / "business-feedback.md").read_text(encoding="utf-8"))

    def test_create_preview_reports_defaulted_missing_fields(self) -> None:
        payload = self.create_payload()
        payload["job"].pop("department")
        payload["job"].pop("english_name")
        payload["files"].pop("persona")
        input_path = self.write_payload("create.json", payload)
        _, preview = self.run_cli("create", "--input", str(input_path))
        self.assertIn("job.department", preview["pending"])
        self.assertIn("job.english_name", preview["pending"])
        self.assertIn("files.persona", preview["pending"])

    def test_duplicate_id_or_standard_name_is_rejected(self) -> None:
        self.seed_job()
        duplicate_id = self.create_payload(name="另一个示例岗位")
        path = self.write_payload("duplicate-id.json", duplicate_id)
        _, result = self.run_cli("create", "--input", str(path), expect=2)
        self.assertIn("ID", result["error"])

        duplicate_name = self.create_payload(job_id="sample-role-2")
        path = self.write_payload("duplicate-name.json", duplicate_name)
        _, result = self.run_cli("create", "--input", str(path), expect=2)
        self.assertIn("标准名称", result["error"])

    def test_resolve_handles_exact_ambiguous_and_suggested_matches(self) -> None:
        first = self.create_payload("mechanical-drawing-engineer", "结构绘图工程师")
        first["job"]["aliases"] = ["结构画图", "Creo绘图"]
        first["job"]["english_name"] = "Mechanical Drawing Engineer"
        self.seed_job(first)

        second = self.create_payload("mechanical-design-engineer", "结构设计工程师")
        second["job"]["aliases"] = ["结构画图", "机械结构工程师"]
        second["job"]["english_name"] = "Mechanical Design Engineer"
        self.write_payload("create-2.json", second)
        path = self.root / "create-2.json"
        _, preview = self.run_cli("create", "--input", str(path))
        self.run_cli("create", "--input", str(path), "--apply", "--plan-hash", preview["plan_hash"])

        _, exact = self.run_cli("resolve", "--query", "mechanical-drawing-engineer", "--json")
        self.assertEqual(exact["status"], "resolved")
        self.assertEqual(exact["matches"][0]["id"], "mechanical-drawing-engineer")

        _, ambiguous = self.run_cli("resolve", "--query", "结构画图", "--json")
        self.assertEqual(ambiguous["status"], "ambiguous")
        self.assertEqual(len(ambiguous["matches"]), 2)

        _, suggested = self.run_cli("resolve", "--query", "结构设计", "--json")
        self.assertEqual(suggested["status"], "suggested")
        self.assertFalse(suggested["auto_selected"])

    def test_update_creates_snapshot_and_uses_version_mapping(self) -> None:
        self.seed_job()
        update = {
            "job_id": "sample-role",
            "expected_version": "1.0.0",
            "change_type": "wording",
            "actor": "tester",
            "reason": "明确职责表述",
            "source": "用户确认",
            "files": {"jd": "# 正式 JD\n\n## 岗位职责\n\n- 负责更新后的示例岗位核心流程。\n"},
        }
        input_path = self.write_payload("update.json", update)
        _, preview = self.run_cli("update", "--input", str(input_path))
        self.assertEqual(preview["version"], {"from": "1.0.0", "to": "1.0.1"})
        self.assertIn("示例岗位的核心流程", preview["diff"]["jd"])
        self.assertIn("更新后的示例岗位核心流程", preview["diff"]["jd"])
        self.assertFalse((self.root / "references" / "jobs" / "sample-role" / "history").exists())

        self.run_cli(
            "update",
            "--input",
            str(input_path),
            "--apply",
            "--plan-hash",
            preview["plan_hash"],
        )
        job_dir = self.root / "references" / "jobs" / "sample-role"
        snapshot = job_dir / "history" / "v1.0.0"
        self.assertTrue((snapshot / "job.json").exists())
        self.assertIn("示例岗位的核心流程", (snapshot / "jd.md").read_text(encoding="utf-8"))
        self.assertEqual(json.loads((job_dir / "job.json").read_text())["current_version"], "1.0.1")
        self.assertIn("1.0.0 → 1.0.1", (job_dir / "changelog.md").read_text(encoding="utf-8"))

    def test_minor_and_major_version_mapping(self) -> None:
        cases = [("persona", "1.1.0"), ("role-scope", "2.0.0")]
        for change_type, expected in cases:
            with self.subTest(change_type=change_type):
                with tempfile.TemporaryDirectory() as isolated:
                    original_root = self.root
                    self.root = Path(isolated)
                    (self.root / "references" / "jobs").mkdir(parents=True)
                    (self.root / "references" / "job-index.json").write_text(
                        json.dumps(
                            {
                                "schema_version": "1.0",
                                "company": "未提供",
                                "updated_at": "2026-07-18",
                                "jobs": [],
                            },
                            ensure_ascii=False,
                        ),
                        encoding="utf-8",
                    )
                    try:
                        self.seed_job()
                        update = {
                            "job_id": "sample-role",
                            "expected_version": "1.0.0",
                            "change_type": change_type,
                            "actor": "tester",
                            "reason": "版本映射测试",
                            "source": "用户确认",
                            "files": {"persona": "# 招聘画像\n\n已更新\n"},
                        }
                        path = self.write_payload(f"{change_type}.json", update)
                        _, preview = self.run_cli("update", "--input", str(path))
                        self.assertEqual(preview["version"]["to"], expected)
                    finally:
                        self.root = original_root

    def test_low_evidence_feedback_cannot_be_promoted(self) -> None:
        self.seed_job()
        update = {
            "job_id": "sample-role",
            "expected_version": "1.0.0",
            "change_type": "screening",
            "actor": "tester",
            "reason": "新增淘汰项",
            "source": "单次面试反馈",
            "files": {"screening-criteria": "# 筛选标准\n\n- 沟通表达差则淘汰。\n"},
            "feedback": [
                {
                    "id": "fb-001",
                    "level": "L1",
                    "date": "2026-07-18",
                    "content": "一次面试中表达不够清楚。",
                    "context": "匿名候选人单次面试",
                    "promote_to_formal": True,
                    "promotion_targets": ["screening-criteria"],
                }
            ],
        }
        path = self.write_payload("low-evidence.json", update)
        _, result = self.run_cli("update", "--input", str(path), expect=2)
        self.assertIn("L1/L2", result["error"])

        update["change_type"] = "feedback"
        update["files"] = {}
        update["feedback"][0]["promote_to_formal"] = False
        path = self.write_payload("feedback-only.json", update)
        _, preview = self.run_cli("update", "--input", str(path))
        self.assertEqual(preview["version"]["to"], "1.0.1")
        self.run_cli(
            "update",
            "--input",
            str(path),
            "--apply",
            "--plan-hash",
            preview["plan_hash"],
        )
        feedback_text = (
            self.root
            / "references"
            / "jobs"
            / "sample-role"
            / "business-feedback.md"
        ).read_text(encoding="utf-8")
        self.assertIn("fb-001", feedback_text)
        self.assertNotIn("尚无已记录的匿名业务反馈", feedback_text)

    def test_high_evidence_feedback_can_be_promoted_with_target_file(self) -> None:
        self.seed_job()
        update = {
            "job_id": "sample-role",
            "expected_version": "1.0.0",
            "change_type": "screening",
            "actor": "tester",
            "reason": "用人经理确认筛选口径",
            "source": "匿名业务反馈",
            "files": {"screening-criteria": "# 筛选标准\n\n- 能清楚说明岗位相关方案取舍。\n"},
            "feedback": [
                {
                    "id": "fb-003",
                    "level": "L3",
                    "date": "2026-07-18",
                    "content": "需要清楚说明岗位相关方案取舍。",
                    "context": "用人经理确认口径",
                    "promote_to_formal": True,
                    "promotion_targets": ["screening-criteria"],
                }
            ],
        }
        path = self.write_payload("high-evidence.json", update)
        _, preview = self.run_cli("update", "--input", str(path))
        _, applied = self.run_cli(
            "update",
            "--input",
            str(path),
            "--apply",
            "--plan-hash",
            preview["plan_hash"],
        )
        self.assertTrue(applied["applied"])
        job_dir = self.root / "references" / "jobs" / "sample-role"
        self.assertIn("fb-003", (job_dir / "business-feedback.md").read_text(encoding="utf-8"))
        self.assertIn("岗位相关方案取舍", (job_dir / "screening-criteria.md").read_text(encoding="utf-8"))

    def test_no_effect_update_is_rejected(self) -> None:
        self.seed_job()
        job_dir = self.root / "references" / "jobs" / "sample-role"
        current = (job_dir / "jd.md").read_text(encoding="utf-8")
        update = {
            "job_id": "sample-role",
            "expected_version": "1.0.0",
            "change_type": "wording",
            "actor": "tester",
            "reason": "无变化",
            "source": "用户输入",
            "files": {"jd": current},
        }
        path = self.write_payload("noop.json", update)
        _, result = self.run_cli("update", "--input", str(path), expect=2)
        self.assertIn("没有实际变化", result["error"])

    def test_common_personal_identifiers_are_rejected(self) -> None:
        examples = (
            "138" + "1234" + "5678",
            "candidate" + "@" + "example.com",
            "110105" + "19491231" + "002X",
        )
        for sensitive in examples:
            with self.subTest(sensitive=sensitive):
                payload = self.create_payload()
                payload["files"]["persona"] = f"候选人联系方式：{sensitive}"
                path = self.write_payload("sensitive.json", payload)
                _, result = self.run_cli("create", "--input", str(path), expect=2)
                self.assertIn("敏感个人信息", result["error"])

    def test_structured_candidate_identity_fields_are_rejected(self) -> None:
        payload = self.create_payload()
        payload["candidate_name"] = "张某"
        path = self.write_payload("candidate.json", payload)
        _, result = self.run_cli("create", "--input", str(path), expect=2)
        self.assertIn("候选人身份字段", result["error"])

    def test_corrupt_or_missing_job_files_block_updates(self) -> None:
        self.seed_job()
        job_dir = self.root / "references" / "jobs" / "sample-role"
        (job_dir / "persona.md").unlink()
        update = {
            "job_id": "sample-role",
            "expected_version": "1.0.0",
            "change_type": "wording",
            "actor": "tester",
            "reason": "更新",
            "source": "用户确认",
            "files": {"jd": "# 正式 JD\n\n更新\n"},
        }
        path = self.write_payload("update.json", update)
        _, result = self.run_cli("update", "--input", str(path), expect=2)
        self.assertIn("缺失", result["error"])

    def test_archive_is_versioned_and_never_physically_deletes(self) -> None:
        self.seed_job()
        _, preview = self.run_cli("archive", "--job-id", "sample-role", "--reason", "暂停招聘")
        self.assertEqual(preview["version"]["to"], "1.0.1")
        self.assertEqual(preview["diff"]["status"], {"before": "active", "after": "archived"})
        self.run_cli(
            "archive",
            "--job-id",
            "sample-role",
            "--reason",
            "暂停招聘",
            "--apply",
            "--plan-hash",
            preview["plan_hash"],
        )
        job_dir = self.root / "references" / "jobs" / "sample-role"
        self.assertTrue(job_dir.exists())
        self.assertEqual(json.loads((job_dir / "job.json").read_text())["status"], "archived")
        self.assertTrue((job_dir / "history" / "v1.0.0").exists())

    def test_history_lists_snapshots(self) -> None:
        self.seed_job()
        _, preview = self.run_cli("archive", "--job-id", "sample-role", "--reason", "暂停招聘")
        self.run_cli(
            "archive",
            "--job-id",
            "sample-role",
            "--reason",
            "暂停招聘",
            "--apply",
            "--plan-hash",
            preview["plan_hash"],
        )
        _, history = self.run_cli("history", "--job-id", "sample-role")
        self.assertEqual(history["versions"], ["1.0.0"])
        self.assertIn("1.0.0 → 1.0.1", history["changelog"])

    def test_atomic_write_set_restores_originals_after_failure(self) -> None:
        if not SCRIPT.exists():
            self.fail("scripts/job_library.py is missing")
        module = load_module()
        first = self.root / "first.txt"
        second = self.root / "second.txt"
        first.write_text("old-first", encoding="utf-8")
        second.write_text("old-second", encoding="utf-8")
        real_replace = os.replace
        calls = 0

        def fail_second(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected replacement failure")
            return real_replace(source, destination)

        with mock.patch.object(module.os, "replace", side_effect=fail_second):
            with self.assertRaises(OSError):
                module.atomic_write_set({first: b"new-first", second: b"new-second"})

        self.assertEqual(first.read_text(encoding="utf-8"), "old-first")
        self.assertEqual(second.read_text(encoding="utf-8"), "old-second")

    def test_atomic_write_set_rolls_back_when_post_validation_fails(self) -> None:
        module = load_module()
        target = self.root / "target.txt"
        target.write_text("old", encoding="utf-8")

        def reject_state() -> None:
            raise module.LibraryError("post-write validation failed")

        with self.assertRaises(module.LibraryError):
            module.atomic_write_set({target: b"new"}, validate_after=reject_state)
        self.assertEqual(target.read_text(encoding="utf-8"), "old")


if __name__ == "__main__":
    unittest.main()
