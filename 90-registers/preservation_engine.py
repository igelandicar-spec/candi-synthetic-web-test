"""Controlled V3 Preservation rebuild and recovery engine.

Adapted from the independently accepted ANDI INT-D01 synthetic mechanism.
The publication/recovery model is unchanged: an exclusive sibling lock, a
journaled before/after generation, declared unique publication and rollback
temporary paths, byte verification, and refusal without deletion when residue
is unowned.  V3 record bodies and authoritative relationships are inputs, not
generated knowledge.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import sys

ACT = '90-registers/ACTIVITY_STATE.json'
REGISTER = '90-registers/CANONICAL_RECORD_REGISTER.json'
MACHINE = '96-machine-tree/MACHINE-TREE.json'
RETRIEVAL = '96-machine-tree/RETRIEVAL-INDEX.json'
SOURCE = '90-registers/SOURCE_INVENTORY.json'
MISSING = '90-registers/MISSING-REFERENCES.json'
HOT_JSON = '00-kernel/HOT-FILES.json'
HOT_MD = '00-kernel/HOT-FILES.md'
SYSTEM_MAP = '00-kernel/SYSTEM-MAP.md'
PROJECT_TREE = '95-human-archive/PROJECT-TREE.md'
MARKER = '00-kernel/KERNEL.md'
BANDS = ('HOT', 'WARM', 'COOL', 'COLD')
MEANINGFUL = {'work_session', 'decision', 'test', 'test_result', 'evidence', 'edit',
              'material_edit', 'reactivation', 'relationship',
              'conflict_resolution', 'measurement', 'discovery'}
CLERICAL = {'housekeeping', 'rename', 'formatting', 'sync',
            'archive_manufacture', 'rebuild', 'metadata', 'read_only'}
RID = re.compile(r'CAN-[A-Z]+-[0-9]{3,}')
PREAMBLE = re.compile(rb'<!-- ([A-Z_]+): ([^\r\n]*?) -->\r?\n')
AUTHORING_RID = re.compile(r'CAN-(GOV|CAR|BM|LAB)-([0-9]{3,})')
AUTHORING_ROOTS = {'GOV': '01-governance', 'CAR': '10-andi-car',
                   'BM': '20-storage-benchmark', 'LAB': '30-lab-mk1'}
SRC_RID = re.compile(r'SRC-[0-9]{3,}')
EVIDENCE_DIR = '80-original-evidence'


class Invalid(ValueError):
    pass


def need(ok, message):
    if not ok:
        raise Invalid(message)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=False, indent=2,
                       allow_nan=False) + '\n').encode('utf-8')


def decode(data):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'Duplicate JSON key: ' + key)
            result[key] = value
        return result
    try:
        return json.loads(data.decode('utf-8-sig'), object_pairs_hook=pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(Invalid(value)))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Invalid('Malformed UTF-8 JSON') from exc


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe(root, rel):
    need(isinstance(rel, str) and rel and '\\' not in rel and ':' not in rel,
         'Invalid relative path')
    parts = rel.split('/')
    need(all(part not in ('', '.', '..') and not part.endswith((' ', '.')) and
             not re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', part)
             for part in parts), 'Unsafe path: ' + rel)
    path = root.joinpath(*parts)
    for item in [path, *path.parents]:
        if item == root:
            break
        if item.exists() or item.is_symlink():
            info = item.lstat()
            need(not stat.S_ISLNK(info.st_mode) and
                 not (getattr(info, 'st_file_attributes', 0) & 1024),
                 'Link/reparse path: ' + rel)
            need(not item.is_file() or info.st_nlink == 1,
                 'Hardlinked file: ' + rel)
    need(path.resolve().is_relative_to(root), 'Path escapes root')
    return path


def root_guard(root):
    root = Path(root).absolute()
    need(root.exists() and root.is_dir(), 'V3 root does not exist')
    for item in [root, *root.parents]:
        info = item.lstat()
        need(not item.is_symlink() and
             not (getattr(info, 'st_file_attributes', 0) & 1024),
             'Root/ancestor link not allowed')
    marker = safe(root, MARKER)
    need(marker.is_file() and
         b'# ANDI \xe2\x80\x94 BOUNDED UNIVERSAL GROUNDING KERNEL' in marker.read_bytes(),
         'Refusing root without frozen-V3 kernel marker')
    for rel in (ACT, REGISTER, MACHINE, SOURCE):
        need(safe(root, rel).is_file(), 'Required V3 input missing: ' + rel)
    return root


def snapshot(root):
    result, aliases = {}, set()
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs.sort()
        for name in sorted(dirs + files):
            rel = (Path(base) / name).relative_to(root).as_posix()
            need(rel.casefold() not in aliases, 'Case-aliased path')
            aliases.add(rel.casefold())
            path = safe(root, rel)
            need(path.is_dir() or path.is_file(), 'Special file')
            if path.is_file():
                result[rel] = path.read_bytes()
    return result


def stamp(value):
    need(isinstance(value, str) and re.fullmatch(
        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})', value),
        'Full timezone-aware timestamp required')
    try:
        return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(dt.timezone.utc)
    except ValueError as exc:
        raise Invalid('Invalid timestamp') from exc


def header(data):
    try:
        data.decode('utf-8-sig')
    except UnicodeError as exc:
        raise Invalid('Record not UTF-8') from exc
    offset = 3 if data.startswith(b'\xef\xbb\xbf') else 0
    fields, spans = {}, {}
    while match := PREAMBLE.match(data, offset):
        key, value = match[1].decode(), match[2].decode('utf-8')
        need(key not in fields, 'Duplicate preamble field: ' + key)
        fields[key], spans[key] = value, match.span(2)
        offset = match.end()
    need({'STABLE_ID', 'AUTHORITY', 'ACTIVITY'} <= set(fields),
         'Malformed/missing V3 preamble field')
    need(RID.fullmatch(fields['STABLE_ID']), 'Invalid stable ID')
    need(fields['ACTIVITY'] in BANDS, 'Invalid activity band')
    need(data[offset:].strip(), 'Record needs body')
    return fields, spans, offset


def calculate(act, ids, as_of=None):
    algorithm = dict(act.get('algorithm', {}))
    n = algorithm.get('configurable_N')
    need(type(n) is int and n > 0, 'Invalid activity N')
    half = algorithm.get('half_life_days', 30)
    need(type(half) in (int, float) and math.isfinite(half) and half > 0,
         'Invalid half-life')
    reference = as_of or algorithm.get('reference_date')
    need(reference is not None, 'Explicit as-of/reference date required')
    now = stamp(reference)
    seen, eligible = set(), []
    for event in act.get('event_log', []):
        need(isinstance(event, dict), 'Event must be object')
        event_id = event.get('event_id')
        need(isinstance(event_id, str) and re.fullmatch(r'ACT-[0-9]+', event_id) and
             event_id not in seen, 'Missing/duplicate event identity')
        seen.add(event_id)
        when = stamp(event.get('timestamp'))
        targets = event.get('affected_records')
        need(isinstance(targets, list) and
             all(isinstance(rid, str) and rid in ids for rid in targets),
             'Invalid event target')
        event_type = event.get('type')
        event_class = event.get('event_class', 'meaningful')
        if event_class == 'meaningful':
            need(event_type in MEANINGFUL, 'Unknown meaningful event type')
            if when <= now:
                eligible.append((when, event_id, event))
        else:
            need(event_class in ('clerical', 'maintenance') and event_type in CLERICAL,
                 'Event class/type mismatch')
    eligible.sort(key=lambda row: (row[0], row[1]))
    weights = {rid: 0.0 for rid in ids}
    counts = {rid: 0 for rid in ids}
    latest, event_ids = {}, {rid: [] for rid in ids}
    for when, event_id, event in eligible:
        weight = 2 ** (-(now.date() - when.date()).days / half)
        need(weight > 0, 'Decay underflow: refuse silent loss of heated record')
        for rid in set(event['affected_records']):
            weights[rid] += weight
            counts[rid] += 1
            latest[rid] = max(latest.get(rid, when), when)
            event_ids[rid].append(event_id)
    ranked = sorted(latest, key=lambda rid: (-weights[rid], -latest[rid].timestamp(), rid))
    bands = {rid: 'COLD' for rid in sorted(ids)}
    for index, rid in enumerate(ranked):
        bands[rid] = BANDS[min(index // n, 3)]
    return {'as_of': now.isoformat(), 'policy': 'exponential',
            'half_life_days': half, 'ranking': ranked, 'bands': bands,
            'scores': weights, 'event_counts': counts,
            'latest': {rid: value.isoformat() for rid, value in latest.items()},
            'event_ids': event_ids}


def discover_records(files, register):
    records = {}
    entries = register.get('records')
    need(isinstance(entries, list) and entries, 'Invalid canonical register')
    for entry in entries:
        need(isinstance(entry, dict), 'Invalid canonical register entry')
        rid, path = entry.get('id'), entry.get('path')
        need(isinstance(rid, str) and RID.fullmatch(rid) and rid not in records,
             'Duplicate/invalid register ID')
        need(isinstance(path, str) and path in files, 'Missing canonical path: ' + str(path))
        fields, spans, offset = header(files[path])
        need(fields['STABLE_ID'] == rid, 'Register/header identity mismatch: ' + rid)
        records[rid] = {'entry': entry, 'path': path, 'fields': fields,
                        'spans': spans, 'offset': offset, 'data': files[path]}
    need(register.get('total') == len(records), 'Canonical register total mismatch')
    return records


def prepare_addition(files, request, as_of=None):
    """Translate one strict transient request into GOLDEN authoritative inputs."""
    required = {'schema', 'stable_id', 'path', 'title', 'type', 'record_type',
                'authority', 'status', 'body', 'source_ids', 'projects',
                'human_summary', 'note', 'relationships', 'activity'}
    need(isinstance(request, dict) and set(request) == required,
         'Authoring request has missing/unknown fields')
    need(type(request['schema']) is int and request['schema'] == 1,
         'Unsupported authoring request schema')

    register, machine, act, sources = (decode(files[path]) for path in
                                       (REGISTER, MACHINE, ACT, SOURCE))
    entries = register.get('records')
    need(isinstance(entries, list) and entries, 'Invalid canonical register')
    rid, rel = request['stable_id'], request['path']
    match = AUTHORING_RID.fullmatch(rid) if isinstance(rid, str) else None
    need(match is not None, 'Invalid authoring stable ID')
    need(rid not in {entry.get('id') for entry in entries if isinstance(entry, dict)},
         'Stable ID already exists')
    prefix, number = match.group(1), int(match.group(2))
    used = [int(found.group(2)) for entry in entries
            if isinstance(entry, dict) and isinstance(entry.get('id'), str)
            and (found := AUTHORING_RID.fullmatch(entry['id']))
            and found.group(1) == prefix]
    need(number == max(used, default=0) + 1,
         'Stable ID is not the next sequential ID for its prefix')

    need(isinstance(rel, str) and '\\' not in rel and ':' not in rel,
         'Invalid canonical path')
    parts = rel.split('/')
    need(len(parts) >= 2 and parts[0] == AUTHORING_ROOTS[prefix] and rel.endswith('.md') and
         all(part not in ('', '.', '..') and not part.endswith((' ', '.')) and
             not re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', part)
             for part in parts),
         'Canonical path does not match the stable-ID project prefix')
    need(rel.casefold() not in {path.casefold() for path in files},
         'Canonical path already exists')

    def text(name):
        value = request[name]
        need(isinstance(value, str) and value.strip() == value and value and
             '\r' not in value and '\n' not in value,
             'Invalid authoring text field: ' + name)
        return value

    title, record_type = text('title'), text('record_type')
    record_kind = text('type')
    authority, status = request['authority'], request['status']
    need(isinstance(authority, str) and authority in {'PROVISIONAL', 'ESTABLISHED'},
         'New record authority must be PROVISIONAL or ESTABLISHED')
    need(isinstance(status, str) and status == 'UNRECONCILED',
         'New record must start UNRECONCILED')
    body = request['body']
    need(isinstance(body, str), 'Record body must be text')
    try:
        body_bytes = body.encode('utf-8')
    except UnicodeError as exc:
        raise Invalid('Record body is not valid UTF-8 text') from exc
    need(not body.startswith('\ufeff') and body_bytes.lstrip().startswith(b'# ') and
         body_bytes.strip(), 'Record body needs a Markdown heading and content')

    source_ids = request['source_ids']
    need(isinstance(source_ids, list) and source_ids and
         all(isinstance(sid, str) and re.fullmatch(r'SRC-[0-9]+', sid) for sid in source_ids) and
         len(source_ids) == len(set(source_ids)), 'Invalid/duplicate source identity')
    inventory_ids = [row.get('inv_id') for row in sources if isinstance(row, dict)]
    need(len(inventory_ids) == len(set(inventory_ids)), 'Duplicate source inventory identity')
    need(set(source_ids) <= set(inventory_ids),
         'Canonical record references unknown source identity')

    projects = request['projects']
    need(isinstance(projects, list) and projects and
         all(isinstance(project, str) and re.fullmatch(r'[A-Z][A-Z0-9_]*', project)
             for project in projects) and len(projects) == len(set(projects)),
         'Invalid/duplicate project identity')
    human_summary, note = text('human_summary'), text('note')

    relationships = request['relationships']
    need(isinstance(relationships, list), 'Relationships must be a list')
    known_ids = {entry['id'] for entry in entries} | {rid}
    existing_edges = {(edge.get('from'), edge.get('to'), edge.get('type'))
                      for edge in machine.get('relationships', []) if isinstance(edge, dict)}
    requested_edges = set()
    for edge in relationships:
        need(isinstance(edge, dict) and set(edge) == {'from', 'to', 'type'},
             'Invalid relationship shape')
        start, end, kind = edge['from'], edge['to'], edge['type']
        need(start in known_ids and end in known_ids and start != end and
             isinstance(kind, str) and re.fullmatch(r'[a-z][a-z0-9_]*', kind),
             'Invalid relationship endpoint/type')
        need(rid in (start, end), 'Authored relationship must involve the new record')
        key = (start, end, kind)
        need(key not in existing_edges and key not in requested_edges,
             'Duplicate relationship')
        requested_edges.add(key)
        need(kind != 'supersedes',
             'Supersession requires the separate two-record maintenance procedure')

    activity = request['activity']
    need(isinstance(activity, dict) and set(activity) == {'timestamp', 'type', 'description'},
         'Invalid activity declaration')
    event_type = activity['type']
    need(isinstance(event_type, str) and event_type in MEANINGFUL,
         'New record requires a meaningful activity type')
    description = activity['description']
    need(isinstance(description, str) and description.strip() == description and description,
         'New record requires an activity description')
    when = stamp(activity['timestamp'])
    reference = as_of or act.get('algorithm', {}).get('reference_date')
    need(reference is not None and when <= stamp(reference),
         'Activity timestamp is later than the rebuild as-of')
    event_numbers = []
    for event in act.get('event_log', []):
        event_id = event.get('event_id') if isinstance(event, dict) else None
        need(isinstance(event_id, str) and re.fullmatch(r'ACT-[0-9]+', event_id),
             'Invalid existing activity identity')
        event_numbers.append(int(event_id.split('-')[1]))
    event_id = f'ACT-{max(event_numbers, default=0) + 1:03d}'

    record = (f'<!-- STABLE_ID: {rid} -->\n'
              f'<!-- SOURCE: {", ".join(source_ids)} -->\n'
              f'<!-- AUTHORITY: {authority} -->\n'
              '<!-- STATUS: UNRECONCILED -->\n'
              '<!-- ACTIVITY: COLD -->\n').encode('utf-8') + body_bytes
    header(record)
    entry = {'id': rid, 'title': title, 'type': record_kind,
             'record_type': record_type, 'authority': authority,
             'status': 'UNRECONCILED', 'path': rel,
             'actual_bytes': len(record), 'original_bytes': None,
             'source_ids': list(source_ids), 'activity_band': 'COLD'}
    node = {'id': rid, 'title': title, 'type': record_kind,
            'authority': authority, 'status': 'UNRECONCILED',
            'record_type': record_type, 'note': note,
            'source_ids': list(source_ids), 'original_source_bytes': None,
            'projects': list(projects), 'path': rel,
            'human_summary': human_summary,
            'actual_manufactured_bytes': len(record), 'activity_band': 'COLD'}
    register['records'].append(entry)
    register['total'] = len(register['records'])
    need(isinstance(machine.get('nodes'), list) and
         isinstance(machine.get('relationships'), list), 'Invalid machine tree')
    machine['nodes'].append(node)
    machine['relationships'].extend(relationships)
    act.setdefault('event_log', []).append({
        'event_id': event_id, 'timestamp': activity['timestamp'],
        'type': event_type, 'description': description,
        'affected_records': [rid], 'affected_branches': [parts[0]]})
    return {rel: record, REGISTER: encode(register), MACHINE: encode(machine), ACT: encode(act)}


def build(files, as_of=None):
    register, machine, act, sources = (decode(files[path]) for path in
                                        (REGISTER, MACHINE, ACT, SOURCE))
    records = discover_records(files, register)
    ids = set(records)
    nodes = machine.get('nodes')
    relationships = machine.get('relationships')
    need(isinstance(nodes, list) and isinstance(relationships, list), 'Invalid machine tree')
    node_map = {node.get('id'): node for node in nodes if isinstance(node, dict)}
    need(set(node_map) == ids and len(node_map) == len(nodes), 'Machine-tree node identity mismatch')
    edges = set()
    supersedes = set()
    for edge in relationships:
        need(isinstance(edge, dict) and set(edge) == {'from', 'to', 'type'},
             'Invalid relationship shape')
        start, end, kind = edge['from'], edge['to'], edge['type']
        need(start in ids and end in ids and start != end and
             isinstance(kind, str) and kind, 'Invalid relationship endpoint/type')
        key = (start, end, kind)
        need(key not in edges, 'Duplicate relationship')
        edges.add(key)
        if kind == 'supersedes':
            supersedes.add((start, end))
    declared_supersedes = set()
    declared_superseded_by = set()
    for rid, record in records.items():
        for target in RID.findall(record['fields'].get('SUPERSEDES', '')):
            need(target in ids and target != rid, 'Invalid SUPERSEDES header identity')
            declared_supersedes.add((rid, target))
        for successor in RID.findall(record['fields'].get('SUPERSEDED_BY', '')):
            need(successor in ids and successor != rid, 'Invalid SUPERSEDED_BY header identity')
            declared_superseded_by.add((successor, rid))
    need(supersedes == declared_supersedes == declared_superseded_by,
         'Supersession relationship/header mismatch')
    for successor, superseded in supersedes:
        need(records[superseded]['entry'].get('status') == 'SUPERSEDED' and
             node_map[superseded].get('status') == 'SUPERSEDED',
             'Superseded record status mismatch: ' + superseded)
    computed = calculate(act, ids, as_of)
    outputs, patched_records = {}, {}
    for rid, record in records.items():
        data, start = record['data'], record['offset']
        left, right = record['spans']['ACTIVITY']
        patched = data[:left] + computed['bands'][rid].encode() + data[right:]
        new_offset = header(patched)[2]
        need(patched[new_offset:] == data[start:], 'Semantic body changed during rebuild: ' + rid)
        outputs[record['path']] = patched
        patched_records[rid] = patched

    for entry in register['records']:
        rid = entry['id']
        entry['activity_band'] = computed['bands'][rid]
        entry['actual_bytes'] = len(patched_records[rid])
    register['activity_source'] = (ACT + ' — exponential 30-day time decay; '
                                   'activity is guidance only, independent of authority/CIF/retention')
    outputs[REGISTER] = encode(register)

    for node in nodes:
        rid = node['id']
        node['activity_band'] = computed['bands'][rid]
        node['actual_manufactured_bytes'] = len(patched_records[rid])
    machine['node_count'] = len(nodes)
    machine['relationship_count'] = len(relationships)
    machine['activity_source'] = register['activity_source']
    outputs[MACHINE] = encode(machine)

    old_retrieval = decode(files[RETRIEVAL]) if RETRIEVAL in files else {
        'index': 'ANDI_RETRIEVAL_INDEX', 'version': '3.0',
        'generated': '2026-09-21',
        'status': 'INTERIM / REVERSIBLE / NON-CANDIDATE',
        'size_summary': {
            'note': ('Most records are compact pointers/summaries. Full originals via '
                     '80-original-evidence/ provenance.')
        }
    }
    entries = []
    for node in nodes:
        rid = node['id']
        source = records[rid]['entry']
        entries.append({
            'id': rid, 'title': source['title'],
            'activity_band': computed['bands'][rid],
            'authority': source['authority'], 'status': source['status'],
            'record_type': source['record_type'], 'path': source['path'],
            'actual_bytes': len(patched_records[rid]),
            'original_bytes': source.get('original_bytes'),
            'projects': node.get('projects', []),
            'summary': node.get('human_summary', ''),
            'source_ids': source.get('source_ids', [])
        })
    old_retrieval['entries'] = entries
    old_retrieval['total_records'] = len(ids)
    old_retrieval['activity_source'] = register['activity_source']
    old_retrieval.setdefault('size_summary', {})['total_manufactured_bytes'] = sum(
        len(patched_records[rid]) for rid in ids)
    old_retrieval['size_summary']['total_original_bytes'] = sum(
        entry.get('original_bytes') or 0 for entry in register['records'])
    outputs[RETRIEVAL] = encode(old_retrieval)

    algorithm = act.setdefault('algorithm', {})
    algorithm.update({'purpose': 'current_work_guidance', 'authority_independent': True,
                      'retention_independent': True, 'cooling': 'exponential',
                      'half_life_days': 30, 'reference_date': computed['as_of']})
    weights = {}
    for rid in computed['ranking']:
        weights[rid] = {'event_count': computed['event_counts'][rid],
                        'decayed_score': computed['scores'][rid],
                        'latest': computed['latest'][rid],
                        'events': computed['event_ids'][rid]}
    branch_hottest = {}
    for node in nodes:
        for project in node.get('projects', []):
            old = branch_hottest.get(project, 'COLD')
            branch_hottest[project] = BANDS[min(BANDS.index(old), BANDS.index(computed['bands'][node['id']]))]
    act['derived_concentration_ranking'] = {
        'computation_note': '30-day exponential time decay; deterministic UTC calendar-day interpretation.',
        'as_of': computed['as_of'], 'weights': weights,
        'ranked_list': [{'rank': index + 1, 'id': rid,
                         'score': computed['scores'][rid],
                         'event_count': computed['event_counts'][rid],
                         'latest': computed['latest'][rid]}
                        for index, rid in enumerate(computed['ranking'])],
        'band_assignments': {band: [rid for rid in sorted(ids)
                                   if computed['bands'][rid] == band] for band in BANDS},
        'branch_hottest': branch_hottest}
    outputs[ACT] = encode(act)

    lookup = {entry['id']: entry for entry in register['records']}
    hot_json = {'index': 'HOT_FILES_INDEX', 'version': '3.1',
                'derived_from': ACT, 'algorithm': 'exponential 30-day time decay',
                'as_of': computed['as_of'],
                'hot_records': [{'id': rid, 'score': computed['scores'][rid],
                                 'event_count': computed['event_counts'][rid],
                                 'title': lookup[rid]['title'], 'path': lookup[rid]['path']}
                                for rid in computed['ranking'] if computed['bands'][rid] == 'HOT'],
                'warm_records': [{'id': rid, 'score': computed['scores'][rid],
                                  'event_count': computed['event_counts'][rid],
                                  'title': lookup[rid]['title'], 'path': lookup[rid]['path']}
                                 for rid in computed['ranking'] if computed['bands'][rid] == 'WARM']}
    outputs[HOT_JSON] = encode(hot_json)
    hot_lines = ['# ANDI — ACTIVE NOW / HOT FILES INDEX',
                 '# Status: DERIVED from ACTIVITY_STATE.json — do not edit independently',
                 '# Algorithm: exponential 30-day time decay; guidance only',
                 '# Activity never changes authority, retention, history or CIF scope.', '',
                 '## HOT RECORDS', '| Rank | ID | Score | Events | Title | Path |',
                 '|---:|---|---:|---:|---|---|']
    for index, row in enumerate(hot_json['hot_records'], 1):
        hot_lines.append(f"| {index} | {row['id']} | {row['score']:.9f} | {row['event_count']} | {row['title']} | {row['path']} |")
    hot_lines += ['', '## WARM RECORDS', '| ID | Score | Events | Title | Path |',
                  '|---|---:|---:|---|---|']
    for row in hot_json['warm_records']:
        hot_lines.append(f"| {row['id']} | {row['score']:.9f} | {row['event_count']} | {row['title']} | {row['path']} |")
    outputs[HOT_MD] = ('\n'.join(hot_lines) + '\n').encode()

    map_lines = ['# ANDI — SHALLOW WHOLE-SYSTEM MAP',
                 '# Status: DERIVED / V3 SUCCESSOR',
                 '# Activity is current-work guidance only; it never changes authority, retention, history or CIF scope.',
                 '', 'Full catalog: `../96-machine-tree/RETRIEVAL-INDEX.json`',
                 'Relationships: `../96-machine-tree/MACHINE-TREE.json`', '', '## CANONICAL RECORDS']
    for node in nodes:
        map_lines += [f"### {node['title']} ({node['id']}) — {computed['bands'][node['id']]}",
                      f"- Authority: {node['authority']}", f"- Status: {node['status']}",
                      f"- Pointer: {node['path']}", f"- Summary: {node.get('human_summary', '')}", '']
    outputs[SYSTEM_MAP] = ('\n'.join(map_lines) + '\n').encode()

    tree_lines = ['# ANDI — HUMAN VISUAL PROJECT TREE', '# Status: DERIVED / V3 SUCCESSOR',
                  '# A COLD governing record still governs. Heat never changes CIF scope.', '']
    projects = {}
    for node in nodes:
        for project in node.get('projects', ['UNASSIGNED']):
            projects.setdefault(project, []).append(node)
    for project, members in sorted(projects.items()):
        tree_lines.append('## ' + project)
        for node in members:
            tree_lines.append(f"- [{node['id']}](../{node['path']}) — {computed['bands'][node['id']]} — {node['status']}")
        tree_lines.append('')
    outputs[PROJECT_TREE] = ('\n'.join(tree_lines) + '\n').encode()

    need(isinstance(sources, list), 'Invalid source inventory')
    inventory_ids = {row.get('inv_id') for row in sources if isinstance(row, dict)}
    required_ids = {sid for entry in register['records'] for sid in entry.get('source_ids', [])}
    marker_ids = set()
    for path, data in files.items():
        if path.startswith('80-original-evidence/') and path.endswith('.provenance.md'):
            match = re.search(rb'<!-- INV_ID: (SRC-[0-9]+) -->', data)
            if match:
                marker_ids.add(match[1].decode())
    missing = [{'id': sid, 'status': 'provenance_marker_absent',
                'affected_records': sorted(entry['id'] for entry in register['records']
                                           if sid in entry.get('source_ids', []))}
               for sid in sorted(required_ids - marker_ids)]
    need(required_ids <= inventory_ids, 'Canonical record references unknown source identity')
    outputs[MISSING] = encode({'scope': 'package provenance-marker accessibility only',
                               'completeness_claimed': False, 'not_checked': True,
                               'missing': missing})
    return outputs


def paths(root):
    return root.parent / ('.' + root.name + '.lock'), root.parent / ('.' + root.name + '.txn')


def atomic_write(path, data, temporary=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(temporary) if temporary is not None else path.with_name(path.name + '.pending-write')
    need(temporary.parent == path.parent, 'Temporary write must be sibling of target')
    need(not temporary.exists(), 'Unresolved temporary write: ' + str(temporary))
    with temporary.open('xb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _owned_pending_paths(root, journal):
    declared = journal.get('owned_pending_writes')
    if declared is None:
        return None
    need(isinstance(declared, dict) and set(declared) == {'publish', 'rollback'},
         'Malformed owned temporary-write map')
    changes = journal.get('changes')
    need(isinstance(changes, dict), 'Malformed transaction changes')
    result, all_paths = {}, set()
    for phase in ('publish', 'rollback'):
        mapping = declared[phase]
        need(isinstance(mapping, dict) and set(mapping) == set(changes),
             'Owned temporary-write targets do not match journal changes')
        result[phase] = {}
        for rel, temporary_rel in mapping.items():
            target, temporary = safe(root, rel), safe(root, temporary_rel)
            need(temporary.parent == target.parent and
                 temporary.name.startswith(target.name + '.pending-write-'),
                 'Unsafe owned temporary-write path')
            need(temporary_rel not in journal['before'] and temporary_rel not in journal['after'],
                 'Temporary-write path collides with journal inventory')
            need(temporary_rel not in all_paths, 'Duplicate owned temporary-write path')
            all_paths.add(temporary_rel)
            result[phase][rel] = temporary_rel
    return result


def _recover_pending_validation(root, journal):
    owned = _owned_pending_paths(root, journal)
    owned_paths = set() if owned is None else {rel for phase in owned.values() for rel in phase.values()}
    for pending in snapshot(root):
        if '.pending-write' not in Path(pending).name or pending in owned_paths:
            continue
        target = pending.split('.pending-write', 1)[0]
        if pending in journal['before'] and target not in journal['changes']:
            continue
        need(False, 'Unowned pending-write residue; recovery refuses: ' + pending)


def _recover(root):
    lock, txn = paths(root)
    need(txn.exists() and (txn / 'journal.json').is_file(),
         'No complete journal; retain for inspection')
    journal = decode((txn / 'journal.json').read_bytes())
    need(journal['root'] == str(root), 'Recovery root mismatch')
    before, after, current = journal['before'], journal['after'], snapshot(root)
    owned = _owned_pending_paths(root, journal)
    owned_paths = set() if owned is None else {rel for phase in owned.values() for rel in phase.values()}
    pending_writes = [rel for rel in current if '.pending-write' in Path(rel).name]
    legacy_owned = set()
    for pending in pending_writes:
        if pending in owned_paths:
            need(pending not in before, 'Pre-existing owned temporary-write path; recovery refuses: ' + pending)
            continue
        if owned is None and pending.endswith('.pending-write'):
            target = pending[:-len('.pending-write')]
            if target in journal['changes']:
                need(pending not in before, 'Pre-existing pending-write residue; recovery refuses: ' + pending)
                need(digest(current[pending]) == journal['changes'][target]['after'],
                     'Pending-write residue does not match journal; recovery refuses: ' + pending)
                legacy_owned.add(pending)
                continue
        target = pending.split('.pending-write', 1)[0]
        if pending in before and target not in journal['changes']:
            continue
        need(False, 'Unowned pending-write residue; recovery refuses: ' + pending)
    for pending in pending_writes:
        if pending in owned_paths or pending in legacy_owned:
            del current[pending]
            path = safe(root, pending)
            if path.exists():
                path.unlink()
    for rel in set(before) | set(after) | set(current):
        value = digest(current[rel]) if rel in current else None
        need(value in (before.get(rel), after.get(rel)),
             'Unexpected edits; recovery refuses: ' + rel)
    for rel, item in journal['changes'].items():
        for side in ('before', 'after'):
            expected = item[side]
            payload = safe(txn, side + '/' + rel)
            need((expected is None and not payload.exists()) or
                 (payload.is_file() and digest(payload.read_bytes()) == expected),
                 'Recovery payload mismatch')
    committed = (txn / 'COMMITTED').is_file()
    if committed:
        need({rel: digest(data) for rel, data in current.items()} == after,
             'Committed generation differs')
    else:
        for rel, item in journal['changes'].items():
            target = safe(root, rel)
            if item['before'] is None:
                if target.exists():
                    target.unlink()
            else:
                temporary = None if owned is None else safe(root, owned['rollback'][rel])
                atomic_write(target, safe(txn, 'before/' + rel).read_bytes(), temporary)
        need({rel: digest(data) for rel, data in snapshot(root).items()} == before,
             'Rollback verification failed')
    need(txn.parent == root.parent and txn.name == '.' + root.name + '.txn',
         'Unsafe cleanup target')
    shutil.rmtree(txn)
    lock.unlink()
    return 'kept_committed' if committed else 'rolled_back'


def recover(root, writer_stopped=False):
    root = root_guard(root)
    need(writer_stopped, 'Recovery requires verified stopped writer and exclusive maintenance window')
    need(paths(root)[0].exists(), 'No recovery lock')
    return _recover(root)


def rebuild(root, as_of=None, changes=None, fault=None, authoring_request=None):
    """Journal and publish one verified V3 generation; no deletion API."""
    root = root_guard(root)
    lock, txn = paths(root)
    need(not txn.exists(), 'Pending recovery transaction')
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise Invalid('Maintenance lock exists; no read/write') from exc
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    prepared = False
    try:
        before, proposed = snapshot(root), None
        need(not (changes and authoring_request),
             'Cannot combine update and new-record authoring operations')
        proposed = dict(before)
        if authoring_request is not None:
            proposed.update(prepare_addition(before, authoring_request, as_of))
        register_paths = {row['path'] for row in decode(before[REGISTER])['records']}
        allowed = register_paths | {ACT, MACHINE, SOURCE}
        # Allow kernel, derived-view, evidence, and register writes
        always_allowed_prefixes = ('00-kernel/', '95-human-archive/', '96-machine-tree/',
                                    EVIDENCE_DIR + '/', '90-registers/')
        for rel in (changes or {}):
            if any(rel.startswith(p) for p in always_allowed_prefixes):
                allowed.add(rel)
        for rel, data in (changes or {}).items():
            safe(root, rel)
            need(rel in allowed, 'Update outside declared authoritative inputs')
            need(isinstance(data, bytes), 'Updates must be bytes')
            if rel in register_paths:
                new_fields = header(data)[0]
                need(rel in before and new_fields['STABLE_ID'] == header(before[rel])[0]['STABLE_ID'],
                     'Stable ID/path cannot change through update API')
            if rel == ACT:
                old_events = decode(before[ACT])['event_log']
                new_events = decode(data)['event_log']
                need(new_events[:len(old_events)] == old_events,
                     'Activity log must be append-only')
            proposed[rel] = data
        proposed.update(build(proposed, as_of))
        changed = {rel: data for rel, data in proposed.items() if before.get(rel) != data}
        if not changed:
            lock.unlink()
            return {'changed': [], 'status': 'no_change'}
        for rel in changed:
            path = safe(root, rel)
            need(not path.exists() or path.is_file(), 'Output is not a file')
        transaction_id = secrets.token_hex(12)
        owned_pending = {phase: {rel: rel + '.pending-write-' + transaction_id + '-' + phase
                                 for rel in sorted(changed)}
                         for phase in ('publish', 'rollback')}
        for phase in owned_pending.values():
            for temporary_rel in phase.values():
                temporary = safe(root, temporary_rel)
                need(temporary_rel not in before and not temporary.exists(),
                     'Unresolved temporary-write path collision')
        txn.mkdir()
        journal = {'root': str(root),
                   'before': {rel: digest(data) for rel, data in before.items()},
                   'after': {rel: digest(data) for rel, data in proposed.items()},
                   'changes': {}, 'owned_pending_writes': owned_pending}
        for rel, data in sorted(changed.items()):
            for side, value in (('before', before.get(rel)), ('after', data)):
                if value is not None:
                    atomic_write(safe(txn, side + '/' + rel), value)
            journal['changes'][rel] = {'before': digest(before[rel]) if rel in before else None,
                                       'after': digest(data)}
        atomic_write(txn / 'journal.json', encode(journal))
        prepared = True
        _owned_pending_paths(root, journal)
        _recover_pending_validation(root, journal)
        need(snapshot(root) == before, 'Source changed during staging')
        if fault == 'before_publish':
            raise OSError('Injected before publication')
        for index, (rel, data) in enumerate(sorted(changed.items())):
            atomic_write(safe(root, rel), data, safe(root, owned_pending['publish'][rel]))
            if index == 0 and fault == 'after_first':
                raise OSError('Injected after first replacement')
            if index == 0 and fault == 'crash_after_first':
                os._exit(73)
        need(snapshot(root) == proposed, 'Readback differs from planned generation')
        atomic_write(txn / 'COMMITTED', b'verified\n')
        if fault == 'crash_after_commit':
            os._exit(74)
        _recover(root)
        return {'changed': sorted(changed), 'status': 'verified'}
    except Exception:
        if prepared:
            _recover(root)
        elif not txn.exists():
            lock.unlink(missing_ok=True)
        raise


def read_record(root, rid):
    root = root_guard(root)
    need(not paths(root)[0].exists(), 'Maintenance in progress; retry after recovery')
    files = snapshot(root)
    register = decode(files[REGISTER])
    matches = [row['path'] for row in register['records'] if row['id'] == rid]
    need(len(matches) == 1, 'Record identity missing/ambiguous')
    data = files[matches[0]]
    need(header(data)[0]['STABLE_ID'] == rid, 'Record identity mismatch')
    need(not paths(root)[0].exists(), 'Maintenance started during read')
    return data


def add_record(root, request, as_of=None, fault=None):
    """Author one new record through the existing verified generation boundary."""
    result = rebuild(root, as_of=as_of, fault=fault, authoring_request=request)
    rid, rel = request.get('stable_id'), request.get('path')
    data = read_record(root, rid)
    fields, _, offset = header(data)
    need(fields.get('STABLE_ID') == rid and fields.get('AUTHORITY') == request.get('authority') and
         fields.get('STATUS') == 'UNRECONCILED', 'Authored record readback mismatch')
    need(data[offset:] == request.get('body', '').encode('utf-8'),
         'Authored record body readback mismatch')
    current = snapshot(root)
    register = decode(current[REGISTER])
    machine = decode(current[MACHINE])
    need(sum(row.get('id') == rid and row.get('path') == rel
             for row in register['records']) == 1, 'Authored register readback mismatch')
    need(sum(node.get('id') == rid and node.get('path') == rel
             for node in machine['nodes']) == 1, 'Authored machine-tree readback mismatch')
    result.update({'record_id': rid, 'path': rel, 'sha256': digest(data)})
    return result


def register_source(root, request, as_of=None, fault=None):
    """Governed source-incorporation doorway.

    Accept a transient JSON request outside the Preservation root.  Validate the
    supplied source identity, create the provenance marker and SOURCE_INVENTORY
    entry through a single journaled transaction, and return a bound receipt.

    This closes the gap where add required an already-existing SRC-NNN.
    """
    root = root_guard(root)
    required = {'schema', 'source_id', 'original_name', 'original_sha256',
                'transport_mechanism', 'delivery_timestamp', 'original_bytes',
                'projects', 'note'}
    need(isinstance(request, dict) and set(request) == required,
         'Source registration request has missing/unknown fields')
    need(type(request['schema']) is int and request['schema'] == 1,
         'Unsupported source registration schema')

    sid = request['source_id']
    need(isinstance(sid, str) and SRC_RID.fullmatch(sid),
         'Invalid source identity')

    files = snapshot(root)
    sources = decode(files[SOURCE])
    need(isinstance(sources, list), 'Invalid source inventory')
    inventory_ids = {row.get('inv_id') for row in sources if isinstance(row, dict)}
    need(sid not in inventory_ids,
         f'Source identity already exists: {sid}')

    match = re.fullmatch(r'SRC-([0-9]{3,})', sid)
    source_num = int(match.group(1))
    existing_nums = [int(re.fullmatch(r'SRC-([0-9]{3,})', i).group(1))
                     for i in inventory_ids if re.fullmatch(r'SRC-([0-9]{3,})', i)]
    need(source_num == max(existing_nums, default=0) + 1,
         'Source identity is not the next sequential SRC number')

    def txt(name):
        value = request[name]
        need(isinstance(value, str) and value.strip() == value and value,
             f'Invalid source field: {name}')
        return value

    original_name = txt('original_name')
    original_sha256 = txt('original_sha256')
    transport = txt('transport_mechanism')
    delivered = txt('delivery_timestamp')
    need(re.fullmatch(r'[0-9a-fA-F]{64}', original_sha256),
         'Invalid SHA-256 hash')
    need(isinstance(request['original_bytes'], int) and request['original_bytes'] >= 0,
         'Invalid original_bytes')

    projects = request['projects']
    need(isinstance(projects, list) and projects and
         all(isinstance(p, str) and re.fullmatch(r'[A-Z][A-Z0-9_]*', p)
             for p in projects) and len(projects) == len(set(projects)),
         'Invalid/duplicate project identity')
    note = txt('note')

    provenance_filename = f'{sid}-{original_name}.provenance.md'
    provenance_path = f'{EVIDENCE_DIR}/postbox/{provenance_filename}'
    provenance_content = (
        f'# PROVENANCE MARKER - {sid}\n\n'
        f'<!-- SOURCE_ID: {sid} -->\n'
        f'<!-- ORIGINAL_NAME: {original_name} -->\n'
        f'<!-- ORIGINAL_SHA256: {original_sha256} -->\n'
        f'<!-- TRANSPORT: {transport} -->\n'
        f'<!-- DELIVERED: {delivered} -->\n'
        f'<!-- ORIGINAL_BYTES: {request["original_bytes"]} -->\n'
        f'<!-- PROVENANCE_STATUS: ESTABLISHED -->\n\n'
        f'Source {sid}: {original_name}\n'
        f'Transport: {transport} | Delivered: {delivered}\n'
        f'[SYNTHETIC MINI - provenance evidence in full Golden +1 archive]\n'
    ).encode('utf-8')

    new_sources = list(sources)
    new_sources.append({
        'inv_id': sid,
        'source_file': provenance_filename,
        'original_name': original_name,
        'original_sha256': original_sha256,
        'transport_mechanism': transport,
        'delivery_timestamp': delivered,
        'original_bytes': request['original_bytes'],
        'provenance_marker_bytes': len(provenance_content),
        'projects': projects,
        'status': 'ESTABLISHED',
        'note': note
    })

    changes = {
        provenance_path: provenance_content,
        SOURCE: encode(new_sources)
    }
    result = rebuild(root, as_of=as_of, changes=changes, fault=fault)
    data = read_source(root, sid)
    result.update({
        'source_id': sid,
        'provenance_path': provenance_path,
        'provenance_sha256': digest(data)
    })
    return result


def read_source(root, sid):
    """Retrieve a source/provenance marker through the governed boundary."""
    root = root_guard(root)
    need(not paths(root)[0].exists(), 'Maintenance in progress; retry after recovery')
    files = snapshot(root)
    sources = decode(files[SOURCE])
    matches = [row for row in sources if isinstance(row, dict) and row.get('inv_id') == sid]
    need(len(matches) == 1, f'Source identity missing/ambiguous: {sid}')
    rel = f'{EVIDENCE_DIR}/postbox/{matches[0]["source_file"]}'
    need(rel in files, f'Provenance marker missing: {rel}')
    data = files[rel]
    need(not paths(root)[0].exists(), 'Maintenance started during read')
    return data


def load_authoring_request(root, request_path):
    """Read strict transient JSON without allowing it inside Preservation."""
    root = root_guard(root)
    request_path = Path(request_path).absolute()
    need(request_path.is_file(), 'Authoring request file does not exist')
    need(not request_path.resolve().is_relative_to(root),
         'Authoring request must remain outside the Preservation root')
    info = request_path.lstat()
    need(not request_path.is_symlink() and
         not (getattr(info, 'st_file_attributes', 0) & 1024) and info.st_nlink == 1,
         'Authoring request cannot be a link/reparse/hardlinked file')
    return decode(request_path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['rebuild', 'recover', 'add',
                                             'register-source', 'postbox'])
    parser.add_argument('root', type=Path)
    parser.add_argument('request', type=Path, nargs='?')
    parser.add_argument('--as-of')
    parser.add_argument('--writer-stopped', action='store_true')
    parser.add_argument('--fault', choices=['before_publish', 'after_first',
                                            'crash_after_first', 'crash_after_commit'])
    args = parser.parse_args()
    try:
        if args.command == 'recover':
            need(args.request is None, 'Recover does not accept an authoring request')
            result = recover(args.root, args.writer_stopped)
        elif args.command == 'add':
            need(args.request is not None, 'Add requires an authoring request file')
            request = load_authoring_request(args.root, args.request)
            result = add_record(args.root, request, args.as_of, args.fault)
        elif args.command == 'register-source':
            need(args.request is not None, 'register-source requires a request file')
            request = load_authoring_request(args.root, args.request)
            result = register_source(args.root, request, args.as_of, args.fault)
        elif args.command == 'postbox':
            need(args.request is not None, 'postbox requires the postbox directory path')
            import importlib.util
            engine_dir = Path(__file__).resolve().parent.parent
            ext_path = engine_dir / 'postbox_extension.py'
            if not ext_path.exists():
                raise Invalid('postbox_extension.py not found in preservation root')
            spec = importlib.util.spec_from_file_location('postbox_extension', str(ext_path))
            pb = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(pb)
            result = pb.process_postbox(args.request, args.root, args.as_of, args.fault,
                                         engine=sys.modules[__name__])
        else:
            need(args.request is None, 'Rebuild does not accept an authoring request')
            result = rebuild(args.root, args.as_of, fault=args.fault)
        print(json.dumps(result, indent=2))
    except (Invalid, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f'HOLD: {exc}\n')


if __name__ == '__main__':
    main()