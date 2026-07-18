#!/usr/bin/env python3
"""Safe local storage for the manual-only generic HR job profile library."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import sys
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo


SCHEMA_VERSION = "1.0"
INITIAL_VERSION = "1.0.0"
EMPTY_FEEDBACK_MARKER = "未提供（尚无已记录的匿名业务反馈）。"
CONTENT_FILES = {
    "jd": "jd.md",
    "persona": "persona.md",
    "screening-criteria": "screening-criteria.md",
    "business-feedback": "business-feedback.md",
}
REQUIRED_JOB_FILES = (
    "job.json",
    "jd.md",
    "persona.md",
    "screening-criteria.md",
    "business-feedback.md",
    "changelog.md",
)
VERSION_BUMPS = {
    "wording": "patch",
    "correction": "patch",
    "feedback": "patch",
    "metadata": "patch",
    "persona": "minor",
    "screening": "minor",
    "standard": "minor",
    "role-scope": "major",
}
FORBIDDEN_IDENTITY_KEYS = {
    "candidate_name",
    "candidate_full_name",
    "candidate_phone",
    "candidate_email",
    "candidate_id",
    "candidate_id_number",
    "resume_name",
}
PII_PATTERNS = (
    re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])"),
    re.compile(r"(?<!\d)\d{17}[0-9Xx](?!\d)"),
)
DEFAULT_TEMPLATES = {
    "jd.md": """# {{JOB_NAME}}｜正式 JD

## 岗位定位

未提供

## 岗位职责

未提供

## 任职要求

未提供

## 必须技能

未提供

## 优先技能

未提供
""",
    "persona.md": """# {{JOB_NAME}}｜招聘画像

## 核心人才特征

未提供

## 目标行业与公司

未提供

## 典型项目经验

未提供

## 能力重点与风险因素

未提供
""",
    "screening-criteria.md": """# {{JOB_NAME}}｜筛选标准

## 硬性条件

未提供

## 强优先条件

未提供

## 一般加分项

未提供

## 明确排除项

未提供

## 需要进一步确认项

未提供
""",
    "business-feedback.md": """# {{JOB_NAME}}｜业务反馈

未提供（尚无已记录的匿名业务反馈）。
""",
    "changelog.md": "# {{JOB_NAME}}｜变更记录\n",
}


class LibraryError(RuntimeError):
    """Expected validation or contract error."""


def today() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()


def now_iso() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


def normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n").encode("utf-8")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LibraryError(f"缺失文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise LibraryError(f"JSON 文件损坏：{path}（{exc}）") from exc
    if not isinstance(value, dict):
        raise LibraryError(f"JSON 顶层必须是对象：{path}")
    return value


def index_path(root: Path) -> Path:
    return root / "references" / "job-index.json"


def jobs_root(root: Path) -> Path:
    return root / "references" / "jobs"


def job_path(root: Path, job_id: str) -> Path:
    validate_job_id(job_id)
    return jobs_root(root) / job_id


def validate_job_id(job_id: str) -> None:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", job_id or ""):
        raise LibraryError("岗位 ID 必须使用小写字母、数字和单连字符")


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def load_index(root: Path) -> dict[str, Any]:
    index = read_json(index_path(root))
    if index.get("schema_version") != SCHEMA_VERSION:
        raise LibraryError(f"岗位索引 schema_version 必须为 {SCHEMA_VERSION}")
    if not isinstance(index.get("jobs"), list):
        raise LibraryError("岗位索引 jobs 必须是数组")
    return index


def find_job(index: dict[str, Any], job_id: str) -> dict[str, Any]:
    for entry in index["jobs"]:
        if entry.get("id") == job_id:
            return entry
    raise LibraryError(f"岗位不存在：{job_id}")


def check_complete_job(root: Path, entry: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    job_id = entry.get("id")
    if not isinstance(job_id, str):
        raise LibraryError("岗位索引存在无效 ID")
    directory = job_path(root, job_id)
    missing = [filename for filename in REQUIRED_JOB_FILES if not (directory / filename).is_file()]
    if missing:
        raise LibraryError(f"岗位 {job_id} 缺失文件：{', '.join(missing)}")
    metadata = read_json(directory / "job.json")
    if metadata.get("id") != job_id:
        raise LibraryError(f"岗位 {job_id} 的 job.json ID 不一致")
    if metadata.get("current_version") != entry.get("current_version"):
        raise LibraryError(f"岗位 {job_id} 的索引版本与 job.json 不一致")
    if metadata.get("status") != entry.get("status"):
        raise LibraryError(f"岗位 {job_id} 的索引状态与 job.json 不一致")
    return directory, metadata


def scan_forbidden_keys(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if str(key).casefold() in FORBIDDEN_IDENTITY_KEYS:
                found.append(child_path)
            found.extend(scan_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(scan_forbidden_keys(child, f"{path}[{index}]"))
    return found


def ensure_no_sensitive_data(value: Any) -> None:
    forbidden = scan_forbidden_keys(value)
    if forbidden:
        raise LibraryError(f"检测到候选人身份字段，禁止写入：{', '.join(forbidden)}")
    text = json.dumps(value, ensure_ascii=False)
    if any(pattern.search(text) for pattern in PII_PATTERNS):
        raise LibraryError("检测到常见敏感个人信息（手机号、邮箱或身份证号），禁止写入")


def load_payload(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    ensure_no_sensitive_data(payload)
    return payload


def validate_library(root: Path) -> list[str]:
    issues: list[str] = []
    try:
        index = load_index(root)
    except LibraryError as exc:
        return [str(exc)]

    ids: set[str] = set()
    names: set[str] = set()
    for position, entry in enumerate(index["jobs"]):
        if not isinstance(entry, dict):
            issues.append(f"索引第 {position + 1} 项不是对象")
            continue
        job_id = entry.get("id")
        name = entry.get("name")
        try:
            if not isinstance(job_id, str):
                raise LibraryError("岗位 ID 缺失")
            validate_job_id(job_id)
        except LibraryError as exc:
            issues.append(f"索引第 {position + 1} 项：{exc}")
            continue
        if job_id in ids:
            issues.append(f"岗位 ID 重复：{job_id}")
        ids.add(job_id)
        if not isinstance(name, str) or not name.strip():
            issues.append(f"岗位 {job_id} 缺少标准名称")
        else:
            normalized_name = normalize(name)
            if normalized_name in names:
                issues.append(f"岗位标准名称重复：{name}")
            names.add(normalized_name)
        expected_path = f"references/jobs/{job_id}"
        if entry.get("path") != expected_path:
            issues.append(f"岗位 {job_id} 的索引路径应为 {expected_path}")
        if entry.get("status") not in {"active", "archived"}:
            issues.append(f"岗位 {job_id} 状态无效")
        try:
            directory, _ = check_complete_job(root, entry)
            for filename in CONTENT_FILES.values():
                text = (directory / filename).read_text(encoding="utf-8")
                if any(pattern.search(text) for pattern in PII_PATTERNS):
                    issues.append(f"岗位 {job_id}/{filename} 含常见敏感个人信息")
        except (LibraryError, UnicodeDecodeError) as exc:
            issues.append(str(exc))
    return issues


def ensure_safe_to_mutate(root: Path) -> dict[str, Any]:
    issues = validate_library(root)
    if issues:
        raise LibraryError("岗位库校验失败，停止写入：" + "；".join(issues))
    return load_index(root)


def template_text(root: Path, filename: str, job_name: str) -> str:
    asset = root / "assets" / "job-template" / filename
    text = asset.read_text(encoding="utf-8") if asset.is_file() else DEFAULT_TEMPLATES[filename]
    return text.replace("{{JOB_NAME}}", job_name).rstrip() + "\n"


def bump_version(version: str, bump: str) -> str:
    try:
        major, minor, patch = (int(part) for part in version.split("."))
    except (TypeError, ValueError) as exc:
        raise LibraryError(f"无效版本号：{version}") from exc
    if bump == "patch":
        patch += 1
    elif bump == "minor":
        minor += 1
        patch = 0
    elif bump == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        raise LibraryError(f"未知版本递增类型：{bump}")
    return f"{major}.{minor}.{patch}"


def state_digest(root: Path, job_id: str | None = None) -> str:
    digest = hashlib.sha256()
    paths = [index_path(root)]
    if job_id:
        directory = job_path(root, job_id)
        if directory.exists():
            paths.extend(path for path in directory.rglob("*") if path.is_file())
    for path in sorted(paths, key=lambda item: item.as_posix()):
        digest.update(relative(root, path).encode("utf-8"))
        if path.exists():
            digest.update(path.read_bytes())
        else:
            digest.update(b"<missing>")
    return digest.hexdigest()


def plan_hash(operation: str, payload: dict[str, Any], state: str) -> str:
    return hashlib.sha256(canonical_bytes({"operation": operation, "payload": payload, "state": state})).hexdigest()


def unified_text_diff(before: str, after: str, label: str) -> str:
    """Return the exact user-reviewable text change used by an update plan."""
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"{label}:before",
            tofile=f"{label}:after",
        )
    )


def atomic_write_set(
    writes: dict[Path, bytes],
    *,
    validate_after: Callable[[], None] | None = None,
) -> None:
    """Replace a set of files and restore every original if one replacement fails."""
    backups: dict[Path, bytes | None] = {}
    staged: dict[Path, Path] = {}
    for target, content in writes.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        backups[target] = target.read_bytes() if target.exists() else None
        temporary = target.parent / f".{target.name}.{uuid.uuid4().hex}.tmp"
        with temporary.open("wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        staged[target] = temporary
    try:
        for target, temporary in staged.items():
            os.replace(temporary, target)
        if validate_after is not None:
            validate_after()
    except Exception:
        for target, original in backups.items():
            if original is None:
                if target.exists():
                    target.unlink()
            else:
                target.write_bytes(original)
        raise
    finally:
        for temporary in staged.values():
            if temporary.exists():
                temporary.unlink()


def job_index_entry(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": metadata["id"],
        "name": metadata["name"],
        "aliases": metadata.get("aliases", []),
        "family": metadata.get("family", "未提供"),
        "status": metadata["status"],
        "current_version": metadata["current_version"],
        "updated_at": metadata["updated_at"],
        "path": f"references/jobs/{metadata['id']}",
    }


def validate_create_payload(payload: dict[str, Any], index: dict[str, Any]) -> dict[str, Any]:
    job = payload.get("job")
    if not isinstance(job, dict):
        raise LibraryError("create 输入缺少 job 对象")
    job_id = job.get("id")
    name = job.get("name")
    if not isinstance(job_id, str):
        raise LibraryError("create 输入缺少岗位 ID")
    validate_job_id(job_id)
    if not isinstance(name, str) or not name.strip():
        raise LibraryError("create 输入缺少岗位标准名称")
    if any(entry.get("id") == job_id for entry in index["jobs"]):
        raise LibraryError(f"岗位 ID 已存在，不能覆盖：{job_id}")
    normalized_name = normalize(name)
    if any(normalize(str(entry.get("name", ""))) == normalized_name for entry in index["jobs"]):
        raise LibraryError(f"岗位标准名称已存在，不能覆盖：{name}")
    aliases = job.get("aliases", [])
    if not isinstance(aliases, list) or not all(isinstance(alias, str) for alias in aliases):
        raise LibraryError("aliases 必须是字符串数组")
    files = payload.get("files", {})
    if not isinstance(files, dict):
        raise LibraryError("files 必须是对象")
    unknown = set(files) - set(CONTENT_FILES)
    if unknown:
        raise LibraryError("未知岗位文件字段：" + ", ".join(sorted(unknown)))
    if any(not isinstance(value, str) for value in files.values()):
        raise LibraryError("岗位文件内容必须是字符串")
    return job


def create_operation(root: Path, input_file: Path, apply: bool, supplied_hash: str | None) -> dict[str, Any]:
    index = ensure_safe_to_mutate(root)
    payload = load_payload(input_file)
    job = validate_create_payload(payload, index)
    job_id = job["id"]
    name = job["name"].strip()
    created_at = today()
    metadata = {
        "id": job_id,
        "name": name,
        "english_name": job.get("english_name", "未提供"),
        "aliases": job.get("aliases", []),
        "department": job.get("department", "未提供"),
        "family": job.get("family", "未提供"),
        "location": job.get("location", "未提供"),
        "status": "active",
        "current_version": INITIAL_VERSION,
        "created_at": created_at,
        "updated_at": today(),
    }
    directory = job_path(root, job_id)
    files_payload = payload.get("files", {})
    rendered: dict[str, str] = {}
    for key, filename in CONTENT_FILES.items():
        rendered[filename] = files_payload.get(key) or template_text(root, filename, name)
        rendered[filename] = rendered[filename].rstrip() + "\n"
    actor = str(payload.get("actor", "tester"))
    reason = str(payload.get("reason", "首次建立岗位"))
    source = str(payload.get("source", "用户提供资料"))
    changelog = template_text(root, "changelog.md", name)
    changelog += (
        f"\n## {today()} · 创建 {INITIAL_VERSION}\n\n"
        f"- 操作人：{actor}\n- 修改原因：{reason}\n- 信息来源：{source}\n"
        "- 修改字段：首次建立全部岗位文件\n"
    )
    rendered["changelog.md"] = changelog
    new_index = json.loads(json.dumps(index, ensure_ascii=False))
    new_index["updated_at"] = today()
    new_index["jobs"].append(job_index_entry(metadata))
    plan = {
        "input": payload,
        "metadata": metadata,
        "files": rendered,
        "index": new_index,
    }
    state = state_digest(root, job_id)
    expected_hash = plan_hash("create", plan, state)
    files = [relative(root, directory / filename) for filename in REQUIRED_JOB_FILES]
    result = {
        "ok": True,
        "operation": "create",
        "job": {"id": job_id, "name": name},
        "files": files + [relative(root, index_path(root))],
        "version": {"from": None, "to": INITIAL_VERSION},
        "result": "preview",
        "conflicts": [],
        "pending": [
            *[
                f"job.{key}"
                for key in ("english_name", "aliases", "department", "family", "location")
                if key not in job or job.get(key) in (None, "", [], "未提供")
            ],
            *[
                f"files.{key}"
                for key in CONTENT_FILES
                if key not in files_payload or not files_payload.get(key)
            ],
        ],
        "changed": False,
        "applied": False,
        "plan_hash": expected_hash,
        "preview": {"metadata": metadata, "files": rendered},
    }
    if not apply:
        return result
    if supplied_hash != expected_hash:
        raise LibraryError("plan_hash 不匹配或已过期；请重新生成预览并确认")
    writes: dict[Path, bytes] = {directory / "job.json": json_bytes(metadata)}
    writes.update({directory / filename: text.encode("utf-8") for filename, text in rendered.items()})
    writes[index_path(root)] = json_bytes(new_index)
    def validate_after() -> None:
        issues = validate_library(root)
        if issues:
            raise LibraryError("写入后校验失败：" + "；".join(issues))

    atomic_write_set(writes, validate_after=validate_after)
    result.update(result="applied", changed=True, applied=True)
    return result


def validate_feedback(feedback: Any, files: dict[str, str]) -> list[dict[str, Any]]:
    if feedback is None:
        return []
    if not isinstance(feedback, list):
        raise LibraryError("feedback 必须是数组")
    validated: list[dict[str, Any]] = []
    for item in feedback:
        if not isinstance(item, dict):
            raise LibraryError("每条 feedback 必须是对象")
        level = item.get("level")
        if level not in {"L1", "L2", "L3", "L4"}:
            raise LibraryError("feedback.level 必须是 L1、L2、L3 或 L4")
        if not isinstance(item.get("content"), str) or not item["content"].strip():
            raise LibraryError("feedback.content 不能为空")
        promoted = bool(item.get("promote_to_formal", False))
        if promoted and level in {"L1", "L2"}:
            raise LibraryError("L1/L2 业务反馈禁止直接升级为正式标准")
        targets = item.get("promotion_targets", [])
        if promoted:
            if not isinstance(targets, list) or not targets:
                raise LibraryError("升级正式标准时必须填写 promotion_targets")
            invalid_targets = set(targets) - {"persona", "screening-criteria", "jd"}
            if invalid_targets:
                raise LibraryError("无效 promotion_targets：" + ", ".join(sorted(invalid_targets)))
            missing_targets = [target for target in targets if target not in files]
            if missing_targets:
                raise LibraryError("升级正式标准时必须同时提交目标文件内容：" + ", ".join(missing_targets))
        validated.append(item)
    return validated


def feedback_markdown(items: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for item in items:
        promoted = "是" if item.get("promote_to_formal") else "否"
        targets = "、".join(item.get("promotion_targets", [])) or "无"
        blocks.append(
            f"## {item.get('date', today())} · {item.get('id', '未提供')}\n\n"
            f"- 证据等级：{item['level']}\n"
            f"- 场景：{item.get('context', '未提供')}\n"
            f"- 反馈内容：{item['content'].strip()}\n"
            f"- 已进入正式标准：{promoted}\n"
            f"- 升级目标：{targets}\n"
        )
    return "\n".join(blocks)


def remove_empty_feedback_marker(text: str) -> str:
    """Remove only the exact empty-state line before the first feedback append."""
    lines = [line for line in text.splitlines() if line.strip() != EMPTY_FEEDBACK_MARKER]
    return "\n".join(lines).rstrip()


def validate_update_payload(payload: dict[str, Any]) -> tuple[str, str, dict[str, str], list[dict[str, Any]]]:
    job_id = payload.get("job_id")
    expected_version = payload.get("expected_version")
    change_type = payload.get("change_type")
    if not isinstance(job_id, str):
        raise LibraryError("update 输入缺少 job_id")
    validate_job_id(job_id)
    if not isinstance(expected_version, str):
        raise LibraryError("update 输入缺少 expected_version")
    if change_type not in VERSION_BUMPS:
        raise LibraryError("change_type 必须是：" + ", ".join(VERSION_BUMPS))
    files = payload.get("files", {})
    if not isinstance(files, dict):
        raise LibraryError("files 必须是对象")
    unknown = set(files) - set(CONTENT_FILES)
    if unknown:
        raise LibraryError("未知岗位文件字段：" + ", ".join(sorted(unknown)))
    if any(not isinstance(value, str) for value in files.values()):
        raise LibraryError("岗位文件内容必须是字符串")
    feedback = validate_feedback(payload.get("feedback"), files)
    job_updates = payload.get("job_updates", {})
    if not isinstance(job_updates, dict):
        raise LibraryError("job_updates 必须是对象")
    allowed_updates = {"name", "english_name", "aliases", "department", "family", "location"}
    unknown_updates = set(job_updates) - allowed_updates
    if unknown_updates:
        raise LibraryError("不允许直接更新字段：" + ", ".join(sorted(unknown_updates)))
    if not files and not feedback and not job_updates:
        raise LibraryError("update 至少需要 files、feedback 或 job_updates 中的一项")
    return job_id, expected_version, files, feedback


def append_changelog(
    current: str,
    *,
    old_version: str,
    new_version: str,
    payload: dict[str, Any],
    before_after: dict[str, tuple[str, str]],
) -> str:
    lines = [
        current.rstrip(),
        "",
        f"## {today()} · {old_version} → {new_version}",
        "",
        f"- 操作人：{payload.get('actor', 'tester')}",
        f"- 更新类型：{payload.get('change_type')}",
        f"- 修改原因：{payload.get('reason', '未提供')}",
        f"- 信息来源：{payload.get('source', '未提供')}",
        f"- 修改字段：{'、'.join(before_after) or '岗位元数据'}",
        "",
    ]
    for field, (before, after) in before_after.items():
        lines.extend(
            [
                f"### {field}",
                "",
                "#### 修改前",
                "",
                before.rstrip() or "未提供",
                "",
                "#### 修改后",
                "",
                after.rstrip() or "未提供",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def update_operation(root: Path, input_file: Path, apply: bool, supplied_hash: str | None) -> dict[str, Any]:
    index = ensure_safe_to_mutate(root)
    payload = load_payload(input_file)
    job_id, expected_version, files, feedback = validate_update_payload(payload)
    entry = find_job(index, job_id)
    directory, metadata = check_complete_job(root, entry)
    old_version = metadata["current_version"]
    if expected_version != old_version:
        raise LibraryError(f"expected_version 已过期：当前为 {old_version}")
    new_version = bump_version(old_version, VERSION_BUMPS[payload["change_type"]])
    snapshot = directory / "history" / f"v{old_version}"
    if snapshot.exists():
        raise LibraryError(f"历史快照已存在，拒绝覆盖：v{old_version}")

    current_text = {
        key: (directory / filename).read_text(encoding="utf-8")
        for key, filename in CONTENT_FILES.items()
    }
    new_text = dict(current_text)
    before_after: dict[str, tuple[str, str]] = {}
    for key, value in files.items():
        normalized_value = value.rstrip() + "\n"
        if normalized_value != current_text[key]:
            new_text[key] = normalized_value
            before_after[key] = (current_text[key], normalized_value)
    if feedback:
        feedback_base = remove_empty_feedback_marker(new_text["business-feedback"])
        appended = feedback_base + "\n\n" + feedback_markdown(feedback)
        appended = appended.rstrip() + "\n"
        new_text["business-feedback"] = appended
        before_after["business-feedback"] = (current_text["business-feedback"], appended)

    job_updates = payload.get("job_updates", {})
    effective_updates = {
        key: value for key, value in job_updates.items() if metadata.get(key) != value
    }
    new_metadata = json.loads(json.dumps(metadata, ensure_ascii=False))
    new_metadata.update(effective_updates)
    new_metadata["current_version"] = new_version
    new_metadata["updated_at"] = today()
    if "name" in effective_updates:
        candidate = normalize(str(effective_updates["name"]))
        if any(
            other.get("id") != job_id and normalize(str(other.get("name", ""))) == candidate
            for other in index["jobs"]
        ):
            raise LibraryError(f"岗位标准名称已存在：{effective_updates['name']}")
    if "aliases" in effective_updates and (
        not isinstance(effective_updates["aliases"], list)
        or not all(isinstance(alias, str) for alias in effective_updates["aliases"])
    ):
        raise LibraryError("job_updates.aliases 必须是字符串数组")
    if not before_after and not effective_updates:
        raise LibraryError("更新没有实际变化，未生成新版本")

    old_changelog = (directory / "changelog.md").read_text(encoding="utf-8")
    new_changelog = append_changelog(
        old_changelog,
        old_version=old_version,
        new_version=new_version,
        payload=payload,
        before_after=before_after,
    )
    new_index = json.loads(json.dumps(index, ensure_ascii=False))
    for position, candidate in enumerate(new_index["jobs"]):
        if candidate.get("id") == job_id:
            new_index["jobs"][position] = job_index_entry(new_metadata)
            break
    new_index["updated_at"] = today()

    plan = {
        "input": payload,
        "metadata": new_metadata,
        "files": new_text,
        "changelog": new_changelog,
        "index": new_index,
    }
    state = state_digest(root, job_id)
    expected_hash = plan_hash("update", plan, state)
    changed_files = [CONTENT_FILES[key] for key in before_after]
    if effective_updates:
        changed_files.append("job.json")
    diff = {
        key: unified_text_diff(before, after, key)
        for key, (before, after) in before_after.items()
    }
    if effective_updates:
        diff["job"] = {
            key: {"before": metadata.get(key, "未提供"), "after": value}
            for key, value in effective_updates.items()
        }
    result = {
        "ok": True,
        "operation": "update",
        "job": {"id": job_id, "name": new_metadata["name"]},
        "files": sorted(set(changed_files + ["job.json", "changelog.md", "job-index.json"])),
        "version": {"from": old_version, "to": new_version},
        "result": "preview",
        "conflicts": [],
        "pending": [],
        "changed": False,
        "applied": False,
        "plan_hash": expected_hash,
        "diff": diff,
    }
    if not apply:
        return result
    if supplied_hash != expected_hash:
        raise LibraryError("plan_hash 不匹配或已过期；请重新生成预览并确认")

    writes: dict[Path, bytes] = {}
    for filename in REQUIRED_JOB_FILES:
        writes[snapshot / filename] = (directory / filename).read_bytes()
    writes[directory / "job.json"] = json_bytes(new_metadata)
    for key, filename in CONTENT_FILES.items():
        writes[directory / filename] = new_text[key].encode("utf-8")
    writes[directory / "changelog.md"] = new_changelog.encode("utf-8")
    writes[index_path(root)] = json_bytes(new_index)
    def validate_after() -> None:
        issues = validate_library(root)
        if issues:
            raise LibraryError("写入后校验失败：" + "；".join(issues))

    atomic_write_set(writes, validate_after=validate_after)
    result.update(result="applied", changed=True, applied=True)
    return result


def archive_operation(
    root: Path,
    job_id: str,
    reason: str,
    apply: bool,
    supplied_hash: str | None,
) -> dict[str, Any]:
    index = ensure_safe_to_mutate(root)
    entry = find_job(index, job_id)
    directory, metadata = check_complete_job(root, entry)
    if metadata["status"] == "archived":
        raise LibraryError(f"岗位已经归档：{job_id}")
    old_version = metadata["current_version"]
    new_version = bump_version(old_version, "patch")
    snapshot = directory / "history" / f"v{old_version}"
    if snapshot.exists():
        raise LibraryError(f"历史快照已存在，拒绝覆盖：v{old_version}")
    payload = {"job_id": job_id, "reason": reason}
    new_metadata = json.loads(json.dumps(metadata, ensure_ascii=False))
    new_metadata.update(status="archived", current_version=new_version, updated_at=today())
    old_changelog = (directory / "changelog.md").read_text(encoding="utf-8")
    changelog_payload = {
        "actor": "tester",
        "change_type": "metadata",
        "reason": reason,
        "source": "用户确认归档",
    }
    new_changelog = append_changelog(
        old_changelog,
        old_version=old_version,
        new_version=new_version,
        payload=changelog_payload,
        before_after={"status": ("active", "archived")},
    )
    new_index = json.loads(json.dumps(index, ensure_ascii=False))
    for position, candidate in enumerate(new_index["jobs"]):
        if candidate.get("id") == job_id:
            new_index["jobs"][position] = job_index_entry(new_metadata)
            break
    new_index["updated_at"] = today()
    plan = {
        "input": payload,
        "metadata": new_metadata,
        "changelog": new_changelog,
        "index": new_index,
    }
    state = state_digest(root, job_id)
    expected_hash = plan_hash("archive", plan, state)
    result = {
        "ok": True,
        "operation": "archive",
        "job": {"id": job_id, "name": metadata["name"]},
        "files": ["job.json", "changelog.md", "job-index.json", f"history/v{old_version}/"],
        "version": {"from": old_version, "to": new_version},
        "result": "preview",
        "conflicts": [],
        "pending": [],
        "changed": False,
        "applied": False,
        "plan_hash": expected_hash,
        "diff": {"status": {"before": "active", "after": "archived"}},
    }
    if not apply:
        return result
    if supplied_hash != expected_hash:
        raise LibraryError("plan_hash 不匹配或已过期；请重新生成预览并确认")
    writes: dict[Path, bytes] = {}
    for filename in REQUIRED_JOB_FILES:
        writes[snapshot / filename] = (directory / filename).read_bytes()
    writes[directory / "job.json"] = json_bytes(new_metadata)
    writes[directory / "changelog.md"] = new_changelog.encode("utf-8")
    writes[index_path(root)] = json_bytes(new_index)
    def validate_after() -> None:
        issues = validate_library(root)
        if issues:
            raise LibraryError("写入后校验失败：" + "；".join(issues))

    atomic_write_set(writes, validate_after=validate_after)
    result.update(result="applied", changed=True, applied=True)
    return result


def validate_command(root: Path) -> dict[str, Any]:
    issues = validate_library(root)
    count = 0
    try:
        count = len(load_index(root)["jobs"])
    except LibraryError:
        pass
    return {
        "ok": not issues,
        "operation": "validate",
        "job_count": count,
        "issues": issues,
        "changed": False,
        "applied": False,
    }


def list_command(root: Path, status: str) -> dict[str, Any]:
    index = load_index(root)
    selected = [entry for entry in index["jobs"] if status == "all" or entry.get("status") == status]
    return {
        "ok": True,
        "operation": "list",
        "status_filter": status,
        "jobs": selected,
        "changed": False,
        "applied": False,
    }


def resolve_command(root: Path, query: str) -> dict[str, Any]:
    index = load_index(root)
    normalized_query = normalize(query)
    exact: list[dict[str, Any]] = []
    for entry in index["jobs"]:
        values = [entry.get("id", ""), entry.get("name", ""), *entry.get("aliases", [])]
        if any(normalize(str(value)) == normalized_query for value in values):
            exact.append(entry)
    if len(exact) == 1:
        status = "resolved"
        matches = exact
    elif len(exact) > 1:
        status = "ambiguous"
        matches = exact
    else:
        scored: list[tuple[float, dict[str, Any]]] = []
        for entry in index["jobs"]:
            values = [entry.get("id", ""), entry.get("name", ""), *entry.get("aliases", [])]
            score = max(
                (difflib.SequenceMatcher(None, normalized_query, normalize(str(value))).ratio() for value in values),
                default=0.0,
            )
            if score >= 0.45:
                scored.append((score, entry))
        scored.sort(key=lambda pair: (-pair[0], pair[1].get("id", "")))
        matches = [{**entry, "match_score": round(score, 3)} for score, entry in scored[:5]]
        status = "suggested" if matches else "not-found"
    return {
        "ok": True,
        "operation": "resolve",
        "query": query,
        "status": status,
        "matches": matches,
        "auto_selected": status == "resolved",
        "changed": False,
        "applied": False,
    }


def history_command(root: Path, job_id: str, version: str | None) -> dict[str, Any]:
    index = load_index(root)
    entry = find_job(index, job_id)
    directory, _ = check_complete_job(root, entry)
    history_root = directory / "history"
    versions = sorted(
        (path.name.removeprefix("v") for path in history_root.iterdir() if path.is_dir()),
        key=lambda value: tuple(int(part) for part in value.split(".")),
    ) if history_root.is_dir() else []
    result: dict[str, Any] = {
        "ok": True,
        "operation": "history",
        "job": {"id": job_id, "name": entry["name"]},
        "versions": versions,
        "changelog": (directory / "changelog.md").read_text(encoding="utf-8"),
        "changed": False,
        "applied": False,
    }
    if version:
        snapshot = history_root / f"v{version}"
        if not snapshot.is_dir():
            raise LibraryError(f"历史版本不存在：{version}")
        result["snapshot"] = {
            filename: (snapshot / filename).read_text(encoding="utf-8")
            for filename in REQUIRED_JOB_FILES
        }
    return result


def build_parser() -> argparse.ArgumentParser:
    default_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="HR 招聘岗位 JD 与画像库安全存储工具")
    parser.add_argument("--root", type=Path, default=default_root, help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="校验索引和岗位文件一致性")
    validate_parser.add_argument("--json", action="store_true", help="输出 JSON")

    list_parser = subparsers.add_parser("list", help="列出岗位")
    list_parser.add_argument("--status", choices=("active", "archived", "all"), default="active")
    list_parser.add_argument("--json", action="store_true", help="输出 JSON")

    resolve_parser = subparsers.add_parser("resolve", help="匹配岗位 ID、名称或别名")
    resolve_parser.add_argument("--query", required=True)
    resolve_parser.add_argument("--json", action="store_true", help="输出 JSON")

    for command in ("create", "update"):
        command_parser = subparsers.add_parser(command, help=f"预览或应用岗位{command}")
        command_parser.add_argument("--input", type=Path, required=True)
        command_parser.add_argument("--apply", action="store_true")
        command_parser.add_argument("--plan-hash")

    archive_parser = subparsers.add_parser("archive", help="预览或应用可追溯归档")
    archive_parser.add_argument("--job-id", required=True)
    archive_parser.add_argument("--reason", required=True)
    archive_parser.add_argument("--apply", action="store_true")
    archive_parser.add_argument("--plan-hash")

    history_parser = subparsers.add_parser("history", help="查看岗位历史")
    history_parser.add_argument("--job-id", required=True)
    history_parser.add_argument("--version")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    if args.command == "validate":
        return validate_command(root)
    if args.command == "list":
        return list_command(root, args.status)
    if args.command == "resolve":
        return resolve_command(root, args.query)
    if args.command == "create":
        return create_operation(root, args.input.resolve(), args.apply, args.plan_hash)
    if args.command == "update":
        return update_operation(root, args.input.resolve(), args.apply, args.plan_hash)
    if args.command == "archive":
        return archive_operation(root, args.job_id, args.reason, args.apply, args.plan_hash)
    if args.command == "history":
        return history_command(root, args.job_id, args.version)
    raise LibraryError(f"未知命令：{args.command}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = run(args)
        exit_code = 0 if result.get("ok") else 2
    except (LibraryError, OSError, UnicodeError) as exc:
        result = {
            "ok": False,
            "operation": getattr(args, "command", "unknown"),
            "error": str(exc),
            "changed": False,
            "applied": False,
        }
        exit_code = 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
