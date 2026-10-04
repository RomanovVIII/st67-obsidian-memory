#!/usr/bin/env python3
"""Cross-platform Markdown/Obsidian link audit for project memory roots."""

from __future__ import annotations

import argparse
import os
import fnmatch
import unicodedata
import sys
sys.dont_write_bytecode = True
from naming import audit_names, key as naming_key, validate_profile
import concurrent.futures
import json
import posixpath
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote


WIKI_EMBED_RE = re.compile(r"!\[\[([^\]]+)\]\]")
WIKI_LINK_RE = re.compile(r"(?<!!)\[\[([^\]]+)\]\]")
MD_ATTACHMENT_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
MD_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
TBD_RE = re.compile(r"TBD_[A-Za-zА-Яа-я0-9_.-]+")
LIFECYCLE_RE = re.compile(r"\b([A-Z]{2,5})(?:_[A-Z][A-Z0-9]{1,15})?-\d{4,}(?!\d)")
URL_RE = re.compile(r"https?://[^\s<>)\"'`]+")
FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
QUOTE_PREFIX_RE = re.compile(r"^ {0,3}> ?")
LIST_PREFIX_RE = re.compile(r"^ {0,3}(?:[-+*]|\d{1,9}[.)]) {1,4}")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
TABLE_SEPARATOR_CELL_RE = re.compile(r"^:?-{2,}:?$")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
DEFAULT_CONFIG_NAME = "obsidian-memory.config.json"
SUPPORTED_SCHEMA_VERSIONS = {1, 2, 3}
V2_CONFIG_KEYS = {
    "schema_version",
    "base_id",
    "scope",
    "index_path",
    "required_paths",
    "excluded_paths",
    "known_top_level_folders",
    "rules_roots",
    "lifecycle_codes",
    "legacy_markers",
    "historical_source_patterns",
    "disallowed_lifecycle_codes",
    "forbidden_path_patterns",
    "index_section_rules",
    "url",
}
URL_KEYS = {"timeout_seconds", "workers", "classes"}
URL_CLASS_KEYS = {"name", "url_patterns", "source_patterns", "check", "strict"}


def strip_inline_code(line: str) -> str:
    output: list[str] = []
    cursor = 0
    while cursor < len(line):
        if line[cursor] != "`":
            output.append(line[cursor])
            cursor += 1
            continue
        run_end = cursor
        while run_end < len(line) and line[run_end] == "`":
            run_end += 1
        delimiter = line[cursor:run_end]
        search_from = run_end
        closing = -1
        while True:
            found = line.find(delimiter, search_from)
            if found < 0:
                break
            after = found + len(delimiter)
            exact_left = found == 0 or line[found - 1] != "`"
            exact_right = after == len(line) or line[after] != "`"
            if exact_left and exact_right:
                closing = found
                break
            search_from = after
        if closing < 0:
            output.append(delimiter)
            cursor = run_end
        else:
            cursor = closing + len(delimiter)
    return "".join(output)


def fence_opening(line: str) -> tuple[Any, list[tuple[str, int]]]:
    """Locate a fence after blockquote/list container markers."""
    content = line.expandtabs(4)
    containers: list[tuple[str, int]] = []
    while True:
        quote = QUOTE_PREFIX_RE.match(content)
        listing = LIST_PREFIX_RE.match(content)
        if quote:
            containers.append(("quote", 0))
            content = content[quote.end():]
        elif listing:
            containers.append(("list", listing.end()))
            content = content[listing.end():]
        else:
            return FENCE_OPEN_RE.match(content), containers


def fence_content(line: str, containers: list[tuple[str, int]]) -> str | None:
    content = line.expandtabs(4)
    if not content.strip():
        return ""
    for kind, indentation in containers:
        if kind == "quote":
            prefix = QUOTE_PREFIX_RE.match(content)
            if not prefix:
                return None
            content = content[prefix.end():]
        else:
            if not content.startswith(" " * indentation):
                return None
            content = content[indentation:]
    return content


def active_lines(text: str) -> Iterable[tuple[int, str]]:
    fence_character = ""
    fence_length = 0
    containers: list[tuple[str, int]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if fence_character:
            content = fence_content(line, containers)
            if content is not None:
                closing = re.fullmatch(
                    rf" {{0,3}}{re.escape(fence_character)}{{{fence_length},}}\s*",
                    content,
                )
                if closing:
                    fence_character = ""
                    fence_length = 0
                    containers = []
                continue
            # A list/quote boundary also ends its unclosed fenced block.
            fence_character = ""
            fence_length = 0
            containers = []
        opening, opening_containers = fence_opening(line)
        if opening and not (opening.group(1).startswith("`") and "`" in opening.group(2)):
            marker = opening.group(1)
            fence_character = marker[0]
            fence_length = len(marker)
            containers = opening_containers
            continue
        yield number, strip_inline_code(line)


def pipe_is_escaped(value: str, position: int) -> bool:
    backslashes = 0
    cursor = position - 1
    while cursor >= 0 and value[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def wiki_alias_parts(raw: str) -> tuple[str, str | None, bool]:
    for position, character in enumerate(raw):
        if character != "|":
            continue
        escaped = pipe_is_escaped(raw, position)
        target = raw[:position]
        if escaped:
            target = target[:-1]
        return target, raw[position + 1 :], escaped
    return raw, None, False


def is_markdown_table_separator(line: str) -> bool:
    stripped = line.strip()
    if not stripped or "|" not in stripped:
        return False
    cells = re.split(r"(?<!\\)\|", stripped)
    if cells and not cells[0].strip():
        cells = cells[1:]
    if cells and not cells[-1].strip():
        cells = cells[:-1]
    return bool(cells) and all(
        TABLE_SEPARATOR_CELL_RE.fullmatch(cell.strip()) for cell in cells
    )


def markdown_table_line_numbers(text: str) -> set[int]:
    lines = list(active_lines(text))
    numbers: set[int] = set()
    for position, (line_number, line) in enumerate(lines):
        if not is_markdown_table_separator(line) or position == 0:
            continue
        header_number, header = lines[position - 1]
        if not re.search(r"(?<!\\)\|", header):
            continue
        numbers.update({header_number, line_number})
        cursor = position + 1
        while cursor < len(lines):
            row_number, row = lines[cursor]
            if not row.strip() or not re.search(r"(?<!\\)\|", row):
                break
            numbers.add(row_number)
            cursor += 1
    return numbers


def strip_code(text: str) -> str:
    lines = text.splitlines()
    kept = dict(active_lines(text))
    return "\n".join(kept.get(number, "") for number in range(1, len(lines) + 1))


def normalize_rel(path: Path, root: Path) -> str:
    return unicodedata.normalize("NFC", path.relative_to(root).as_posix())


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def validate_relative_path(value: str, field: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError(f"invalid config: {field} contains an empty or invalid path")
    raw_normalized = value.replace("\\", "/")
    normalized = raw_normalized.strip("/")
    candidate = Path(normalized)
    if (
        Path(value).is_absolute()
        or raw_normalized.startswith("/")
        or re.match(r"^[A-Za-z]:/", raw_normalized)
        or not normalized
        or ".." in candidate.parts
    ):
        raise ValueError(f"invalid config: {field} must stay inside memory_root: {value}")
    return candidate.as_posix()


def require_string_list(config: dict[str, Any], name: str) -> list[str]:
    value = config.get(name, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"invalid config: {name} must be an array of strings")
    return value


def reject_unknown_keys(value: dict[str, Any], allowed: set[str], field: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(f"invalid config: unknown key in {field}: {unknown[0]}")


def validate_code(value: Any, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Z]{2,5}", value):
        raise ValueError(f"invalid config: {field} must be an uppercase lifecycle code")
    return value


def validate_path_list(config: dict[str, Any], name: str) -> list[str]:
    return [validate_relative_path(value, name) for value in require_string_list(config, name)]


def compile_patterns(values: list[str], field: str) -> list[re.Pattern[str]]:
    patterns: list[re.Pattern[str]] = []
    for value in values:
        try:
            patterns.append(re.compile(value))
        except re.error as exc:
            raise ValueError(f"invalid config: bad regular expression in {field}: {exc}") from exc
    return patterns


def validate_url_policy(config: dict[str, Any], strict_keys: bool) -> dict[str, Any]:
    url = config.get("url", {})
    if not isinstance(url, dict):
        raise ValueError("invalid config: url must be an object")
    if strict_keys:
        reject_unknown_keys(url, URL_KEYS, "url")
    timeout = url.get("timeout_seconds", 10)
    workers = url.get("workers", 8)
    classes = url.get("classes", [])
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
        raise ValueError("invalid config: url.timeout_seconds must be positive")
    if not isinstance(workers, int) or isinstance(workers, bool) or workers <= 0:
        raise ValueError("invalid config: url.workers must be a positive integer")
    if not isinstance(classes, list):
        raise ValueError("invalid config: url.classes must be an array")

    validated_classes: list[dict[str, Any]] = []
    for position, item in enumerate(classes):
        field = f"url.classes[{position}]"
        if not isinstance(item, dict):
            raise ValueError(f"invalid config: {field} must be an object")
        if strict_keys:
            reject_unknown_keys(item, URL_CLASS_KEYS, field)
        name = item.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"invalid config: {field}.name must be a string")
        url_patterns = item.get("url_patterns", [])
        source_patterns = item.get("source_patterns", [])
        if not isinstance(url_patterns, list) or not all(
            isinstance(value, str) for value in url_patterns
        ):
            raise ValueError(f"invalid config: {field}.url_patterns must be an array of strings")
        if not isinstance(source_patterns, list) or not all(
            isinstance(value, str) for value in source_patterns
        ):
            raise ValueError(f"invalid config: {field}.source_patterns must be an array of strings")
        check = item.get("check", True)
        strict = item.get("strict", False)
        if not isinstance(check, bool) or not isinstance(strict, bool):
            raise ValueError(f"invalid config: {field} check and strict must be booleans")
        validated_classes.append(
            {
                "name": name,
                "url_patterns": url_patterns,
                "source_patterns": source_patterns,
                "check": check,
                "strict": strict,
                "_url_patterns": compile_patterns(url_patterns, f"{field}.url_patterns"),
                "_source_patterns": compile_patterns(
                    source_patterns, f"{field}.source_patterns"
                ),
            }
        )
    return {
        "timeout_seconds": float(timeout),
        "workers": workers,
        "classes": validated_classes,
    }


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    schema_version = config.get("schema_version")
    if type(schema_version) is not int or schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError("invalid config: schema_version must be 1, 2 or 3")
    strict_keys = schema_version in {2, 3}
    if strict_keys:
        allowed = V2_CONFIG_KEYS | ({"file_namespace", "parent_base_id", "naming_profile", "allocation_owner", "last_issued"} if schema_version == 3 else set())
        reject_unknown_keys(config, allowed, "schema")
    if schema_version == 3:
        validate_profile(config)

    index_field = "index" if schema_version == 1 else "index_path"
    index = config.get(index_field, "index.md")
    if not isinstance(index, str):
        raise ValueError(f"invalid config: {index_field} must be a string")

    validated: dict[str, Any] = dict(config)
    validated[index_field] = validate_relative_path(index, index_field)
    validated["_index_path"] = validated[index_field]
    if schema_version == 1:
        for field in (
            "required_paths",
            "excluded_folders",
            "known_top_level_folders",
            "rules_roots",
        ):
            validated[field] = validate_path_list(config, field)
        validated["_excluded_paths"] = validated["excluded_folders"]
    else:
        for field in (
            "required_paths",
            "excluded_paths",
            "known_top_level_folders",
            "rules_roots",
        ):
            validated[field] = validate_path_list(config, field)
        validated["_excluded_paths"] = validated["excluded_paths"]
        for field in ("base_id", "scope"):
            value = config.get(field, "")
            if not isinstance(value, str):
                raise ValueError(f"invalid config: {field} must be a string")
            validated[field] = value

    validated["lifecycle_codes"] = [
        validate_code(code, "lifecycle_codes")
        for code in require_string_list(config, "lifecycle_codes")
    ]
    validated["legacy_markers"] = require_string_list(config, "legacy_markers")
    historical = require_string_list(config, "historical_source_patterns")
    validated["historical_source_patterns"] = historical
    validated["_historical_patterns"] = compile_patterns(
        historical, "historical_source_patterns"
    )

    if strict_keys:
        forbidden = require_string_list(config, "forbidden_path_patterns")
        validated["forbidden_path_patterns"] = forbidden
        validated["_forbidden_patterns"] = compile_patterns(
            forbidden, "forbidden_path_patterns"
        )

        disallowed = config.get("disallowed_lifecycle_codes", [])
        if not isinstance(disallowed, list):
            raise ValueError("invalid config: disallowed_lifecycle_codes must be an array")
        validated_disallowed: list[dict[str, Any]] = []
        for position, item in enumerate(disallowed):
            field = f"disallowed_lifecycle_codes[{position}]"
            if not isinstance(item, dict):
                raise ValueError(f"invalid config: {field} must be an object")
            reject_unknown_keys(item, {"code", "path_prefixes"}, field)
            validated_disallowed.append(
                {
                    "code": validate_code(item.get("code"), f"{field}.code"),
                    "path_prefixes": [
                        validate_relative_path(value, f"{field}.path_prefixes")
                        for value in require_string_list(item, "path_prefixes")
                    ],
                }
            )
        validated["disallowed_lifecycle_codes"] = validated_disallowed

        section_rules = config.get("index_section_rules", [])
        if not isinstance(section_rules, list):
            raise ValueError("invalid config: index_section_rules must be an array")
        validated_rules: list[dict[str, Any]] = []
        for position, item in enumerate(section_rules):
            field = f"index_section_rules[{position}]"
            if not isinstance(item, dict):
                raise ValueError(f"invalid config: {field} must be an object")
            reject_unknown_keys(item, {"heading", "path_prefixes", "lifecycle_codes"}, field)
            heading = item.get("heading")
            if not isinstance(heading, str) or not heading.strip():
                raise ValueError(f"invalid config: {field}.heading must be a non-empty string")
            validated_rules.append(
                {
                    "heading": heading.strip(),
                    "path_prefixes": [
                        validate_relative_path(value, f"{field}.path_prefixes")
                        for value in require_string_list(item, "path_prefixes")
                    ],
                    "lifecycle_codes": [
                        validate_code(value, f"{field}.lifecycle_codes")
                        for value in require_string_list(item, "lifecycle_codes")
                    ],
                }
            )
        validated["index_section_rules"] = validated_rules
    else:
        validated["_forbidden_patterns"] = []
        validated["disallowed_lifecycle_codes"] = []
        validated["index_section_rules"] = []

    validated["url"] = validate_url_policy(config, strict_keys)
    return validated


def load_config(root: Path, explicit_path: str | None) -> tuple[dict[str, Any], Path | None]:
    root = root.resolve()
    config_path = Path(explicit_path) if explicit_path else root / DEFAULT_CONFIG_NAME
    if not explicit_path and not config_path.exists():
        candidates = sorted(root.glob("CFG_*.json"))
        if len(candidates) > 1:
            raise ValueError("ambiguous root config; use --config")
        if candidates:
            config_path = candidates[0]
    if not config_path.is_absolute():
        config_path = root / config_path
    config_path = config_path.resolve()
    if not is_within(config_path, root):
        raise ValueError("config path must stay inside memory_root")
    if not config_path.exists():
        if explicit_path:
            raise ValueError(f"config file does not exist: {config_path}")
        return {}, None
    if not config_path.is_file():
        raise ValueError(f"config path is not a file: {config_path}")
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid config: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("invalid config: top-level JSON value must be an object")
    return validate_config(raw), config_path


def path_is_excluded(relative_path: str, excluded_paths: list[str]) -> bool:
    normalized = relative_path.replace("\\", "/").strip("/")
    return any(
        normalized == folder or normalized.startswith(f"{folder}/")
        for folder in excluded_paths
    )


def collect_files(root: Path, excluded_paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        resolved = path.resolve()
        if not is_within(resolved, root):
            raise ValueError("unsafe path outside vault")
        relative = normalize_rel(path, root)
        if not path_is_excluded(relative, excluded_paths):
            files.append(path)
    return sorted(
        files,
        key=lambda item: (
            normalize_rel(item, root).casefold(),
            normalize_rel(item, root),
        ),
    )


def collect_markdown_files(root: Path, excluded_paths: list[str]) -> list[Path]:
    return [
        path
        for path in collect_files(root, excluded_paths)
        if path.suffix.casefold() == ".md"
    ]


def wiki_target_path(raw: str) -> str | None:
    target, _, _ = wiki_alias_parts(raw)
    target = target.split("#", 1)[0].strip()
    if not target or SCHEME_RE.match(target):
        return None
    return unicodedata.normalize("NFC", unquote(target).replace("\\", "/")).lstrip("/")


def wiki_target_candidates(raw: str) -> list[str]:
    target = wiki_target_path(raw)
    if target is None:
        return []
    candidates = [target]
    if not target.casefold().endswith(".md"):
        candidates.append(f"{target}.md")
    return candidates


def wiki_target_text(raw: str) -> str | None:
    candidates = wiki_target_candidates(raw)
    return candidates[-1] if candidates else None


def binary_wiki_target(raw: str) -> bool:
    target = wiki_target_path(raw)
    return bool(target and Path(target).suffix.casefold() not in {"", ".md"})


def resolve_wiki_target(
    raw: str, source_relative: str, relative_files: list[str]
) -> tuple[str, str | None, list[str]]:
    reference, _, _ = wiki_alias_parts(raw)
    if reference.startswith("#"):
        return ("found", source_relative, []) if source_relative in relative_files else ("missing", source_relative, [])
    target_options = wiki_target_candidates(raw)
    original = unquote(reference.split("#", 1)[0]).replace("\\", "/").strip()
    if original.startswith("/") or re.match(r"^[A-Za-z]:", original):
        return "missing", None, []
    if not target_options:
        return "ignored", None, []
    file_set = set(relative_files)

    for target in target_options:
        if target in file_set:
            if relative_files.count(target) > 1:
                return "ambiguous", None, [v for v in relative_files if v == target]
            return "found", target, []

    source_dir = posixpath.dirname(source_relative)
    for target in target_options:
        source_candidate = posixpath.normpath(posixpath.join(source_dir, target))
        if not source_candidate.startswith("../") and source_candidate in file_set:
            return "found", source_candidate, []

    if ".." in Path(original).parts:
        return "missing", target_options[-1], []

    candidate_basenames = {
        posixpath.basename(target).casefold() for target in target_options
    }
    candidates = sorted(
        (
            relative
            for relative in relative_files
            if posixpath.basename(relative).casefold() in candidate_basenames
        ),
        key=lambda value: (value.casefold(), value),
    )
    if len(candidates) == 1:
        return "found", candidates[0], []
    if len(candidates) > 1:
        return "ambiguous", None, candidates
    return "missing", target_options[-1], []


def resolve_markdown_target(raw: str, source: Path, root: Path) -> Path | None:
    target = raw.strip()
    if not target or target.startswith("#") or SCHEME_RE.match(target):
        return None
    path_only = unquote(target.split("#", 1)[0].strip()).replace("\\", "/")
    if not path_only:
        return None
    if path_only.startswith("/") or re.match(r"^[A-Za-z]:", path_only):
        raise ValueError("unsafe path outside vault")
    resolved = resolve_unicode_path(source.parent / path_only, root)
    return resolved


def normalize_unicode(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def safe_display(value: str) -> str:
    return "".join(f"\\x{ord(c):02x}" if ord(c) < 32 or ord(c) == 127 else c for c in normalize_unicode(value))


def resolve_inside(candidate: Path, boundary: Path, message: str) -> Path:
    if not is_within(candidate.resolve(), boundary.resolve()):
        raise ValueError(message)
    return candidate.resolve()


def resolve_unicode_path(candidate: Path, boundary: Path | None = None) -> Path:
    candidate = candidate.resolve()
    if boundary is not None:
        resolve_inside(candidate, boundary, "unsafe path outside vault")
    parts = candidate.parts
    if not parts:
        return candidate
    current = Path(parts[0])
    for part in parts[1:]:
        direct = current / part
        try:
            children = list(current.iterdir())
            exact_matches = [child for child in children if child.name == part]
            matches = [
                child
                for child in children
                if normalize_unicode(child.name) == normalize_unicode(part)
            ]
            if not matches and direct.exists():
                matches = [child for child in children if naming_key(child.name) == naming_key(part)]
        except OSError:
            if direct.exists():
                current = direct
                continue
            return candidate
        if len(exact_matches) == 1:
            current = exact_matches[0]
            continue
        if len(matches) != 1:
            if not matches and direct.exists():
                current = direct
                continue
            return candidate
        current = matches[0]
    resolved = current.resolve()
    if boundary is not None:
        resolve_inside(resolved, boundary, "unsafe path outside vault")
    return resolved


def fragment_exists(raw: str, path: Path, markdown: bool = False) -> bool:
    reference, _, _ = wiki_alias_parts(raw)
    _, separator, fragment = reference.partition("#")
    if not separator or not fragment or path.suffix.casefold() != ".md" or not path.is_file():
        return True
    original_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    lines = list(active_lines("\n".join(original_lines)))
    def anchor(value):
        value = re.sub(r"(`+)(.*?)\1", lambda m: m[2], value)
        value = re.sub(r"(\*{1,3}|_{1,3}|~~)(.*?)\1", lambda m: m[2], value)
        value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
        return " ".join(normalize_unicode(unquote(value)).strip().split()).casefold()
    headings, blocks, slugs = set(), set(), set()
    def add_heading(value):
        visible = anchor(value)
        headings.add(visible)
        slug = ''.join(c if c.isalnum() or c in '_-' else '-' if c == ' ' else '' for c in visible)
        candidate, sequence = slug, 0
        while candidate in slugs:
            sequence += 1
            candidate = slug + '-' + str(sequence)
        slugs.add(candidate)
    for i, (line_number, line) in enumerate(lines):
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", original_lines[line_number - 1])
        if match:
            add_heading(match[1])
        if i + 1 < len(lines) and lines[i + 1][0] == line_number + 1 and line.strip() and re.fullmatch(r"\s{0,3}(?:=+|-+)\s*", lines[i + 1][1]):
            add_heading(original_lines[line_number - 1])
        block = re.search(r"(?:^|\s)\^([A-Za-z0-9-]+)\s*$", line)
        if block:
            blocks.add(anchor(block[1]))
    fragment = unquote(fragment)
    return anchor(fragment[1:]) in blocks if fragment.startswith("^") else anchor(fragment) in headings or (markdown and anchor(fragment) in slugs)


def safe_result(result, inventory, index_entries, index_name):
    """Never emit document-controlled link values, regex captures or URL credentials."""
    stale = {v: next((e['line'] for e in index_entries if e['target'] == v), '0') for v in result['STALE_INDEX_ENTRIES']}
    result['STALE_INDEX_ENTRIES'] = [f"{safe_display(index_name)} -> STALE_INDEX_ENTRY_LINE_{stale[v]}" for v in result['STALE_INDEX_ENTRIES']]
    def clean(value):
        if isinstance(value, list):
            return [clean(i) for i in value]
        if isinstance(value, dict):
            output = dict(value)
            if 'kind' in output:
                # Resolved inventory paths and lifecycle codes are useful safe identity data.
                target = output.get('target', '')
                if target not in inventory and not re.fullmatch(r'[A-Z]{2,5}(?:_[A-Z0-9]+)?-[0-9]{4,}', target):
                    output['target'] = ''
                safe_line_kinds = {'AMBIGUOUS_WIKI_LINK', 'AMBIGUOUS_WIKI_EMBED', 'INDEX_SECTION_MISMATCH',
                                   'UNESCAPED_WIKI_ALIAS_IN_TABLE', 'FORBIDDEN_PATH_PATTERN', 'FORBIDDEN_PATH_PATTERN_HISTORICAL'}
                line = re.match(r'^Line ([0-9]+)', output.get('message', '')) if output['kind'] in safe_line_kinds else None
                output['message'] = 'Line ' + line[1] if line else ''
                if line and output['kind'].startswith('FORBIDDEN_PATH_PATTERN'):
                    output['message'] += ': forbidden route-like reference.'
            if 'url' in output:
                output['url'] = '[redacted]'
                output['error'] = 'request failed' if output.get('error') else None
            return {k: clean(v) for k, v in output.items()}
        if isinstance(value, str):
            return safe_display(value)
        return value
    return clean(result)


def finding(
    kind: str,
    source: str = "",
    target: str = "",
    message: str = "",
    class_name: str = "",
) -> dict[str, str]:
    return {
        "kind": kind,
        "source": source,
        "target": target,
        "class": class_name,
        "message": message,
    }


def parse_index(
    index_path: Path, root: Path, relative_files: list[str]
) -> tuple[list[dict[str, str]], set[str], list[dict[str, str]]]:
    if not index_path.exists() or not index_path.is_file() or not is_within(index_path.resolve(), root):
        return [], set(), []
    source_relative = normalize_rel(index_path, root)
    entries: list[dict[str, str]] = []
    headings: set[str] = set()
    ambiguities: list[dict[str, str]] = []
    current_heading = ""
    text = index_path.read_text(encoding="utf-8", errors="replace")
    for line_number, line in active_lines(text):
        heading = HEADING_RE.match(line)
        if heading:
            current_heading = heading.group(1).strip()
            headings.add(current_heading.casefold())
            continue
        for regex in (WIKI_EMBED_RE, WIKI_LINK_RE):
            for match in regex.finditer(line):
                raw = match.group(1)
                status, resolved, candidates = resolve_wiki_target(
                    raw, source_relative, relative_files
                )
                target = resolved or wiki_target_text(raw)
                if target:
                    entries.append(
                        {
                            "heading": current_heading,
                            "target": target,
                            "raw": raw,
                            "line": str(line_number),
                        }
                    )
                if status == "ambiguous":
                    ambiguities.append(
                        finding(
                            "AMBIGUOUS_WIKI_LINK",
                            source_relative,
                            raw,
                            "Candidates: " + ", ".join(candidates),
                        )
                    )
        for regex in (MD_ATTACHMENT_RE, MD_LINK_RE):
            for match in regex.finditer(line):
                try:
                    resolved_path = resolve_markdown_target(match.group(1), index_path, root)
                except ValueError:
                    continue
                if resolved_path is not None and resolved_path.suffix.casefold() == ".md":
                    entries.append(
                        {
                            "heading": current_heading,
                            "target": normalize_rel(resolved_path, root),
                            "raw": match.group(1),
                            "line": str(line_number),
                        }
                    )
    return entries, headings, ambiguities


def target_has_prefix(target: str, prefixes: list[str]) -> bool:
    normalized = target.replace("\\", "/").strip("/")
    return any(normalized == prefix or normalized.startswith(f"{prefix}/") for prefix in prefixes)


def target_matches_section(target: str, rule: dict[str, Any]) -> bool:
    if target_has_prefix(target, rule["path_prefixes"]):
        return True
    return any(re.search(rf"\b{re.escape(code)}(?:_[A-Z][A-Z0-9]{{1,15}})?-\d{{4,}}(?!\d)", target) for code in rule["lifecycle_codes"])


def index_policy_findings(
    entries: list[dict[str, str]], headings: set[str], rules: list[dict[str, Any]]
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for rule in rules:
        if rule["heading"].casefold() not in headings:
            findings.append(
                finding(
                    "MISSING_INDEX_SECTION",
                    target=rule["heading"],
                    message="Configured index heading is missing.",
                )
            )

    by_target: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        by_target.setdefault(entry["target"].casefold(), []).append(entry)
    for duplicates in by_target.values():
        if len(duplicates) > 1:
            target = sorted((item["target"] for item in duplicates), key=lambda value: (value.casefold(), value))[0]
            findings.append(
                finding(
                    "DUPLICATE_INDEX_ENTRY",
                    target=target,
                    message=f"Index contains {len(duplicates)} entries for this target.",
                )
            )

    for entry in entries:
        expected = sorted(
            {
                rule["heading"]
                for rule in rules
                if target_matches_section(entry["target"], rule)
            },
            key=lambda value: (value.casefold(), value),
        )
        if expected and entry["heading"].casefold() not in {value.casefold() for value in expected}:
            findings.append(
                finding(
                    "INDEX_SECTION_MISMATCH",
                    source="",
                    target=entry["target"],
                    message="Line " + entry["line"],
                )
            )
    return findings


def duplicate_filename_findings(
    root: Path, relative_files: list[str], compare_roots: list[Path],
    names: set[str] | None = None,
) -> list[dict[str, str]]:
    grouped: dict[str, list[str]] = {}
    seen_paths: set[Path] = set()

    def add_candidate(path: Path, label: str, relative: str) -> None:
        if names is not None and naming_key(path.name) not in names:
            return
        resolved = path.resolve()
        if resolved in seen_paths:
            return
        seen_paths.add(resolved)
        if any(part.casefold() == ".obsidian" for part in Path(relative).parts):
            return
        grouped.setdefault(naming_key(path.name), []).append(f"{label}:{relative}")

    for path in collect_files(root, []):
        relative = normalize_rel(path, root)
        if relative in relative_files:
            add_candidate(path, "primary", relative)
    for position, compare_root in enumerate(compare_roots, start=1):
        files = collect_files(compare_root, [])
        for path in files:
            relative = normalize_rel(path, compare_root)
            add_candidate(path, f"compare[{position}]", relative)

    results: list[dict[str, str]] = []
    for candidates in grouped.values():
        if len(candidates) < 2:
            continue
        ordered = sorted(candidates, key=lambda value: (value.casefold(), value))
        results.append(
            finding(
                "DUPLICATE_MANAGED_FILENAME",
                target="; ".join(ordered),
                message="Managed filename is not unique case-insensitively.",
            )
        )
    return sorted(results, key=lambda item: (item["target"].casefold(), item["target"]))


def entry_link_targets(
    line: str, source: Path, source_relative: str, root: Path, relative_files: list[str]
) -> list[str]:
    targets: list[str] = []
    for regex in (WIKI_EMBED_RE, WIKI_LINK_RE):
        for match in regex.finditer(line):
            status, resolved, _ = resolve_wiki_target(match.group(1), source_relative, relative_files)
            target = resolved or wiki_target_text(match.group(1))
            if status != "ignored" and target:
                targets.append(target)
    for regex in (MD_ATTACHMENT_RE, MD_LINK_RE):
        for match in regex.finditer(line):
            try:
                resolved_path = resolve_markdown_target(match.group(1), source, root)
            except ValueError:
                continue
            if resolved_path is not None and resolved_path.suffix.casefold() == ".md":
                targets.append(normalize_rel(resolved_path, root))
    return targets


def disallowed_code_findings(
    root: Path,
    files: list[Path],
    relative_files: list[str],
    index_name: str,
    rules: list[dict[str, Any]],
    selected: set[str] | None = None,
    touched: set[str] | None = None,
) -> list[dict[str, str]]:
    results: dict[tuple[str, str, str], dict[str, str]] = {}
    for rule in rules:
        code = rule["code"]
        code_re = re.compile(rf"\b{re.escape(code)}(?:_[A-Z][A-Z0-9]{{1,15}})?-\d{{4,}}(?!\d)")
        for relative in relative_files:
            if selected is not None and relative not in selected:
                continue
            if target_has_prefix(relative, rule["path_prefixes"]):
                match = code_re.search(relative)
                if match:
                    item = finding(
                        "DISALLOWED_LIFECYCLE_CODE",
                        source=relative,
                        target=match.group(0),
                        message="Disallowed lifecycle code appears in a managed path.",
                    )
                    results[(item["source"], item["target"], item["message"])] = item

        entry_files = [
            path
            for path in files
            if (
                normalize_rel(path, root) == index_name
                or path.stem.casefold() == "todo"
                or path.stem.casefold().startswith("todo_")
                or target_has_prefix(normalize_rel(path, root), rule["path_prefixes"])
            )
        ]
        for path in entry_files:
            source_relative = normalize_rel(path, root)
            text = path.read_text(encoding="utf-8", errors="replace")
            for _, line in active_lines(text):
                targets = entry_link_targets(line, path, source_relative, root, relative_files)
                if not targets:
                    continue
                matches = sorted(set(code_re.findall(line)))
                for target in targets:
                    if selected is not None and source_relative not in selected and target not in (touched or set()):
                        continue
                    if not target_has_prefix(target, rule["path_prefixes"]):
                        continue
                    entry_matches = matches
                    if selected is not None and source_relative not in selected:
                        # An unrelated link's alias on the same line is outside
                        # the local scope; a plain entry label still applies.
                        entry_matches = code_re.findall(without_link_markup(line))
                        for regex in (WIKI_EMBED_RE, WIKI_LINK_RE, MD_ATTACHMENT_RE, MD_LINK_RE):
                            for link in regex.finditer(line):
                                if target in entry_link_targets(link.group(0), path, source_relative, root, relative_files):
                                    entry_matches.extend(code_re.findall(link.group(0)))
                    for match in sorted(set(entry_matches)):
                        item = finding(
                            "DISALLOWED_LIFECYCLE_CODE",
                            source=source_relative,
                            target=match,
                            message=f"Active entry targets {target}.",
                        )
                        results[(item["source"], item["target"], item["message"])] = item
    return sorted(
        results.values(),
        key=lambda item: (item["source"].casefold(), item["source"], item["target"]),
    )


def forbidden_link_targets(line: str) -> list[str]:
    targets: list[str] = []
    for regex in (WIKI_EMBED_RE, WIKI_LINK_RE):
        for match in regex.finditer(line):
            target = wiki_target_path(match.group(1))
            if target:
                targets.append(target)
    for regex in (MD_ATTACHMENT_RE, MD_LINK_RE):
        for match in regex.finditer(line):
            target = match.group(1).strip()
            target = re.sub(r"\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\))\s*$", "", target)
            target = target.split("#", 1)[0].strip().strip("<>")
            if target and not SCHEME_RE.match(target):
                targets.append(unquote(target).replace("\\", "/"))
    return targets


def without_link_markup(line: str) -> str:
    for regex in (WIKI_EMBED_RE, WIKI_LINK_RE, MD_ATTACHMENT_RE, MD_LINK_RE):
        line = regex.sub("", line)
    return line


def plain_route_targets(line: str) -> list[str]:
    text = without_link_markup(line).strip()
    text = re.sub(r"^(?:>\s*)?(?:[-*+]\s+)?", "", text).strip()
    if not text:
        return []
    if re.fullmatch(r"[A-Za-z]:[\\/][^\s]+", text):
        return [text.replace("\\", "/")]
    if ":" in text:
        label, value = text.split(":", 1)
        normalized_label = label.strip().casefold()
        if normalized_label.endswith(("route", "path", "маршрут", "путь")):
            candidate = value.strip()
            return [candidate] if candidate else []
        return []
    if re.fullmatch(r"\S+", text) and ("/" in text or "\\" in text):
        return [text.replace("\\", "/")]
    return []


def frontmatter_lines(text: str) -> set[int]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return set()
    for position, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            return set(range(1, position + 1))
    return set()


def forbidden_route_findings(
    root: Path,
    files: list[Path],
    patterns: list[re.Pattern[str]],
    historical_patterns: list[re.Pattern[str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    strict: dict[tuple[str, str], dict[str, str]] = {}
    advisory: dict[tuple[str, str], dict[str, str]] = {}
    for path in files:
        source = normalize_rel(path, root)
        historical = any(pattern.search(source) for pattern in historical_patterns)
        text = path.read_text(encoding="utf-8", errors="replace")
        yaml_lines = frontmatter_lines(text)
        for line_number, line in active_lines(text):
            if line_number in yaml_lines:
                continue
            targets = forbidden_link_targets(line) + plain_route_targets(line)
            for target in targets:
                for pattern in patterns:
                    for match in pattern.finditer(target):
                        value = match.group(0)
                        kind = (
                            "FORBIDDEN_PATH_PATTERN_HISTORICAL"
                            if historical
                            else "FORBIDDEN_PATH_PATTERN"
                        )
                        item = finding(kind, source=source, target=value, message=f"Line {line_number}: forbidden route-like reference.")
                        (advisory if historical else strict)[(source, value)] = item
    key = lambda item: (item["source"].casefold(), item["source"], item["target"])
    return sorted(strict.values(), key=key), sorted(advisory.values(), key=key)


def classify_url(url: str, source: str, config: dict[str, Any]) -> dict[str, Any]:
    for item in config.get("url", {}).get("classes", []):
        if any(pattern.search(url) for pattern in item["_url_patterns"]) or any(
            pattern.search(source) for pattern in item["_source_patterns"]
        ):
            return item
    return {
        "name": "unclassified",
        "check": True,
        "strict": False,
        "_url_patterns": [],
        "_source_patterns": [],
    }


def request_url(url: str, method: str, timeout: float) -> tuple[bool, int | None, str | None]:
    request = urllib.request.Request(url, method=method, headers={"User-Agent": "obsidian-memory/1"})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            status = int(response.status)
            return (200 <= status < 400 or status in {401, 403}), status, None
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        return (status in {401, 403}), status, str(exc)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, None, str(exc)


def check_url(item: dict[str, Any], timeout: float) -> dict[str, Any]:
    reachable, status, error = request_url(item["url"], "HEAD", timeout)
    method = "HEAD"
    fallback = False
    if not reachable and (status is None or status in {400, 404, 405, 501}):
        reachable, status, error = request_url(item["url"], "GET", timeout)
        method = "GET"
        fallback = True
    return {
        **item,
        "method": method,
        "fallback_get": fallback,
        "status": status,
        "reachable": reachable,
        "error": error,
    }


def audit(
    root: Path,
    index_name: str,
    config: dict[str, Any] | Path | None = None,
    check_urls: bool = False,
    compare_roots: list[Path] | None = None,
    changed_paths: list[str] | None = None,
    removed_paths: list[str] | None = None,
    *, vault_root: Path | None = None, index_exclude: list[str] | None = None,
) -> dict[str, Any]:
    legacy_api = config is None or isinstance(config, Path)
    if legacy_api:
        if isinstance(config, Path):
            vault_root = config
        config = {}
        if isinstance(check_urls, list):
            index_exclude = check_urls
        elif check_urls:
            raise ValueError("URL checking requires the configured API or explicit CLI flag")
        check_urls = False
    config = config or {}
    index_exclude = [normalize_unicode(pattern.replace("\\", "/")) for pattern in (index_exclude or [])]
    root = root.resolve()
    vault_root = (vault_root or root).resolve()
    if not is_within(root, vault_root):
        raise ValueError("memory root must be inside the vault root")
    if not is_within((root / index_name).resolve(), root):
        raise ValueError("index must be inside memory root")
    index_name = unicodedata.normalize("NFC", index_name)
    compare_roots = compare_roots or []
    excluded = config.get("_excluded_paths", config.get("excluded_folders", []))
    all_files = collect_files(root, excluded)
    files = [path for path in all_files if path.suffix.casefold() == ".md"]
    relative_all_files = [normalize_rel(path, root) for path in all_files]
    resolution_files = list(relative_all_files)
    if vault_root != root:
        resolution_files.extend(unicodedata.normalize("NFC", os.path.relpath(path, root).replace("\\", "/"))
                                for path in collect_files(vault_root, []) if not is_within(path, root))
    relative_files = [normalize_rel(path, root) for path in files]
    changed = set(changed_paths or [])
    removed = set(removed_paths or [])
    local = bool(changed or removed)
    touched = changed | removed
    selected = changed & set(relative_files)
    old_all_files = sorted(set(relative_all_files) | removed)
    old_md_files = [value for value in old_all_files if Path(value).suffix.casefold() == ".md"]
    affected_sources: set[str] = set(selected)

    def relevant_wiki(raw: str, source: str, embed: bool = False) -> bool:
        if not local or source in selected:
            return True
        inventories = (relative_all_files, old_all_files) if binary_wiki_target(raw) else (relative_files, old_md_files)
        for inventory in inventories:
            _, target, candidates = resolve_wiki_target(raw, source, inventory)
            if target in touched or touched.intersection(candidates):
                return True
        return False
    file_set = set(relative_files)
    incoming = {relative: set() for relative in relative_files}

    wiki_broken: list[str] = []
    wiki_embed_broken: list[str] = []
    markdown_broken: list[str] = []
    attachment_broken: list[str] = []
    ambiguities: list[dict[str, str]] = []
    unescaped_table_aliases: list[dict[str, str]] = []
    tbd_refs: list[str] = []
    old_markers: list[dict[str, str]] = []
    historical_markers: list[dict[str, str]] = []
    removal_findings: list[dict[str, str]] = []
    url_mentions: dict[str, set[str]] = {}
    historical_patterns = config.get("_historical_patterns", [])

    for path in files:
        source = normalize_rel(path, root)
        raw_text = path.read_text(encoding="utf-8", errors="replace")
        text = strip_code(raw_text)
        table_lines = markdown_table_line_numbers(raw_text)
        for line_number, line in active_lines(raw_text):
            if line_number not in table_lines:
                continue
            for regex in (WIKI_EMBED_RE, WIKI_LINK_RE):
                for match in regex.finditer(line):
                    raw = match.group(1)
                    if not relevant_wiki(raw, source, regex is WIKI_EMBED_RE):
                        continue
                    _, alias, escaped = wiki_alias_parts(raw)
                    if alias is not None and not escaped:
                        unescaped_table_aliases.append(
                            finding(
                                "UNESCAPED_WIKI_ALIAS_IN_TABLE",
                                source=source,
                                target=raw,
                                message=(
                                    f"Line {line_number}: escape the table alias "
                                    "delimiter as \\|."
                                ),
                            )
                        )
        for regex, broken, kind in (
            (WIKI_EMBED_RE, wiki_embed_broken, "AMBIGUOUS_WIKI_EMBED"),
            (WIKI_LINK_RE, wiki_broken, "AMBIGUOUS_WIKI_LINK"),
        ):
            for match in regex.finditer(text):
                raw = match.group(1)
                target_inventory = resolution_files if binary_wiki_target(raw) else [v for v in resolution_files if Path(v).suffix.casefold() == ".md"]
                line_number = text.count("\n", 0, match.start()) + 1
                status, target, candidates = resolve_wiki_target(
                    raw, source, target_inventory
                )
                if status == "found" and target and (not local or relevant_wiki(raw, source)) and not fragment_exists(raw, resolve_unicode_path(root / target, vault_root)):
                    status = "missing"
                if status == "found" and target and target in incoming:
                    incoming[target].add(source)
                if not relevant_wiki(raw, source, regex is WIKI_EMBED_RE):
                    continue
                affected_sources.add(source)
                if local and removed and status == "found":
                    old_inventory = old_all_files if binary_wiki_target(raw) else old_md_files
                    _, old_target, old_candidates = resolve_wiki_target(raw, source, old_inventory)
                    if old_target in removed or removed.intersection(old_candidates):
                        removal_findings.append(finding(
                            "WIKI_TARGET_CHANGED_AFTER_REMOVAL", source, raw,
                            "Removed candidate: " + ", ".join(sorted(({old_target} | set(old_candidates)) & removed))
                            + "; current target: " + str(target),
                        ))
                if status == "ambiguous":
                    ambiguities.append(
                        finding(kind, source, "", f"Line {line_number}")
                    )
                elif status == "missing":
                    category = "BROKEN_WIKI_EMBED" if regex is WIKI_EMBED_RE else "BROKEN_WIKILINK"
                    broken.append(f"{safe_display(source)} -> {category}_LINE_{line_number}")

        for regex, broken in (
            (MD_ATTACHMENT_RE, attachment_broken),
            (MD_LINK_RE, markdown_broken),
        ):
            for match in regex.finditer(text):
                raw = match.group(1)
                line_number = text.count("\n", 0, match.start()) + 1
                unsafe = False
                try:
                    target_path = path if raw.strip().startswith("#") else resolve_markdown_target(raw, path, vault_root)
                except ValueError:
                    target_path, unsafe = None, True
                if local and source not in selected and (
                    target_path is None or not is_within(target_path, root) or normalize_rel(target_path, root) not in touched
                ):
                    continue
                affected_sources.add(source)
                invalid_fragment = target_path is not None and target_path.exists() and not fragment_exists(raw, target_path, markdown=True)
                if unsafe or invalid_fragment or (target_path is not None and not target_path.exists()):
                    category = "UNSAFE_MARKDOWN_LINK" if unsafe else ("BROKEN_MARKDOWN_ATTACHMENT" if regex is MD_ATTACHMENT_RE else "BROKEN_MARKDOWN_LINK")
                    broken.append(f"{safe_display(source)} -> {category}_LINE_{line_number}")
                elif (
                    target_path is not None
                    and target_path.suffix.casefold() == ".md"
                    and target_path.exists()
                    and is_within(target_path, root)
                ):
                    target = normalize_rel(target_path, root)
                    if target in incoming:
                        incoming[target].add(source)

        if local and source not in selected:
            continue
        for match in TBD_RE.finditer(text):
            tbd_refs.append(f"{safe_display(source)} -> TBD_REFERENCE_LINE_{text.count(chr(10), 0, match.start()) + 1}")
        historical = any(pattern.search(source) for pattern in historical_patterns)
        for marker in config.get("legacy_markers", []):
            if marker in text:
                item = finding("OLD_LIFECYCLE_MARKER", source, marker)
                (historical_markers if historical else old_markers).append(item)
        for match in URL_RE.finditer(text):
            url = match.group(0).rstrip(".,;:]}`")
            url_mentions.setdefault(url, set()).add(source)

    index_path = resolve_unicode_path(root / index_name, root)
    index_entries, index_headings, index_ambiguities = parse_index(
        index_path, root, old_md_files if local else relative_files
    )
    if local:
        index_ambiguities = [item for item in index_ambiguities if relevant_wiki(item["target"], index_name)]
    ambiguities.extend(index_ambiguities)
    index_targets = {entry["target"] for entry in index_entries}
    missing_from_index = sorted(file_set - index_targets - {v for v in file_set if any(fnmatch.fnmatchcase(v, pattern) for pattern in (index_exclude or []))}, key=lambda value: (value.casefold(), value))
    stale_index = sorted(index_targets - file_set, key=lambda value: (value.casefold(), value))
    if local:
        missing_from_index = [value for value in missing_from_index if value in selected]
        stale_index = [value for value in stale_index if value in removed or index_name in selected]
    zero_incoming = sorted(
        (relative for relative, refs in incoming.items() if not refs and relative != index_name),
        key=lambda value: (value.casefold(), value),
    )
    weak_incoming = sorted(
        (
            relative
            for relative, refs in incoming.items()
            if relative not in {index_name, "log.md"}
            and not (refs - {index_name, "log.md"})
        ),
        key=lambda value: (value.casefold(), value),
    )
    if local:
        zero_incoming = [value for value in zero_incoming if value in selected]
        weak_incoming = [value for value in weak_incoming if value in selected]

    missing_required: list[str] = []
    for relative in config.get("required_paths", []):
        if local and not any(value == relative or value.startswith(relative.rstrip("/") + "/") for value in touched):
            continue
        candidate = (root / relative).resolve()
        if not is_within(candidate, root) or not candidate.exists():
            missing_required.append(relative)

    preflight: list[dict[str, str]] = []
    known_top = set(config.get("known_top_level_folders", [])) | set(excluded)
    if config:
        for directory in sorted(root.iterdir(), key=lambda value: (value.name.casefold(), value.name)):
            if not directory.is_dir() or directory.name in known_top:
                continue
            if not is_within(directory.resolve(), root):
                continue
            if local and directory.name not in {Path(value).parts[0] for value in touched}:
                continue
            preflight.append(
                finding(
                    "PREFLIGHT_UNKNOWN_TOP_LEVEL_FOLDER",
                    target=directory.name,
                    message="Top-level folder is not listed in config.",
                )
            )
        known_codes = set(config.get("lifecycle_codes", []))
        found_codes: set[str] = set()
        for rules_root in config.get("rules_roots", []):
            for path in files:
                relative = normalize_rel(path, root)
                if local and relative not in selected:
                    continue
                if target_has_prefix(relative, [rules_root]):
                    rules_text = strip_code(path.read_text(encoding="utf-8", errors="replace"))
                    found_codes.update(match.group(1) for match in LIFECYCLE_RE.finditer(rules_text))
        for code in sorted(found_codes - known_codes):
            preflight.append(
                finding(
                    "PREFLIGHT_UNKNOWN_LIFECYCLE_CODE",
                    target=code,
                    message="Lifecycle-like code appears in rules but is not listed in config.",
                )
            )

    section_rules = config.get("index_section_rules", [])
    policy_entries = index_entries
    if local and index_name not in selected:
        policy_entries = [entry for entry in index_entries if entry["target"] in touched]
        section_rules = [rule for rule in section_rules if any(target_matches_section(value, rule) for value in touched)]
    index_findings = index_policy_findings(policy_entries, index_headings, section_rules)
    for item in index_findings:
        item["source"] = index_name
    duplicate_findings = duplicate_filename_findings(
        root, relative_all_files, compare_roots,
        {naming_key(Path(value).name) for value in touched} if local else None,
    )
    disallowed_findings = disallowed_code_findings(
        root,
        files,
        relative_files,
        index_name,
        config.get("disallowed_lifecycle_codes", []),
        selected if local else None,
        touched if local else None,
    )
    forbidden_strict, forbidden_advisory = forbidden_route_findings(
        root,
        [path for path in files if normalize_rel(path, root) in selected] if local else files,
        config.get("_forbidden_patterns", []),
        historical_patterns,
    )

    url_items: list[dict[str, Any]] = []
    for url, sources in sorted(url_mentions.items()):
        source_list = sorted(sources)
        url_class = classify_url(url, source_list[0], config)
        url_items.append(
            {
                "url": url,
                "sources": source_list,
                "class": url_class["name"],
                "check": url_class["check"],
                "strict": url_class["strict"],
            }
        )
    url_results: list[dict[str, Any]] = []
    if check_urls:
        candidates = [item for item in url_items if item["check"]]
        url_config = config.get("url", {"timeout_seconds": 10.0, "workers": 8})
        with concurrent.futures.ThreadPoolExecutor(max_workers=url_config["workers"]) as executor:
            url_results = list(
                executor.map(
                    lambda item: check_url(item, url_config["timeout_seconds"]),
                    candidates,
                )
            )

    url_findings: list[dict[str, str]] = []
    strict_url_findings: list[dict[str, str]] = []
    for item in url_results:
        if item["reachable"]:
            continue
        message = item["error"] or f"HTTP {item['status']}"
        url_finding = finding(
            "URL_UNREACHABLE_STRICT" if item["strict"] else "URL_UNREACHABLE_ADVISORY",
            source="; ".join(item["sources"]),
            target=item["url"],
            message=message,
            class_name=item["class"],
        )
        url_findings.append(url_finding)
        if item["strict"]:
            strict_url_findings.append(url_finding)

    naming_findings = audit_names(root, all_files, config, touched if local else None, strip_code)
    strict_problems: list[dict[str, str]] = []
    for name, values in (
        ("BROKEN_WIKI_LINK", wiki_broken),
        ("BROKEN_WIKI_EMBED", wiki_embed_broken),
        ("BROKEN_MARKDOWN_LINK", markdown_broken),
        ("BROKEN_MARKDOWN_ATTACHMENT", attachment_broken),
        ("MISSING_FROM_INDEX", missing_from_index),
        ("STALE_INDEX_ENTRY", stale_index),
        ("TBD_REFERENCE", tbd_refs),
    ):
        strict_problems.extend(finding(name, target=value) for value in values)
    strict_problems.extend(
        finding("PREFLIGHT_MISSING_REQUIRED_PATH", target=value) for value in missing_required
    )
    strict_problems.extend(old_markers)
    strict_problems.extend(ambiguities)
    strict_problems.extend(unescaped_table_aliases)
    strict_problems.extend(duplicate_findings)
    strict_problems.extend(index_findings)
    strict_problems.extend(disallowed_findings)
    strict_problems.extend(forbidden_strict)
    strict_problems.extend(strict_url_findings)
    strict_problems.extend(removal_findings)
    strict_problems.extend(naming_findings)

    advisory_findings: list[dict[str, str]] = []
    advisory_findings.extend(
        finding("ZERO_INCOMING_EXCEPT_INDEX", target=value) for value in zero_incoming
    )
    advisory_findings.extend(
        finding("ONLY_INDEX_OR_LOG_INCOMING", target=value) for value in weak_incoming
    )
    advisory_findings.extend(historical_markers)
    advisory_findings.extend(forbidden_advisory)
    advisory_findings.extend(item for item in url_findings if item not in strict_url_findings)

    result = {
        "MD_FILES": len(relative_files),
        "NAMING_FINDINGS": naming_findings,
        "AMBIGUOUS_WIKI_EMBEDS": [i for i in ambiguities if i["kind"] == "AMBIGUOUS_WIKI_EMBED"],
        "BROKEN_WIKI_LINKS": sorted(wiki_broken),
        "BROKEN_WIKI_EMBEDS": sorted(wiki_embed_broken),
        "BROKEN_MARKDOWN_LINKS": sorted(markdown_broken),
        "BROKEN_MARKDOWN_ATTACHMENTS": sorted(attachment_broken),
        "AMBIGUOUS_WIKI_LINKS": [i for i in ambiguities if i["kind"] != "AMBIGUOUS_WIKI_EMBED"],
        "UNESCAPED_WIKI_ALIASES_IN_TABLE": unescaped_table_aliases,
        "DUPLICATE_MANAGED_FILENAMES": duplicate_findings,
        "INDEX_POLICY_FINDINGS": index_findings,
        "DISALLOWED_LIFECYCLE_CODE_FINDINGS": disallowed_findings,
        "FORBIDDEN_PATH_FINDINGS": forbidden_strict + forbidden_advisory,
        "MISSING_FROM_INDEX": missing_from_index,
        "STALE_INDEX_ENTRIES": stale_index,
        "ZERO_INCOMING_EXCEPT_INDEX": zero_incoming,
        "ONLY_INDEX_OR_LOG_INCOMING": weak_incoming,
        "TBD_REFERENCES": sorted(tbd_refs),
        "MISSING_REQUIRED_PATHS": sorted(missing_required),
        "OLD_LIFECYCLE_MARKERS": sorted(old_markers, key=lambda item: (item["source"], item["target"])),
        "HISTORICAL_LIFECYCLE_MARKERS": sorted(
            historical_markers, key=lambda item: (item["source"], item["target"])
        ),
        "PREFLIGHT_WARNINGS": preflight,
        "URLS_FOUND": len(url_items),
        "URLS_CHECKED": len(url_results),
        "URL_RESULTS": url_results,
        "URL_FINDINGS": url_findings,
        "STRICT_PROBLEMS": strict_problems,
        "ADVISORY_FINDINGS": advisory_findings,
        "STRICT_PROBLEM_COUNT": len(strict_problems),
        "ADVISORY_FINDING_COUNT": len(advisory_findings),
        "PREFLIGHT_WARNING_COUNT": len(preflight),
        "CONFIG_PATH": None,
    }
    if local:
        result["AUDIT_SCOPE"] = {
            "mode": "local", "changed": sorted(changed), "removed": sorted(removed),
            "checked_documents": sorted(selected), "affected_link_sources": sorted(affected_sources),
            "inventory_md_files": len(relative_files),
            "note": "Other documents are scanned for affected links only; this is not a full audit.",
        }
        result["REMOVAL_LINK_FINDINGS"] = removal_findings
    result = safe_result(result, set(relative_all_files) | touched, index_entries, index_name)
    if legacy_api:
        for name in ("BROKEN_WIKI_LINKS", "BROKEN_WIKI_EMBEDS", "BROKEN_MARKDOWN_LINKS", "BROKEN_MARKDOWN_ATTACHMENTS"):
            result[name].sort(key=lambda v: (v.rsplit("_LINE_", 1)[0], int(v.rsplit("_LINE_", 1)[1])))
        for name, kind in (("AMBIGUOUS_WIKI_LINKS", "AMBIGUOUS_WIKILINK"), ("AMBIGUOUS_WIKI_EMBEDS", "AMBIGUOUS_WIKI_EMBED")):
            category = "AMBIGUOUS_WIKI_LINK" if name.endswith("LINKS") else "AMBIGUOUS_WIKI_EMBED"
            result[name] = [f"{i['source']} -> {kind}_LINE_{i['message'].split()[-1]}" for i in ambiguities if i['kind'] == category]
    return result


def emit_section(name: str, values: list[Any]) -> None:
    print(f"{name}={len(values)}")
    for value in values:
        if isinstance(value, dict):
            parts = [value.get("kind", "")]
            if value.get("source"):
                parts.append(value["source"])
            if value.get("target"):
                parts.append(value["target"])
            if value.get("message"):
                parts.append(value["message"])
            print(" -> ".join(parts))
        else:
            print(value)


def render_text(result: dict[str, Any], check_urls: bool) -> None:
    if "AUDIT_SCOPE" in result:
        scope = result["AUDIT_SCOPE"]
        print("AUDIT_MODE=local (not a full audit)")
        emit_section("CHANGED_PATHS", scope["changed"])
        emit_section("REMOVED_PATHS", scope["removed"])
        emit_section("CHECKED_DOCUMENTS", scope["checked_documents"])
        emit_section("AFFECTED_LINK_SOURCES", scope["affected_link_sources"])
        emit_section("REMOVAL_LINK_FINDINGS", result["REMOVAL_LINK_FINDINGS"])
    print(f"MD_FILES={result['MD_FILES']}")
    for name in (
        "BROKEN_WIKI_LINKS",
        "BROKEN_WIKI_EMBEDS",
        "BROKEN_MARKDOWN_LINKS",
        "BROKEN_MARKDOWN_ATTACHMENTS",
        "AMBIGUOUS_WIKI_LINKS",
        "AMBIGUOUS_WIKI_EMBEDS",
        "NAMING_FINDINGS",
        "UNESCAPED_WIKI_ALIASES_IN_TABLE",
        "DUPLICATE_MANAGED_FILENAMES",
        "INDEX_POLICY_FINDINGS",
        "DISALLOWED_LIFECYCLE_CODE_FINDINGS",
        "FORBIDDEN_PATH_FINDINGS",
        "MISSING_FROM_INDEX",
        "STALE_INDEX_ENTRIES",
        "MISSING_REQUIRED_PATHS",
        "OLD_LIFECYCLE_MARKERS",
        "TBD_REFERENCES",
        "ZERO_INCOMING_EXCEPT_INDEX",
        "ONLY_INDEX_OR_LOG_INCOMING",
        "HISTORICAL_LIFECYCLE_MARKERS",
        "PREFLIGHT_WARNINGS",
    ):
        emit_section(name, result[name])
    print(f"STRICT_PROBLEM_COUNT={result['STRICT_PROBLEM_COUNT']}")
    print(f"ADVISORY_FINDING_COUNT={result['ADVISORY_FINDING_COUNT']}")
    print(f"PREFLIGHT_WARNING_COUNT={result['PREFLIGHT_WARNING_COUNT']}")
    if check_urls:
        print(f"URLS_CHECKED={result['URLS_CHECKED']}/{result['URLS_FOUND']}")
    else:
        print(f"URLS_FOUND={result['URLS_FOUND']} (reachability not checked)")


def output_path_inside_root(value: str, root: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    if not is_within(path, root):
        raise ValueError("json-out path must stay inside memory_root")
    return path


def resolve_compare_roots(values: list[str]) -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()
    for value in values:
        root = Path(value).resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"compare root is not a directory: {root}")
        if root not in seen:
            seen.add(root)
            roots.append(root)
    return roots


def validate_scope_paths(root: Path, config: dict[str, Any], changed: list[str], removed: list[str]) -> tuple[list[str], list[str]]:
    excluded = config.get("_excluded_paths", config.get("excluded_folders", []))
    groups: list[list[str]] = []
    for field, values in (("changed", changed), ("removed", removed)):
        normalized: set[str] = set()
        for value in values:
            # Drive-relative Windows paths and '.' are not file paths, on any OS.
            if re.match(r"^[A-Za-z]:", value) or value.replace("\\", "/").strip("/") in {"", "."}:
                raise ValueError(f"{field} must be a root-relative file path: {value}")
            relative = validate_relative_path(value, field)
            candidate = resolve_unicode_path(root / relative, root)
            resolved = candidate.resolve()
            if not is_within(resolved, root) or path_is_excluded(relative, excluded) or path_is_excluded(normalize_rel(resolved, root), excluded):
                raise ValueError(f"{field} path is outside the managed scope: {value}")
            if candidate.is_symlink() and not candidate.exists():
                raise ValueError(f"{field} path is a dangling symlink: {value}")
            if field == "changed" and not candidate.is_file():
                raise ValueError(f"changed path must be an existing file: {value}")
            if field == "removed" and candidate.exists():
                raise ValueError(f"removed path must be absent: {value}")
            normalized.add(normalize_rel(candidate, root))
        groups.append(sorted(normalized))
    if set(groups[0]) & set(groups[1]):
        raise ValueError("a path cannot be both changed and removed")
    return groups[0], groups[1]


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    class SafeParser(argparse.ArgumentParser):
        def error(self, message):
            self.exit(2, "ERROR: invalid arguments\n")
    parser = SafeParser(description="Audit local Markdown and Obsidian links.")
    parser.add_argument("memory_root", help="Path to the memory root containing index.md.")
    parser.add_argument("--vault-root", help="Confirmed same-base vault boundary; never a neighboring base.")
    parser.add_argument("--index-exclude", action="append", default=[], metavar="GLOB", help="Exclude only index coverage, not link checks.")
    parser.add_argument("--config", help="Configuration file inside memory root.")
    parser.add_argument("--index", help="Index file relative to memory root (overrides config).")
    parser.add_argument("--changed", action="append", default=[], metavar="RELATIVE_PATH", help="Existing changed file inside root; repeatable. Enables local audit.")
    parser.add_argument("--removed", action="append", default=[], metavar="RELATIVE_PATH", help="Absent old file path inside root; repeatable. Enables local audit.")
    parser.add_argument(
        "--compare-root",
        action="append",
        default=[],
        metavar="PATH",
        help="Compare managed filenames with another root; repeatable.",
    )
    parser.add_argument("--check-urls", action="store_true", help="Check configured URL classes.")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON.")
    parser.add_argument("--json-out", help="Write the JSON report to this explicit path.")
    parser.add_argument(
        "--strict-exit",
        action="store_true",
        help="Exit with code 1 when strict problems are found.",
    )
    args = parser.parse_args(argv)

    root = Path(args.memory_root).resolve()
    if not root.exists() or not root.is_dir():
        print("ERROR: memory root is not a directory", file=sys.stderr)
        return 2
    try:
        config, config_path = load_config(root, args.config)
        index_name = (
            validate_relative_path(args.index, "index")
            if args.index
            else config.get("_index_path", "index.md")
        )
        compare_roots = resolve_compare_roots(args.compare_root)
        json_out = output_path_inside_root(args.json_out, root) if args.json_out else None
        changed, removed = validate_scope_paths(root, config, args.changed, args.removed)
    except ValueError as exc:
        message = "index must be inside memory root" if args.index and (".." in Path(args.index).parts or Path(args.index).is_absolute()) else "invalid configuration or scope paths"
        if "must stay inside" in str(exc) and message != "index must be inside memory root":
            message = "scope/config paths must stay inside memory_root"
        print("ERROR: " + message, file=sys.stderr)
        return 2

    try:
        result = audit(root, index_name, config, args.check_urls, compare_roots, changed, removed,
                       vault_root=Path(args.vault_root) if args.vault_root else None, index_exclude=args.index_exclude)
    except (ValueError, OSError) as exc:
        message = "memory root must be inside the vault root" if str(exc) == "memory root must be inside the vault root" else "unsafe path outside vault or unreadable input"
        print("ERROR: " + message, file=sys.stderr)
        return 2
    result["CONFIG_PATH"] = normalize_rel(config_path, root) if config_path else None
    rendered_json = json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True)
    if json_out:
        try:
            json_out.parent.mkdir(parents=True, exist_ok=True)
            json_out.write_text(rendered_json + "\n", encoding="utf-8")
        except OSError as exc:
            print("ERROR: cannot write JSON report", file=sys.stderr)
            return 2
    if args.json:
        print(rendered_json)
    else:
        render_text(result, args.check_urls)
    if args.strict_exit and result["STRICT_PROBLEM_COUNT"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
