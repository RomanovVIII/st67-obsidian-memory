#!/usr/bin/env python3
"""Cross-platform Markdown/Obsidian link audit for project memory roots."""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote


WIKI_EMBED_RE = re.compile(r"!\[\[([^\]]+)\]\]")
WIKI_LINK_RE = re.compile(r"(?<!!)\[\[([^\]]+)\]\]")
MD_ATTACHMENT_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
MD_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
TBD_RE = re.compile(r"TBD_[A-Za-z0-9_.-]+")
FENCED_CODE_RE = re.compile(r"(?s)```.*?```")
INLINE_CODE_RE = re.compile(r"`[^`\r\n]*`")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[/\\]")
ATX_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
SETEXT_HEADING_RE = re.compile(r"^\s{0,3}(?:=+|-+)\s*$")
BLOCK_REFERENCE_RE = re.compile(r"(?:^|\s)\^([A-Za-z0-9-]+)\s*$")


def strip_code(text: str) -> str:
    text = FENCED_CODE_RE.sub("", text)
    return INLINE_CODE_RE.sub("", text)


def normalize_unicode(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def normalize_rel(path: Path, root: Path) -> str:
    return normalize_unicode(path.relative_to(root).as_posix())


def safe_display(value: str) -> str:
    """Escape control characters before a value reaches a terminal or log."""
    return "".join(
        f"\\x{ord(char):02x}" if ord(char) < 32 or ord(char) == 127 else char
        for char in normalize_unicode(value)
    )


def line_finding(source: str, category: str, text: str, offset: int) -> str:
    line_number = text.count("\n", 0, offset) + 1
    return f"{safe_display(source)} -> {category}_LINE_{line_number}"


def path_reference_is_unsafe(value: str) -> bool:
    normalized = normalize_unicode(unquote(value.strip()).replace("\\", "/"))
    if not normalized:
        return False
    if normalized.startswith("/") or WINDOWS_ABSOLUTE_RE.match(normalized):
        return True
    return ".." in Path(normalized).parts


def wiki_reference_is_unsafe(raw: str) -> bool:
    reference = raw.split("|", 1)[0].strip()
    target = reference.split("#", 1)[0].strip()
    return bool(
        target
        and not SCHEME_RE.match(target)
        and path_reference_is_unsafe(target)
    )


def resolve_inside(candidate: Path, boundary: Path, message: str) -> Path:
    resolved = candidate.resolve()
    try:
        resolved.relative_to(boundary.resolve())
    except ValueError as exc:
        raise ValueError(message) from exc
    return resolved


def safe_file_paths(root: Path, pattern: str, boundary: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob(pattern):
        resolve_inside(path, boundary, "unsafe path outside vault")
        if path.is_file():
            files.append(path)
    return files


def resolve_wiki_target(raw: str) -> str | None:
    parsed = parse_wiki_reference(raw)
    if parsed is None:
        return None
    target, _fragment = parsed
    if not target:
        return None
    return wiki_target_path(target)


def parse_wiki_reference(raw: str) -> tuple[str, str | None] | None:
    """Return the normalized path and optional fragment before an alias."""
    reference = raw.split("|", 1)[0].strip()
    if not reference:
        return None
    target, separator, fragment = reference.partition("#")
    target = normalize_unicode(unquote(target).replace("\\", "/").lstrip("/"))
    if target and SCHEME_RE.match(target):
        return None
    normalized_fragment = normalize_unicode(unquote(fragment.strip())) if separator else None
    return target, normalized_fragment


def wiki_target_path(target: str) -> str:
    suffix = Path(target).suffix.lower()
    if not suffix:
        return f"{target}.md"
    return target


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


def resolve_markdown_target(raw: str, source: Path, vault_root: Path) -> Path | None:
    target = raw.strip()
    if not target or target.startswith("#") or SCHEME_RE.match(target):
        return None
    path_only = normalize_unicode(
        unquote(target.split("#", 1)[0].strip()).replace("\\", "/")
    )
    if not path_only:
        return None
    if path_reference_is_unsafe(path_only):
        raise ValueError("unsafe path outside vault")
    return resolve_unicode_path(source.parent / path_only, vault_root)


def wiki_candidates(
    raw: str,
    vault_files: set[str],
    source_file: str | None = None,
) -> list[str]:
    parsed = parse_wiki_reference(raw)
    if parsed is None:
        return []
    target, fragment = parsed
    if not target:
        return [source_file] if fragment and source_file in vault_files else []
    target = wiki_target_path(target)
    if target in vault_files:
        return [target]
    suffix = f"/{target}"
    return sorted(path for path in vault_files if path.endswith(suffix))


def is_binary_wiki_reference(raw: str) -> bool:
    parsed = parse_wiki_reference(raw)
    if parsed is None:
        return False
    target, _fragment = parsed
    return bool(target and Path(target).suffix.lower() not in {"", ".md"})


def normalized_anchor(value: str) -> str:
    return " ".join(normalize_unicode(value).casefold().split())


def markdown_anchors(path: Path) -> tuple[set[str], set[str]]:
    text = strip_code(path.read_text(encoding="utf-8", errors="replace"))
    lines = text.splitlines()
    headings: set[str] = set()
    blocks: set[str] = set()
    for index, line in enumerate(lines):
        match = ATX_HEADING_RE.match(line)
        if match:
            headings.add(normalized_anchor(match.group(1)))
        if index + 1 < len(lines) and line.strip() and SETEXT_HEADING_RE.match(
            lines[index + 1]
        ):
            headings.add(normalized_anchor(line.strip()))
        block_match = BLOCK_REFERENCE_RE.search(line)
        if block_match:
            blocks.add(normalized_anchor(block_match.group(1)))
    return headings, blocks


def wiki_fragment_exists(candidate: str, fragment: str | None, vault_root: Path) -> bool:
    if not fragment or Path(candidate).suffix.lower() != ".md":
        return True
    target_path = resolve_unicode_path(vault_root / candidate, vault_root)
    headings, blocks = markdown_anchors(target_path)
    if fragment.startswith("^"):
        return normalized_anchor(fragment[1:]) in blocks
    return normalized_anchor(fragment) in headings


def local_target(candidate: str, root: Path, vault_root: Path) -> str | None:
    try:
        resolved = resolve_unicode_path(vault_root / candidate, vault_root)
        return normalize_rel(resolved, root)
    except ValueError:
        return None


def collect_index_targets(
    index_path: Path,
    root: Path,
    vault_root: Path,
    vault_files: set[str],
) -> tuple[set[str], dict[str, int]]:
    if not index_path.exists():
        return set(), {}
    text = strip_code(index_path.read_text(encoding="utf-8", errors="replace"))
    targets: set[str] = set()
    target_lines: dict[str, int] = {}
    source_file = normalize_rel(index_path, vault_root)
    for match in WIKI_EMBED_RE.finditer(text):
        if wiki_reference_is_unsafe(match.group(1)):
            continue
        candidates = wiki_candidates(match.group(1), vault_files, source_file)
        if len(candidates) == 1:
            target = local_target(candidates[0], root, vault_root)
            if target:
                targets.add(target)
                target_lines.setdefault(target, text.count("\n", 0, match.start()) + 1)
    for match in WIKI_LINK_RE.finditer(text):
        if wiki_reference_is_unsafe(match.group(1)):
            continue
        candidates = wiki_candidates(match.group(1), vault_files, source_file)
        if len(candidates) == 1:
            target = local_target(candidates[0], root, vault_root)
            if target:
                targets.add(target)
                target_lines.setdefault(target, text.count("\n", 0, match.start()) + 1)
    for regex in (MD_ATTACHMENT_RE, MD_LINK_RE):
        for match in regex.finditer(text):
            try:
                resolved = resolve_markdown_target(
                    match.group(1), index_path, vault_root
                )
            except ValueError:
                continue
            if resolved and resolved.suffix.lower() == ".md":
                try:
                    target = normalize_rel(resolved, index_path.parent)
                except ValueError:
                    continue
                targets.add(target)
                target_lines.setdefault(target, text.count("\n", 0, match.start()) + 1)
    return targets, target_lines


def emit_section(name: str, values: list[str] | set[str]) -> int:
    ordered = sorted(values)
    print(f"{name}={len(ordered)}")
    for value in ordered:
        print(safe_display(value))
    return len(ordered)


def audit(
    root: Path,
    index_name: str,
    vault_root: Path | None = None,
    index_exclude: list[str] | None = None,
) -> dict[str, list[str] | int]:
    root = root.resolve()
    vault_root = (vault_root or root).resolve()
    try:
        root.relative_to(vault_root)
    except ValueError as exc:
        raise ValueError("memory root must be inside the vault root") from exc

    files = sorted(safe_file_paths(root, "*.md", vault_root))
    rel_files = [normalize_rel(path, root) for path in files]
    file_set = set(rel_files)
    index_exclude = [
        normalize_unicode(pattern.replace("\\", "/"))
        for pattern in (index_exclude or [])
    ]
    managed_file_set = {
        rel
        for rel in file_set
        if not any(fnmatch.fnmatchcase(rel, pattern) for pattern in index_exclude)
    }
    vault_markdown_files = {
        normalize_rel(path, vault_root)
        for path in safe_file_paths(vault_root, "*.md", vault_root)
    }
    vault_all_files = {
        normalize_rel(path, vault_root)
        for path in safe_file_paths(vault_root, "*", vault_root)
    }
    incoming = {rel: set() for rel in rel_files}

    wiki_broken: list[str] = []
    wiki_embed_broken: list[str] = []
    wiki_ambiguous: list[str] = []
    wiki_embed_ambiguous: list[str] = []
    md_broken: list[str] = []
    md_attachment_broken: list[str] = []
    tbd_refs: list[str] = []

    for path in files:
        rel_source = normalize_rel(path, root)
        vault_source = normalize_rel(path, vault_root)
        text = strip_code(path.read_text(encoding="utf-8", errors="replace"))

        for match in WIKI_EMBED_RE.finditer(text):
            raw = match.group(1)
            if wiki_reference_is_unsafe(raw):
                wiki_embed_broken.append(
                    line_finding(rel_source, "UNSAFE_WIKI_EMBED", text, match.start())
                )
                continue
            parsed = parse_wiki_reference(raw)
            if parsed is None:
                continue
            candidate_files = (
                vault_all_files if is_binary_wiki_reference(raw) else vault_markdown_files
            )
            candidates = wiki_candidates(raw, candidate_files, vault_source)
            if not candidates:
                wiki_embed_broken.append(
                    line_finding(rel_source, "BROKEN_WIKI_EMBED", text, match.start())
                )
            elif len(candidates) > 1:
                wiki_embed_ambiguous.append(
                    line_finding(
                        rel_source, "AMBIGUOUS_WIKI_EMBED", text, match.start()
                    )
                )
            else:
                _target, fragment = parsed
                if not wiki_fragment_exists(candidates[0], fragment, vault_root):
                    wiki_embed_broken.append(
                        line_finding(
                            rel_source, "BROKEN_WIKI_EMBED", text, match.start()
                        )
                    )
                    continue
                target = local_target(candidates[0], root, vault_root)
                if target in incoming:
                    incoming[target].add(rel_source)

        for match in WIKI_LINK_RE.finditer(text):
            raw = match.group(1)
            if wiki_reference_is_unsafe(raw):
                wiki_broken.append(
                    line_finding(rel_source, "UNSAFE_WIKILINK", text, match.start())
                )
                continue
            parsed = parse_wiki_reference(raw)
            if parsed is None:
                continue
            candidate_files = (
                vault_all_files if is_binary_wiki_reference(raw) else vault_markdown_files
            )
            candidates = wiki_candidates(raw, candidate_files, vault_source)
            if not candidates:
                wiki_broken.append(
                    line_finding(rel_source, "BROKEN_WIKILINK", text, match.start())
                )
            elif len(candidates) > 1:
                wiki_ambiguous.append(
                    line_finding(rel_source, "AMBIGUOUS_WIKILINK", text, match.start())
                )
            else:
                _target, fragment = parsed
                if not wiki_fragment_exists(candidates[0], fragment, vault_root):
                    wiki_broken.append(
                        line_finding(
                            rel_source, "BROKEN_WIKILINK", text, match.start()
                        )
                    )
                    continue
                target = local_target(candidates[0], root, vault_root)
                if target in incoming:
                    incoming[target].add(rel_source)

        for match in MD_ATTACHMENT_RE.finditer(text):
            raw = match.group(1)
            try:
                target_path = resolve_markdown_target(raw, path, vault_root)
            except ValueError:
                md_attachment_broken.append(
                    line_finding(
                        rel_source, "UNSAFE_MARKDOWN_ATTACHMENT", text, match.start()
                    )
                )
                continue
            if target_path and not target_path.exists():
                md_attachment_broken.append(
                    line_finding(
                        rel_source, "BROKEN_MARKDOWN_ATTACHMENT", text, match.start()
                    )
                )
            elif target_path and target_path.suffix.lower() == ".md":
                try:
                    target = normalize_rel(target_path, root)
                except ValueError:
                    target = None
                if target in incoming:
                    incoming[target].add(rel_source)

        for match in MD_LINK_RE.finditer(text):
            raw = match.group(1)
            try:
                target_path = resolve_markdown_target(raw, path, vault_root)
            except ValueError:
                md_broken.append(
                    line_finding(
                        rel_source, "UNSAFE_MARKDOWN_LINK", text, match.start()
                    )
                )
                continue
            if target_path and not target_path.exists():
                md_broken.append(
                    line_finding(
                        rel_source, "BROKEN_MARKDOWN_LINK", text, match.start()
                    )
                )
            elif target_path and target_path.suffix.lower() == ".md":
                try:
                    target = normalize_rel(target_path, root)
                except ValueError:
                    target = None
                if target in incoming:
                    incoming[target].add(rel_source)

        for match in TBD_RE.finditer(text):
            tbd_refs.append(
                line_finding(rel_source, "TBD_REFERENCE", text, match.start())
            )

    normalized_index_name = normalize_unicode(index_name.replace("\\", "/"))
    if path_reference_is_unsafe(normalized_index_name):
        raise ValueError("index must be inside memory root")
    try:
        index_path = resolve_unicode_path(root / normalized_index_name, root)
    except ValueError as exc:
        raise ValueError("index must be inside memory root") from exc
    index_rel = normalize_rel(index_path, root)
    index_targets, index_target_lines = collect_index_targets(
        index_path,
        root,
        vault_root,
        vault_markdown_files,
    )
    missing_from_index = sorted(
        safe_display(value) for value in managed_file_set - index_targets
    )
    stale_index = sorted(
        f"{safe_display(index_rel)} -> STALE_INDEX_ENTRY_LINE_"
        f"{index_target_lines[target]}"
        for target in index_targets - file_set
    )
    zero_incoming = sorted(
        safe_display(rel)
        for rel, refs in incoming.items()
        if not refs and rel != index_rel
    )
    weak_incoming = sorted(
        safe_display(rel)
        for rel, refs in incoming.items()
        if rel not in {index_rel, "log.md"} and not (refs - {index_rel, "log.md"})
    )

    return {
        "MD_FILES": len(rel_files),
        "BROKEN_WIKI_LINKS": wiki_broken,
        "BROKEN_WIKI_EMBEDS": wiki_embed_broken,
        "AMBIGUOUS_WIKI_LINKS": sorted(wiki_ambiguous),
        "AMBIGUOUS_WIKI_EMBEDS": sorted(wiki_embed_ambiguous),
        "BROKEN_MARKDOWN_LINKS": md_broken,
        "BROKEN_MARKDOWN_ATTACHMENTS": md_attachment_broken,
        "MISSING_FROM_INDEX": missing_from_index,
        "STALE_INDEX_ENTRIES": stale_index,
        "ZERO_INCOMING_EXCEPT_INDEX": zero_incoming,
        "ONLY_INDEX_OR_LOG_INCOMING": weak_incoming,
        "TBD_REFERENCES": tbd_refs,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Audit local Markdown and Obsidian links.")
    parser.add_argument("memory_root", help="Path to the memory root containing index.md.")
    parser.add_argument("--index", default="index.md", help="Index file relative to memory root.")
    parser.add_argument(
        "--vault-root",
        help="Obsidian vault root. Defaults to the memory root for a standalone vault.",
    )
    parser.add_argument(
        "--index-exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="Glob excluded from index coverage only; repeat for multiple patterns.",
    )
    parser.add_argument(
        "--strict-exit",
        action="store_true",
        help="Exit non-zero when strict link/index problems are found.",
    )
    args = parser.parse_args(argv)

    root = Path(args.memory_root)
    if not root.exists() or not root.is_dir():
        print("ERROR: memory root is not a directory", file=sys.stderr)
        return 2
    vault_root = Path(args.vault_root) if args.vault_root else root
    if not vault_root.exists() or not vault_root.is_dir():
        print("ERROR: vault root is not a directory", file=sys.stderr)
        return 2

    try:
        result = audit(root, args.index, vault_root, args.index_exclude)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"MD_FILES={result['MD_FILES']}")
    strict_count = 0
    for name in (
        "BROKEN_WIKI_LINKS",
        "BROKEN_WIKI_EMBEDS",
        "AMBIGUOUS_WIKI_LINKS",
        "AMBIGUOUS_WIKI_EMBEDS",
        "BROKEN_MARKDOWN_LINKS",
        "BROKEN_MARKDOWN_ATTACHMENTS",
        "MISSING_FROM_INDEX",
        "STALE_INDEX_ENTRIES",
    ):
        strict_count += emit_section(name, result[name])
    emit_section("ZERO_INCOMING_EXCEPT_INDEX", result["ZERO_INCOMING_EXCEPT_INDEX"])
    emit_section("ONLY_INDEX_OR_LOG_INCOMING", result["ONLY_INDEX_OR_LOG_INCOMING"])
    strict_count += emit_section("TBD_REFERENCES", result["TBD_REFERENCES"])

    if args.strict_exit and strict_count:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
