#!/usr/bin/env python3
"""Read-only structural audit for the Obsidian Memory onboarding schema."""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path


INVENTORY_COUNTERS = (
    "PROJECT_MD_FILES",
    "WIKI_CANDIDATES",
    "OBSIDIAN_VAULTS",
    "SENSITIVE_CANDIDATES",
)
STRICT_COUNTERS = (
    "MISSING_REQUIRED_OBJECTS",
    "NAMING_VIOLATIONS",
    "NUMBERING_VIOLATIONS",
    "FRONTMATTER_VIOLATIONS",
    "EXTRA_INDEX_FILES",
    "MISSING_FROM_INDEX",
    "STALE_INDEX_ENTRIES",
    "INDEX_FORMAT_VIOLATIONS",
    "INDEX_ORDER_VIOLATIONS",
    "MISSING_CURRENT_LOG",
)
CODE_RE = re.compile(r"^[A-Z][A-Z0-9]{1,7}$")
KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(?:\s*(.*))?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LOG_NAME_RE = re.compile(
    r"^(?P<number>\d{4})_LOG-(?P<code>[A-Z][A-Z0-9]{1,7})_"
    r"(?P<month>\d{4}-\d{2})\.md$"
)
NUMBERED_NAME_RE = re.compile(
    r"^(?P<number>\d{4})_(?P<type>[A-Z][A-Z0-9]*)-"
    r"(?P<code>[A-Z][A-Z0-9]{1,7})-(?P<slug>.+)\.md$"
)
FILE_INDEX_RE = re.compile(
    r"^- \[\[([^\]|]+)\|([^\]]+)\]\] — Назначение: (.+?) Состав: (.+)$"
)
FOLDER_INDEX_RE = re.compile(
    r"^- `([^`]+/)` — (.+?)\. Назначение: (.+?) Состав: (.+)$"
)
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?im)^\s*(?:api[_-]?key|token|password|secret)\s*[:=]\s*\S+"
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}
SENSITIVE_TEXT_SUFFIXES = {
    ".cfg",
    ".conf",
    ".env",
    ".ini",
    ".json",
    ".md",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def normalize_unicode(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def normalize_rel(path: Path, root: Path, *, directory: bool = False) -> str:
    relative = normalize_unicode(path.relative_to(root).as_posix())
    return f"{relative}/" if directory else relative


def safe_display(value: str) -> str:
    """Escape control characters before a value reaches a terminal or log."""
    return "".join(
        f"\\x{ord(char):02x}" if ord(char) < 32 or ord(char) == 127 else char
        for char in normalize_unicode(value)
    )


def resolve_inside(candidate: Path, boundary: Path, message: str) -> Path:
    resolved = candidate.resolve()
    try:
        resolved.relative_to(boundary.resolve())
    except ValueError as exc:
        raise ValueError(message) from exc
    return resolved


def iter_project_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*"):
        resolve_inside(path, root, "unsafe path outside project")
        paths.append(path)
    return paths


def sort_key(value: str) -> str:
    return normalize_unicode(value).casefold()


def path_is_ignored(path: Path, root: Path, *, include_obsidian: bool = False) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return True
    ignored = IGNORED_DIRS | (set() if include_obsidian else {".obsidian"})
    return any(part in ignored for part in parts)


def iter_project_files(root: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in iter_project_paths(root)
            if path.is_file() and not path_is_ignored(path, root)
        ),
        key=lambda path: sort_key(normalize_rel(path, root)),
    )


def find_sensitive_candidates(root: Path) -> list[str]:
    findings: set[str] = set()
    for path in iter_project_files(root):
        relative = normalize_rel(path, root)
        lowered = path.name.casefold()
        if (
            lowered == ".env"
            or lowered.startswith("id_rsa")
            or lowered.startswith("credentials")
            or lowered.startswith("secrets")
            or path.suffix.casefold() in {".key", ".pem", ".p12", ".pfx"}
        ):
            findings.add(f"{safe_display(relative)} -> SENSITIVE_FILENAME")
        if path.suffix.casefold() not in SENSITIVE_TEXT_SUFFIXES:
            continue
        try:
            if path.stat().st_size > 1_048_576:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if PRIVATE_KEY_RE.search(text):
            findings.add(f"{safe_display(relative)} -> PRIVATE_KEY_MATERIAL")
        if SECRET_ASSIGNMENT_RE.search(text):
            findings.add(f"{safe_display(relative)} -> SECRET_ASSIGNMENT")
        if EMAIL_RE.search(text):
            findings.add(f"{safe_display(relative)} -> EMAIL_ADDRESS")
    return sorted(findings, key=sort_key)


def inventory(root: Path) -> dict[str, int | list[str]]:
    project_paths = iter_project_paths(root)
    markdown_files = [
        path for path in iter_project_files(root) if path.suffix.casefold() == ".md"
    ]
    wiki_candidates = sorted(
        {
            normalize_rel(path, root, directory=True)
            for path in project_paths
            if path.is_dir()
            and path.name.startswith("wiki_")
            and not path_is_ignored(path, root)
        },
        key=sort_key,
    )
    obsidian_vaults = sorted(
        {
            normalize_rel(path.parent, root, directory=True)
            for path in project_paths
            if path.name == ".obsidian"
            and path.is_dir()
            and not path_is_ignored(path.parent, root, include_obsidian=True)
        },
        key=sort_key,
    )
    return {
        "PROJECT_MD_FILES": len(markdown_files),
        "WIKI_CANDIDATES": wiki_candidates,
        "OBSIDIAN_VAULTS": obsidian_vaults,
        "SENSITIVE_CANDIDATES": find_sensitive_candidates(root),
    }


def is_temporary_file(path: Path) -> bool:
    name = path.name
    return (
        name == ".DS_Store"
        or name.startswith(".~")
        or name.endswith("~")
        or path.suffix.casefold() in {".bak", ".swp", ".tmp"}
    )


def excluded_from_index(path: Path, wiki_root: Path) -> bool:
    relative = path.relative_to(wiki_root)
    parts = relative.parts
    if not parts:
        return False
    if parts[0] == ".obsidian":
        return True
    if parts[0] == "inbox" and len(parts) > 1:
        return True
    if any(part in IGNORED_DIRS for part in parts):
        return True
    return path.is_file() and is_temporary_file(path)


def permanent_objects(wiki_root: Path) -> tuple[set[str], list[Path]]:
    directories: set[str] = set()
    markdown_files: list[Path] = []
    for path in iter_project_paths(wiki_root):
        if excluded_from_index(path, wiki_root):
            continue
        if path.is_dir():
            directories.add(normalize_rel(path, wiki_root, directory=True))
        elif path.is_file() and path.suffix.casefold() == ".md":
            markdown_files.append(path)
    markdown_files.sort(key=lambda path: sort_key(normalize_rel(path, wiki_root)))
    return directories, markdown_files


def clean_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1].strip()
    return value


def yaml_value_is_present(value: str) -> bool:
    return clean_scalar(value).casefold() not in {"", "[]", "{}", "null", "~"}


def frontmatter_violations(
    path: Path,
    relative: str,
    expected: dict[str, str | None],
) -> list[str]:
    display_relative = safe_display(relative)
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return [f"{display_relative} -> unreadable"]
    if not lines or lines[0] != "---":
        return [f"{display_relative} -> missing frontmatter"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return [f"{display_relative} -> unterminated frontmatter"]

    values: dict[str, str] = {}
    duplicates: list[str] = []
    list_values: dict[str, list[str]] = {}
    current_key: str | None = None
    for line in lines[1:end]:
        match = KEY_RE.match(line)
        if match:
            key, raw_value = match.groups()
            if key in values:
                duplicates.append(key)
            else:
                values[key] = (raw_value or "").strip()
            current_key = key
            continue
        stripped = line.strip()
        if current_key and stripped.startswith("-"):
            list_values.setdefault(current_key, []).append(stripped[1:].strip())

    findings = [
        f"{display_relative} -> duplicate key: {key}" for key in duplicates
    ]
    for key in ("title", "created", "updated", "status", "tags"):
        if key not in values:
            findings.append(f"{display_relative} -> missing key: {key}")
            continue
        if key == "tags":
            if not yaml_value_is_present(values[key]) and not any(
                yaml_value_is_present(item) for item in list_values.get(key, [])
            ):
                findings.append(f"{display_relative} -> empty key: tags")
        elif not yaml_value_is_present(values[key]):
            findings.append(f"{display_relative} -> empty key: {key}")
    for key in ("created", "updated"):
        if key in values:
            value = clean_scalar(values[key])
            if not yaml_value_is_present(value):
                continue
            if not DATE_RE.fullmatch(value):
                findings.append(f"{display_relative} -> invalid date: {key}")
            else:
                try:
                    date.fromisoformat(value)
                except ValueError:
                    findings.append(f"{display_relative} -> invalid date: {key}")
    for key, wanted in expected.items():
        if key not in values:
            findings.append(f"{display_relative} -> missing key: {key}")
        elif not yaml_value_is_present(values[key]):
            findings.append(f"{display_relative} -> empty key: {key}")
        elif wanted is not None and clean_scalar(values[key]) != wanted:
            findings.append(
                f"{display_relative} -> invalid {key}: expected {safe_display(wanted)}"
            )
    return findings


def valid_slug(value: str) -> bool:
    value = normalize_unicode(value)
    if not value or value.startswith("-") or value.endswith("-") or "--" in value:
        return False
    for char in value:
        if char == "-" or char.isdigit():
            continue
        if not char.isalpha() or char != char.lower():
            return False
    return True


def classify_numbered_file(
    path: Path,
    relative: str,
    code: str,
) -> tuple[str, int, dict[str, str | None]] | None:
    normalized_name = normalize_unicode(path.name)
    log_match = LOG_NAME_RE.fullmatch(normalized_name)
    if log_match:
        marker = "LOG"
        if log_match.group("code") != code or path.parent.name != "logs":
            return None
        number = int(log_match.group("number"))
        return marker, number, {
            "code": f"LOG-{code}-{number:04d}",
            "type": None,
        }
    match = NUMBERED_NAME_RE.fullmatch(normalized_name)
    if not match or not valid_slug(match.group("slug")):
        return None
    marker = match.group("type")
    if match.group("code") != code:
        return None
    expected_parent = {"RUL": "rules", "INC": "incidents"}.get(marker)
    relative_parent = Path(relative).parent.as_posix()
    if expected_parent and path.parent.name != expected_parent:
        return None
    if not expected_parent and relative_parent in {".", "rules", "incidents", "logs"}:
        return None
    number = int(match.group("number"))
    return marker, number, {
        "code": f"{marker}-{code}-{number:04d}",
        "type": None,
    }


def parse_index(index_path: Path, relative: str) -> tuple[dict[str, int], list[str], list[str]]:
    display_relative = safe_display(relative)
    try:
        lines = index_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}, [f"{display_relative} -> unreadable"], []
    section_count = lines.count("## Состав базы")
    if section_count > 1:
        duplicate_finding = (
            f"{display_relative} -> duplicate section: ## Состав базы"
        )
    else:
        duplicate_finding = None
    try:
        start = lines.index("## Состав базы") + 1
    except ValueError:
        return {}, [f"{display_relative} -> missing section: ## Состав базы"], []
    section: list[tuple[int, str]] = []
    for line_number, line in enumerate(lines[start:], start=start + 1):
        if line.startswith("## "):
            break
        if line.startswith("- "):
            section.append((line_number, line))

    entries: dict[str, int] = {}
    order: list[str] = []
    format_findings: list[str] = [duplicate_finding] if duplicate_finding else []
    for line_number, line in section:
        file_match = FILE_INDEX_RE.fullmatch(line)
        folder_match = FOLDER_INDEX_RE.fullmatch(line)
        if file_match:
            raw_path, title, purpose, contents = file_match.groups()
        elif folder_match:
            raw_path, title, purpose, contents = folder_match.groups()
        else:
            format_findings.append(
                f"{display_relative} -> UNRECOGNIZED_ENTRY_LINE_{line_number}"
            )
            continue
        target = normalize_unicode(raw_path.replace("\\", "/").lstrip("/"))
        if not all(value.strip().strip(".") for value in (title, purpose, contents)):
            format_findings.append(
                f"{display_relative} -> INVALID_ENTRY_LINE_{line_number}"
            )
            continue
        if target in entries:
            format_findings.append(
                f"{display_relative} -> DUPLICATE_ENTRY_LINE_{line_number}"
            )
            continue
        entries[target] = line_number
        order.append(target)
    return entries, sorted(set(format_findings), key=sort_key), order


def validate_structure(
    project_root: Path,
    wiki_root: Path,
    code: str,
    current_month: str,
) -> dict[str, list[str]]:
    findings = {name: [] for name in STRICT_COUNTERS}
    required_paths = (
        (project_root / "AGENTS.md", "file"),
        (wiki_root / f"decisions_{code}.md", "file"),
        (wiki_root / "entities", "directory"),
        (wiki_root / "inbox", "directory"),
        (wiki_root / "incidents", "directory"),
        (wiki_root / f"index_{code}.md", "file"),
        (wiki_root / "logs", "directory"),
        (wiki_root / "rules", "directory"),
        (
            wiki_root / "rules" / f"0001_RUL-{code}-database-maintenance.md",
            "file",
        ),
        (wiki_root / "rules" / f"0002_RUL-{code}-link-workflow.md", "file"),
        (wiki_root / f"todo_{code}.md", "file"),
    )
    for path, expected_type in required_paths:
        boundary = project_root if path == project_root / "AGENTS.md" else wiki_root
        if path.is_symlink():
            resolve_inside(path, boundary, "unsafe path outside project")
        type_matches = path.is_file() if expected_type == "file" else path.is_dir()
        if not type_matches:
            root = project_root if path == project_root / "AGENTS.md" else wiki_root
            findings["MISSING_REQUIRED_OBJECTS"].append(
                safe_display(
                    normalize_rel(path, root, directory=expected_type == "directory")
                )
            )

    directories, markdown_files = permanent_objects(wiki_root)
    expected_singletons = {
        f"decisions_{code}.md",
        f"index_{code}.md",
        f"todo_{code}.md",
    }
    numbers: dict[str, list[int]] = {}
    expected_metadata: dict[str, dict[str, str | None]] = {}
    for path in markdown_files:
        relative = normalize_rel(path, wiki_root)
        if path.name.casefold().startswith("index") and relative != f"index_{code}.md":
            findings["EXTRA_INDEX_FILES"].append(safe_display(relative))
        if relative in expected_singletons:
            expected_metadata[relative] = {}
            continue
        classified = classify_numbered_file(path, relative, code)
        if classified is None:
            findings["NAMING_VIOLATIONS"].append(safe_display(relative))
            expected_metadata[relative] = {}
            continue
        marker, number, metadata = classified
        numbers.setdefault(marker, []).append(number)
        expected_metadata[relative] = metadata

    for marker, marker_numbers in sorted(numbers.items()):
        expected_number = 1
        for actual_number in sorted(marker_numbers):
            if actual_number != expected_number:
                findings["NUMBERING_VIOLATIONS"].append(
                    f"{marker} -> expected {expected_number:04d}, found {actual_number:04d}"
                )
                expected_number = actual_number
            expected_number += 1

    for path in markdown_files:
        relative = normalize_rel(path, wiki_root)
        findings["FRONTMATTER_VIOLATIONS"].extend(
            frontmatter_violations(path, relative, expected_metadata.get(relative, {}))
        )

    current_logs = [
        path
        for path in markdown_files
        if path.parent.name == "logs"
        and (match := LOG_NAME_RE.fullmatch(normalize_unicode(path.name)))
        and match.group("code") == code
        and match.group("month") == current_month
    ]
    if not current_logs:
        findings["MISSING_CURRENT_LOG"].append(current_month)

    expected_index_objects = directories | {
        normalize_rel(path, wiki_root) for path in markdown_files
    }
    index_path = wiki_root / f"index_{code}.md"
    if index_path.is_file():
        entries, format_findings, order = parse_index(index_path, f"index_{code}.md")
        findings["INDEX_FORMAT_VIOLATIONS"].extend(format_findings)
        findings["MISSING_FROM_INDEX"].extend(
            sorted(
                (safe_display(value) for value in expected_index_objects - set(entries)),
                key=sort_key,
            )
        )
        findings["STALE_INDEX_ENTRIES"].extend(
            sorted(
                (
                    f"{safe_display(f'index_{code}.md')} -> "
                    f"STALE_INDEX_ENTRY_LINE_{entries[target]}"
                    for target in set(entries) - expected_index_objects
                ),
                key=sort_key,
            )
        )
        if order != sorted(order, key=sort_key):
            findings["INDEX_ORDER_VIOLATIONS"].append("## Состав базы")
    else:
        findings["MISSING_FROM_INDEX"].extend(
            sorted(
                (safe_display(value) for value in expected_index_objects),
                key=sort_key,
            )
        )

    return {
        name: sorted(set(values), key=sort_key)
        for name, values in findings.items()
    }


def audit(
    project_root: Path,
    *,
    wiki_root: Path | None = None,
    code: str | None = None,
    current_month: str | None = None,
) -> dict[str, int | list[str]]:
    project_root = project_root.resolve()
    if not project_root.is_dir():
        raise ValueError("project root is not a directory")
    if (wiki_root is None) != (code is None):
        raise ValueError("--wiki-root and --code must be provided together")
    if code is not None and not CODE_RE.fullmatch(code):
        raise ValueError("invalid project code")

    result = inventory(project_root)
    result.update({name: [] for name in STRICT_COUNTERS})
    if wiki_root is None or code is None:
        return result

    wiki_root = wiki_root.resolve()
    if not wiki_root.is_dir():
        raise ValueError("wiki root is not a directory")
    try:
        wiki_root.relative_to(project_root)
    except ValueError as exc:
        raise ValueError("wiki root must be inside the project root") from exc
    month = current_month or date.today().strftime("%Y-%m")
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise ValueError(f"invalid current month: {month}")
    result.update(validate_structure(project_root, wiki_root, code, month))
    return result


def emit_section(name: str, values: list[str]) -> int:
    print(f"{name}={len(values)}")
    for value in values:
        print(safe_display(value))
    return len(values)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Audit an Obsidian Memory onboarding project without changing it."
    )
    parser.add_argument("project_root", help="Project root containing AGENTS.md.")
    parser.add_argument("--wiki-root", help="Onboarding wiki root inside the project.")
    parser.add_argument("--code", help="Confirmed project code, for example HOME.")
    parser.add_argument(
        "--strict-exit",
        action="store_true",
        help="Exit with code 1 when structural validation findings exist.",
    )
    args = parser.parse_args(argv)

    if bool(args.wiki_root) != bool(args.code):
        print(
            "ERROR: --wiki-root and --code must be provided together",
            file=sys.stderr,
        )
        return 2
    project_root = Path(args.project_root)
    wiki_root: Path | None = None
    if args.wiki_root:
        candidate = Path(args.wiki_root)
        wiki_root = candidate if candidate.is_absolute() else project_root / candidate
    try:
        result = audit(project_root, wiki_root=wiki_root, code=args.code)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"PROJECT_MD_FILES={result['PROJECT_MD_FILES']}")
    for name in INVENTORY_COUNTERS[1:]:
        emit_section(name, result[name])
    strict_count = 0
    for name in STRICT_COUNTERS:
        strict_count += emit_section(name, result[name])
    if args.strict_exit and strict_count:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
