"""Read-only naming-v1 validation; stdlib, Python 3.9+."""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

TYPES = frozenset('IDX CFG LOG TODO HOST DEV APP SRV NET STO PLN CPLD TRB CTRB DEC RSR RPT RUL ATT RAW TMP'.split())
SEQUENTIAL = TYPES - {'IDX', 'CFG', 'TMP'}
DATED = {'PLN', 'CPLD', 'TRB', 'CTRB', 'DEC'}
NAMESPACE = re.compile(r'[A-Z][A-Z0-9]{1,15}\Z')
IDENTITY = re.compile(r'([A-Z]{2,5})_([A-Z][A-Z0-9]{1,15})-([0-9]{4,})\Z')
LEGACY_IDENTITY = re.compile(r'([A-Z]{2,5})-([0-9]{4,})\Z')
NUMBERED = re.compile(r'([A-Z]{2,5})_([A-Z][A-Z0-9]{1,15})-([0-9]{4,})_(.+)\Z')


def key(value: str) -> str:
    return unicodedata.normalize('NFC', value).casefold()


def validate_profile(config: dict[str, Any]) -> None:
    namespace = config.get('file_namespace')
    if not isinstance(namespace, str) or not NAMESPACE.fullmatch(namespace):
        raise ValueError('invalid config: file_namespace must be 2-16 uppercase ASCII letters/digits, starting with a letter')
    if config.get('naming_profile') != 'naming-v1':
        raise ValueError('invalid config: naming_profile must be naming-v1')
    for field in ('base_id', 'allocation_owner'):
        if not isinstance(config.get(field), str) or not config[field].strip():
            raise ValueError('invalid config: ' + field + ' must be non-empty')
    if 'parent_base_id' in config and (not isinstance(config['parent_base_id'], str) or not config['parent_base_id'].strip()):
        raise ValueError('invalid config: parent_base_id must be non-empty when present')
    if config.get('parent_base_id') == config.get('base_id'):
        raise ValueError('invalid config: a base cannot be its own parent')
    counters = config.get('last_issued')
    if not isinstance(counters, dict) or any(t not in SEQUENTIAL or type(n) is not int or n < 0 for t, n in counters.items()):
        raise ValueError('invalid config: last_issued must contain known sequential types and nonnegative integer counters')


def frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0] != '---':
        return {}
    result: dict[str, str] = {}
    for line in lines[1:]:
        if line == '---':
            break
        match = re.fullmatch(r'([a-z_]+):\s*(.*?)\s*', line)
        if match:
            result[match[1]] = match[2].strip('\"\'')
    return result


def valid_topic(value: str) -> bool:
    return bool(value) and any(c.isalnum() for c in value) and all(c.isalnum() or unicodedata.category(c).startswith('M') or c in '_-' for c in value)


def filename_identity(path: Path, namespace: str) -> tuple[str | None, str | None]:
    """Return stable ID and diagnostic category; values are not diagnostics."""
    normalized = Path(unicodedata.normalize('NFC', path.name))
    name, stem, extension = normalized.name, normalized.stem, normalized.suffix
    if name in ('IDX_' + namespace + '.md', 'CFG_' + namespace + '.json', 'TODO_' + namespace + '.md'):
        return stem, None
    if stem.startswith('TMP_'):
        match = re.fullmatch(r'TMP_([A-Z][A-Z0-9]{1,15})_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})_(.+)', stem)
        if match and match[1] == namespace and extension and valid_topic(match[3]):
            return 'TMP_' + match[1] + '_' + match[2], None
        return None, 'INVALID_FILENAME'
    match = NUMBERED.fullmatch(stem)
    if not match or match[1] not in SEQUENTIAL or match[2] != namespace or int(match[3]) < 1:
        return None, 'INVALID_FILENAME'
    typ, base, number, rest = match.groups()
    identity = typ + '_' + base + '-' + number
    if number != str(int(number)).zfill(4):
        return identity, 'NONCANONICAL_SEQUENCE_NUMBER'
    try:
        if typ == 'LOG':
            datetime.strptime(rest, '%Y-%m')
            if not re.fullmatch(r'\d{4}-\d{2}', rest):
                raise ValueError()
        elif typ in DATED:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}_.+', rest):
                raise ValueError()
            datetime.strptime(rest[:16], '%Y-%m-%d_%H-%M')
            if not valid_topic(rest[17:]):
                raise ValueError()
        elif typ == 'RPT':
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}_.+', rest):
                raise ValueError()
            datetime.strptime(rest[:10], '%Y-%m-%d')
            if not valid_topic(rest[11:]):
                raise ValueError()
        elif not valid_topic(rest):
            raise ValueError()
    except ValueError:
        return identity, 'INVALID_FILENAME'
    if not extension or (typ not in {'ATT', 'RAW'} and extension != '.md'):
        return identity, 'INVALID_EXTENSION'
    return identity, None


def audit_names(root: Path, files: list[Path], config: dict[str, Any], touched: set[str] | None = None,
                text_reader=None) -> list[dict[str, str]]:
    if config.get('naming_profile') != 'naming-v1':
        return []
    namespace = config['file_namespace']
    counters = config['last_issued']
    findings: list[dict[str, str]] = []
    records: dict[str, list[str]] = {}
    maxima: dict[str, tuple[int, str]] = {}
    relevant_types: set[str] = set()
    touched_keys = {key(s) for s in touched} if touched is not None else None

    def relevant(relative):
        return touched_keys is None or key(relative) in touched_keys

    def add(kind, source):
        findings.append(dict(kind=kind, source=source, target='', message='', **{'class': ''}))

    for path in files:
        relative = path.relative_to(root).as_posix()
        identity, error = filename_identity(path, namespace)
        if error and relevant(relative):
            add(error, relative)
        if identity:
            records.setdefault(key(identity), []).append(relative)
            match = IDENTITY.fullmatch(identity)
            if match:
                typ, _, number = match.groups()
                if relevant(relative):
                    relevant_types.add(typ)
                if int(number) > maxima.get(typ, (0, ''))[0]:
                    maxima[typ] = int(number), relative
        if path.suffix != '.md':
            continue
        # Only IDs are read in unrelated documents, to find collisions/counter maxima.
        text = path.read_text(encoding='utf-8', errors='replace')
        metadata = frontmatter(text)
        if identity and IDENTITY.fullmatch(identity) and not identity.startswith(('ATT_', 'RAW_')) and relevant(relative):
            if metadata.get('id') != identity:
                add('DOCUMENT_ID_MISMATCH', relative)
        if identity and identity.startswith(('CPLD_', 'CTRB_')):
            origin = metadata.get('source_id', '')
            source_match = IDENTITY.fullmatch(origin) or LEGACY_IDENTITY.fullmatch(origin)
            required = 'PLN' if identity.startswith('CPLD_') else 'TRB'
            origin_number = int(source_match.groups()[-1]) if source_match else 0
            valid_origin = bool(source_match and source_match[1] == required and origin_number > 0
                                and source_match.groups()[-1] == str(origin_number).zfill(4)
                                and (not IDENTITY.fullmatch(origin) or source_match[2] == namespace))
            if not valid_origin:
                if relevant(relative):
                    add('INVALID_SOURCE_ID', relative)
            else:
                if relevant(relative):
                    relevant_types.add(required)
                if origin_number > maxima.get(required, (0, ''))[0]:
                    maxima[required] = origin_number, relative
        if path.name == 'TODO_' + namespace + '.md':
            active = text_reader(text) if text_reader else text
            for match in re.finditer(r'(?m)^\s*(?:#{1,6}\s+|[-*]\s+(?:\[[ xX]\]\s+)?)(TODO_' + re.escape(namespace) + r'-([0-9]{4,}))(?=\s*(?:[:—|]|$))', active):
                number = int(match[2])
                if relevant(relative) and (number < 1 or match[2] != str(number).zfill(4)):
                    add('NONCANONICAL_SEQUENCE_NUMBER', relative)
                records.setdefault(key('TODO_' + namespace + '-' + str(number).zfill(4)), []).append(relative)
                if relevant(relative):
                    relevant_types.add('TODO')
                if number > maxima.get('TODO', (0, ''))[0]:
                    maxima['TODO'] = number, relative
    for paths in records.values():
        if len(paths) > 1 and any(relevant(p) for p in paths):
            add('DUPLICATE_DOCUMENT_ID', next(p for p in paths if relevant(p)))
    for typ, (number, relative) in maxima.items():
        if counters.get(typ, 0) < number and (touched is None or typ in relevant_types or any(Path(p).name.startswith('CFG_') for p in touched)):
            add('COUNTER_BELOW_ISSUED', relative)
    return findings
