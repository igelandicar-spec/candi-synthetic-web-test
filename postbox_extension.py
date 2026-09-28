"""
Golden +1 Postbox and Source-Incorporation Extension.
These functions are injected into preservation_engine.py to complete the
save/source/postbox authoring doorway per the current development brief.
"""

from pathlib import Path
import datetime as dt
import json
import re
import secrets

# # --- Postbox Processor ---

def process_postbox(postbox_dir, root, as_of=None, fault=None, engine=None):
    """File-postbox processor: DELIVERED -> RECEIVED -> VALIDATED -> COMMITTED -> VERIFIED.

    The postbox is a folder outside the Preservation root. Each file is a discrete
    letter. After processing, submissions move to postbox/processed/. Receipts go
    to postbox/receipts/.
    """
    e = engine
    root = e.root_guard(root)
    postbox = Path(postbox_dir).absolute()
    e.need(postbox.is_dir(), 'Postbox directory does not exist')
    e.need(not postbox.resolve().is_relative_to(root),
           'Postbox must remain outside the Preservation root')

    processed_dir = postbox / 'processed'
    receipts_dir = postbox / 'receipts'
    processed_dir.mkdir(exist_ok=True)
    receipts_dir.mkdir(exist_ok=True)

    pending = sorted(
        f for f in postbox.iterdir()
        if f.is_file() and not f.name.startswith('.')
        and f.name not in ('processed', 'receipts')
    )

    results = []
    for submission in pending:
        try:
            data = submission.read_bytes()
            req_hash = e.digest(data)
            try:
                request = e.decode(data)
            except (e.Invalid, UnicodeError, json.JSONDecodeError) as exc:
                results.append(_pb_refuse(submission, processed_dir, receipts_dir,
                                          'MALFORMED', str(exc), engine=e))
                continue

            op = request.get('operation') if isinstance(request, dict) else None
            e.need(isinstance(op, str) and op in _SAVE_OPS,
                   'Unknown/unsupported operation: ' + str(op))

            result = _dispatch_postbox_op(op, request, root, as_of, fault, engine=e)
            receipt = {'status': 'VERIFIED', 'operation': op,
                       'request_file': submission.name, 'request_sha256': req_hash, **result}
            _pb_finish(submission, processed_dir, receipts_dir, 'VERIFIED', receipt, engine=e)
            results.append(receipt)

        except (e.Invalid, OSError, KeyError, TypeError) as exc:
            results.append(_pb_refuse(submission, processed_dir, receipts_dir,
                                      'REFUSED', str(exc), engine=e))
    return results
def _dispatch_postbox_op(op, request, root, as_of, fault, engine=None):
    """Route postbox operations to the appropriate engine function."""
    e = engine
    if op == 'add_source':
        return e.register_source(root, {
            'schema': 1,
            'source_id': request['source_id'],
            'original_name': request['original_name'],
            'original_sha256': request['original_sha256'],
            'transport_mechanism': request['transport_mechanism'],
            'delivery_timestamp': request['delivery_timestamp'],
            'original_bytes': request['original_bytes'],
            'projects': request['projects'],
            'note': request.get('note', 'Postbox source incorporation')
        }, as_of, fault)

    elif op == 'add_knowledge':
        return e.add_record(root, {
            'schema': 1,
            'stable_id': request['stable_id'],
            'path': request['path'],
            'title': request['title'],
            'type': request['type'],
            'record_type': request['record_type'],
            'authority': request['authority'],
            'status': request.get('status', 'UNRECONCILED'),
            'body': request['body'],
            'source_ids': request['source_ids'],
            'projects': request['projects'],
            'human_summary': request.get('human_summary', request.get('title', '')),
            'note': request.get('note', 'Postbox knowledge'),
            'relationships': request.get('relationships', []),
            'activity': request.get('activity', {
                'timestamp': as_of or '2026-09-27T00:00:00Z',
                'type': 'edit',
                'description': 'Postbox: ' + str(request.get('title', ''))
            })
        }, as_of, fault)

    elif op == 'update':
        rid = request['stable_id']
        files_before = e.snapshot(root)
        reg = e.decode(files_before[e.REGISTER])
        matches = [row for row in reg['records'] if row['id'] == rid]
        e.need(matches, 'Unknown record: ' + rid)
        rel = matches[0]['path']
        old_data = files_before[rel]
        _, _, offset = e.header(old_data)
        new_data = old_data[:offset] + request.get('body', '').encode('utf-8')
        act = e.decode(files_before[e.ACT])
        n = len(act.get('event_log', [])) + 1
        act.setdefault('event_log', []).append({
            'event_id': f'ACT-{n:03d}',
            'timestamp': as_of or '2026-09-27T00:00:00Z',
            'type': 'edit',
            'description': 'Postbox update: ' + rid,
            'affected_records': [rid],
            'affected_branches': ['maintenance']
        })
        result = e.rebuild(root, as_of=as_of, changes={rel: new_data, e.ACT: e.encode(act)}, fault=fault)
        result.update({'record_id': rid, 'path': rel, 'sha256': e.digest(new_data)})
        return result

    elif op == 'supersede':
        old_rid = request['superseded_id']
        new_rid = request['stable_id']
        new_rel = request['path']
        files_before = e.snapshot(root)
        reg = e.decode(files_before[e.REGISTER])
        old_matches = [row for row in reg['records'] if row['id'] == old_rid]
        e.need(old_matches, 'Unknown record to supersede: ' + old_rid)
        old_rel = old_matches[0]['path']
        old_data = files_before[old_rel]
        fields, spans, offset = e.header(old_data)
        new_record = (
            f'<!-- STABLE_ID: {new_rid} -->\n'
            f'<!-- SOURCE: {", ".join(request.get("source_ids", []))} -->\n'
            f'<!-- AUTHORITY: {request.get("authority", "ESTABLISHED")} -->\n'
            f'<!-- STATUS: UNRECONCILED -->\n'
            f'<!-- SUPERSEDES: {old_rid} -->\n'
            f'<!-- ACTIVITY: COLD -->\n\n'
        ).encode('utf-8')
        new_record += request.get('body', '# Superseding record\n').encode('utf-8')
        old_patched = (
            old_data[:spans['ACTIVITY'][1]]
            + b'STATUS: SUPERSEDED\n<!-- SUPERSEDED_BY: '
            + new_rid.encode() + b' -->\n<!-- '
            + old_data[spans['ACTIVITY'][0]:spans['ACTIVITY'][1]]
            + old_data[spans['ACTIVITY'][1]:offset]
            + old_data[offset:]
        )
        machine = e.decode(files_before[e.MACHINE])
        machine['nodes'].append({
            'id': new_rid, 'title': request.get('title', ''),
            'type': request.get('type', 'historical'),
            'authority': request.get('authority', 'ESTABLISHED'),
            'status': 'UNRECONCILED',
            'record_type': request.get('record_type', 'canonical_record'),
            'note': request.get('note', ''),
            'source_ids': request.get('source_ids', []),
            'original_source_bytes': None,
            'projects': request.get('projects', []),
            'path': new_rel,
            'human_summary': request.get('human_summary', ''),
            'actual_manufactured_bytes': len(new_record),
            'activity_band': 'COLD'
        })
        machine['relationships'].append({
            'from': new_rid, 'to': old_rid, 'type': 'supersedes'
        })
        act = e.decode(files_before[e.ACT])
        n = len(act.get('event_log', [])) + 1
        act.setdefault('event_log', []).append({
            'event_id': f'ACT-{n:03d}',
            'timestamp': as_of or '2026-09-27T00:00:00Z',
            'type': 'edit',
            'description': f'Superseded {old_rid} by {new_rid}',
            'affected_records': [old_rid, new_rid],
            'affected_branches': ['maintenance']
        })
        changes = {old_rel: old_patched, new_rel: new_record,
                   e.MACHINE: e.encode(machine), e.ACT: e.encode(act)}
        result = e.rebuild(root, as_of=as_of, changes=changes, fault=fault)
        result.update({'superseded_id': old_rid, 'new_record_id': new_rid, 'new_path': new_rel})
        return result

    raise e.Invalid('Unknown operation: ' + op)


def _pb_refuse(submission, processed_dir, receipts_dir, status, reason, engine=None):
    receipt = {'status': status, 'reason': reason, 'request_file': submission.name}
    _pb_finish(submission, processed_dir, receipts_dir, status, receipt, engine=engine)
    return receipt


def _pb_finish(submission, processed_dir, receipts_dir, status, receipt, engine=None):
    e = engine
    receipt_data = e.encode(receipt)
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    receipt_path = receipts_dir / f'{stamp}-receipt-{submission.stem}.json'
    e.atomic_write(receipt_path, receipt_data)
    new_name = f'{stamp}-{status}-{submission.name}'
    new_path = processed_dir / new_name
    e.need(not new_path.exists(), 'Archive collision: ' + new_name)
    submission.replace(new_path)
EVIDENCE_DIR = '80-original-evidence'
SRC_RID = re.compile(r'SRC-[0-9]{3,}')
REGISTER = '90-registers/CANONICAL_RECORD_REGISTER.json'
MACHINE = '96-machine-tree/MACHINE-TREE.json'
ACT = '90-registers/ACTIVITY_STATE.json'
SOURCE = '90-registers/SOURCE_INVENTORY.json'
MEANINGFUL = {'work_session', 'decision', 'test', 'test_result', 'evidence', 'edit',
              'material_edit', 'reactivation', 'relationship',
              'conflict_resolution', 'measurement', 'discovery'}
_SAVE_OPS = {'add_knowledge', 'add_source', 'update', 'supersede'}