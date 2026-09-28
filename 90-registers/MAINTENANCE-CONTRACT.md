# ANDI PRESERVATION — LIVING-SYSTEM MAINTENANCE CONTRACT
# Version: 3.0
# Status: INTERIM / REVERSIBLE / NON-CANDIDATE

## PURPOSE
This contract defines how every structural artifact in the archive is maintained
as a living system. For each artifact: what it is, what drives changes to it,
how to update it incrementally, how to recover it, and what wins on conflict.

A fresh Driver must be able to perform any common maintenance operation by
following this contract without reconstructing the whole corpus.

### Controlled publication and recovery
Use `90-registers/preservation_engine.py` for one journaled maintenance generation.
The engine validates identity, relationships, activity and output paths before
publication, then verifies the complete readback. It has no deletion API.
Publication and rollback temporary paths are uniquely declared in the journal
before use. Recovery may remove only those declared paths; pre-existing or
otherwise unowned residue is preserved and causes refusal. Run recovery only
after verifying that the writer is stopped and an exclusive maintenance window
exists. A repeated rebuild with the same explicit `--as-of` must be a no-change
operation. These mechanics do not authorise activation or cutover.

---

## 1. CANONICAL RECORDS

**Class**: AUTHORITATIVE state (the knowledge itself)
**Source of truth**: The record IS the truth for its declared scope.
**What causes change**: Meaningful project work — new facts, decisions, edits, supersessions.
**Incremental update**: Edit the record directly. Update its `<!-- STABLE_ID -->` header if metadata changes. If the record is a pointer/summary, update BOTH the pointer AND the underlying original when the original changes.
**Recovery**: Canonical content originates from project work. If a canonical record is lost, its content must be recovered from the original source evidence (80-original-evidence/ provenance markers), project conversations, or Chris/Andi knowledge. It cannot be regenerated from derived views.
**Conflict rule**: The canonical record wins over any derived view, index, summary or navigation artifact.

### Adding a new canonical record
Use the supported `preservation_engine.py add` boundary with one strict UTF-8 JSON
request outside the Preservation root. Do not manually stage a partial generation.
The doorway accepts only the next sequential `CAN-GOV-NNN`, `CAN-CAR-NNN`,
`CAN-BM-NNN` or `CAN-LAB-NNN` identity and a matching project path. All fields
below are required; unknown fields are refused:

```json
{
  "schema": 1,
  "stable_id": "CAN-CAR-014",
  "path": "10-andi-car/history/example.md",
  "title": "Example record",
  "type": "historical",
  "record_type": "canonical_record",
  "authority": "PROVISIONAL",
  "status": "UNRECONCILED",
  "body": "# Example record\nCanonical knowledge.\n",
  "source_ids": ["SRC-001"],
  "projects": ["ANDI_CAR"],
  "human_summary": "Bounded retrieval summary",
  "note": "Canonical record authored through the supported boundary.",
  "relationships": [
    {"from": "CAN-CAR-014", "to": "CAN-CAR-001", "type": "references"}
  ],
  "activity": {
    "timestamp": "2026-09-25T00:00:00Z",
    "type": "edit",
    "description": "Example canonical record authored."
  }
}
```

Run `python preservation_engine.py add <preservation-root> <request.json>
--as-of <timezone-aware timestamp>`. The request is transient and is never
copied into Preservation. `authority` may be only `PROVISIONAL` or
`ESTABLISHED`; this doorway cannot create `GOVERNING` authority. Every new
record starts `UNRECONCILED`, and its initial activity is derived. Source IDs
must already resolve in SOURCE_INVENTORY and their provenance markers remain
subject to whole-generation validation. Every relationship must involve the
new record and must have valid endpoints. Supersession continues to require
the separate two-record procedure below.

The engine creates one canonical original, appends its register entry,
machine-tree node/relationships and meaningful activity event, then delegates
all validation, derived-view generation, locking, journaling, publication,
readback, rollback and recovery to the existing whole-generation transaction.
Existing identities and case-aliased paths are refused rather than overwritten.
After interruption, stop the writer and use the existing `recover
--writer-stopped` operation before retrying.

### Decomposing a large canonical record
When a canonical leaf grows too large for practical retrieval:
1. Create new child records with new stable IDs for the split portions.
2. The original record either:
   a. Becomes a navigation/index record pointing to the children (retains its stable ID, changes record_type to "decomposition_index"), OR
   b. Is superseded by the children (add superseded_by pointing to the new IDs; mark status SUPERSEDED).
3. All INBOUND references to the original ID remain valid because the original record still exists (as index or superseded marker).
4. Add supersedes/child relationships in MACHINE-TREE.
5. Old provenance/source markers are NOT deleted — they reference the original undivided source.
6. Log a meaningful activity event.

### Superseding a canonical record
1. Create the replacement record with a new stable ID.
2. Add `superseded_by: NEW-ID` to the old record header. Change status to SUPERSEDED.
3. Add `supersedes: OLD-ID` to the new record header.
4. Update relationships in MACHINE-TREE.
5. The old record remains physically present and retrievable — superseded content is history, not garbage.
6. Log a meaningful activity event.

---

## 2. CANONICAL RECORD REGISTER (90-registers/CANONICAL_RECORD_REGISTER.json)

**Class**: REGISTER (index of canonical records)
**Source of truth**: Derived from the set of canonical record files. Each record's `<!-- STABLE_ID -->` header is primary; the register is a convenience index.
**What causes change**: Any canonical record is added, removed, superseded, or has metadata change.
**Incremental update**: Add/modify the relevant entry in the JSON array. Do not rewrite unrelated entries.
**Recovery**: Walk the physical archive tree, find all files with `<!-- STABLE_ID: ... -->` headers, and rebuild the register from those headers plus filesystem metadata.
**Conflict rule**: If the register disagrees with a canonical record's own header, the header wins.

---

## 3. STABLE IDS AND RELATIONSHIPS

**Class**: AUTHORITATIVE identity (IDs), AUTHORITATIVE structure (relationships)
**Source of truth**: Each record's `<!-- STABLE_ID -->` header is the primary ID assignment. Relationships are authoritative in MACHINE-TREE.json.
**What causes change**: New records, new dependencies, supersessions, decompositions.
**Incremental update**: Add new relationships to MACHINE-TREE.json. Never reuse or renumber existing IDs.
**Recovery**: IDs survive in file headers even if MACHINE-TREE is lost. Relationships can be partially reconstructed from `depends_on`, `supersedes`, `evidence_for` references within canonical records themselves, plus the register.
**Conflict rule**: File-header ID is canonical. MACHINE-TREE relationships are authoritative for cross-record structure.

---

## 4. PROVENANCE / SOURCE REGISTER (80-original-evidence/ + 90-registers/SOURCE_INVENTORY.json)

**Class**: AUTHORITATIVE provenance (the provenance markers), REGISTER (the inventory index)
**Source of truth**: The .provenance.md files in 80-original-evidence/ are the authoritative provenance chain to original source material. SOURCE_INVENTORY.json is a convenience index.
**What causes change**: New source material is incorporated; original source is independently verified or corrected.
**Incremental update for new source**: Create a new .provenance.md in the appropriate subfolder. Add entry to SOURCE_INVENTORY.json.
**Recovery**: Walk 80-original-evidence/ to rebuild SOURCE_INVENTORY.json.
**Conflict rule**: Provenance markers describe ORIGINAL source identity. They do not change merely because a canonical record is edited. If original source bytes/hashes are independently verified to differ, update the provenance marker with an explanation.

---

## 5. SUPERSESSION STATE

**Class**: AUTHORITATIVE (lives within canonical records and MACHINE-TREE relationships)
**Source of truth**: The supersedes/superseded_by fields in canonical record headers AND in MACHINE-TREE.json relationships.
**What causes change**: A decision, design or fact is replaced by a newer version.
**Incremental update**: See "Superseding a canonical record" above.
**Recovery**: Supersession relationships can be found by scanning canonical record headers for supersedes/superseded_by fields.
**Conflict rule**: If a record header and MACHINE-TREE disagree on supersession, investigate and reconcile. Neither silently wins — add to Human Review Register.

---

## 6. SYSTEM-MAP (00-kernel/SYSTEM-MAP.md)

**Class**: DERIVED navigational view
**Source of truth**: Canonical records + CANONICAL_RECORD_REGISTER + ACTIVITY_STATE (for branch hottest_activity)
**What causes change**: New project/branch, new canonical record, activity band changes, status changes.
**Incremental update**: Add/modify the relevant project/branch section. Update branch hottest_activity from current ACTIVITY_STATE bands.
**Recovery**: Regenerate entirely from CANONICAL_RECORD_REGISTER (for record list) + ACTIVITY_STATE (for bands) + canonical record headers (for authority/status). Loss of SYSTEM-MAP does NOT lose knowledge.
**Conflict rule**: If SYSTEM-MAP disagrees with a canonical record or ACTIVITY_STATE, the source wins. Regenerate the conflicting section.

---

## 7. HOT-FILES (00-kernel/HOT-FILES.md + HOT-FILES.json)

**Class**: DERIVED navigational shortcut
**Source of truth**: ACTIVITY_STATE.json (band assignments)
**What causes change**: Any activity band recomputation.
**Incremental update**: Regenerate from current ACTIVITY_STATE band_assignments + CANONICAL_RECORD_REGISTER for paths/titles.
**Recovery**: Regenerate entirely from ACTIVITY_STATE + register. Loss of HOT-FILES does NOT lose knowledge or activity state.
**Conflict rule**: ACTIVITY_STATE.json always wins. HOT-FILES is a disposable view.

---

## 8. HUMAN PROJECT-TREE (95-human-archive/PROJECT-TREE.md)

**Class**: DERIVED human navigational view
**Source of truth**: Canonical records + CANONICAL_RECORD_REGISTER + ACTIVITY_STATE (for band annotations)
**What causes change**: New project/branch, structural reorganisation, activity changes.
**Incremental update**: Add new branches/records to the tree. Update activity annotations from ACTIVITY_STATE.
**Recovery**: Regenerate from register + activity state + canonical record metadata. Loss does NOT lose knowledge.
**Conflict rule**: Source records win. Regenerate conflicting portions.

---

## 9. HUMAN HISTORY VIEWS (95-human-archive/MILESTONE-TIMELINE.md, HISTORICAL-NARRATIVE.md)

**Class**: DERIVED human historical views (see Correction 3 below for growth method)
**Source of truth**: Canonical records, activity event log, original evidence.
**What causes change**: New milestones, decisions, significant events.
**Incremental update**: APPEND new entries to the timeline. For narrative, append a new dated chapter/section rather than rewriting earlier chapters. See bounded-history-growth section below.
**Recovery**: Can be reconstructed from canonical records + activity event log + original evidence, but reconstruction is expensive. Treat as valuable cached work.
**Conflict rule**: If a history view contradicts a canonical record, the canonical record wins. Correct the history view.

---

## 10. MACHINE-TREE (96-machine-tree/MACHINE-TREE.json)

**Class**: AUTHORITATIVE for relationships; DERIVED for activity bands and sizes
**Source of truth**: Relationships are authoritative here. Activity bands derived from ACTIVITY_STATE. Sizes measured from filesystem.
**What causes change**: New records, new relationships, activity recomputation, file size changes.
**Incremental update**: Add new nodes/relationships. Update activity_band fields from ACTIVITY_STATE. Remeasure actual_manufactured_bytes for changed files.
**Recovery**: Nodes from CANONICAL_RECORD_REGISTER + file headers. Activity from ACTIVITY_STATE. Sizes from filesystem. Relationships are harder: they live primarily here, but can be partially reconstructed from record-internal references. Loss of MACHINE-TREE loses AUTHORITATIVE relationship structure — back it up.
**Conflict rule**: For relationships: MACHINE-TREE is authoritative. For activity: ACTIVITY_STATE wins.

---

## 11. RETRIEVAL-INDEX (96-machine-tree/RETRIEVAL-INDEX.json)

**Class**: DERIVED machine retrieval convenience index
**Source of truth**: CANONICAL_RECORD_REGISTER + MACHINE-TREE node metadata + ACTIVITY_STATE + filesystem (for sizes)
**What causes change**: Any canonical record change, activity recomputation.
**Incremental update**: Update the relevant entry. Or regenerate entirely.
**Recovery**: Regenerate from register + activity state + filesystem walk. Loss does NOT lose knowledge.
**Conflict rule**: Sources win. Regenerate on conflict.

---

## 12. ACTIVITY STATE (90-registers/ACTIVITY_STATE.json)

**Class**: AUTHORITATIVE for activity tracking
**Source of truth**: This file IS the authoritative activity state. Its event_log is append-only ground truth. Band assignments are derived from the event_log using the concentration algorithm.
**What causes change**: Meaningful project work occurs.
**Incremental update**: Append a new ACT-NNN event. Recompute derived_concentration_ranking from the event_log. Regenerate HOT-FILES and other derived views.
**Recovery**: The event_log is the durable core. If band_assignments or weights are lost/corrupted, recompute from the event_log. If the event_log itself is lost, activity history is lost — but canonical knowledge is NOT lost. A fresh event_log can be started; previous concentration context is gone but new work immediately establishes new bands.
**Conflict rule**: event_log is append-only ground truth. Derived rankings always recomputable from it.

---

## SOURCE-OF-TRUTH MATRIX (summary)

| Artifact | Class | Source of Truth | Recoverable From |
|----------|-------|-----------------|-------------------|
| Canonical records | AUTHORITATIVE | Themselves | Original evidence + project work |
| Canonical register | REGISTER | Canonical file headers | Filesystem scan of headers |
| Stable IDs | AUTHORITATIVE | File headers | File headers (survive all derived-view loss) |
| Relationships | AUTHORITATIVE | MACHINE-TREE.json | Partial: record-internal refs |
| Provenance markers | AUTHORITATIVE | 80-original-evidence/ files | Themselves (+ SOURCE_INVENTORY as index) |
| Supersession | AUTHORITATIVE | Record headers + MACHINE-TREE | Record header scan |
| SYSTEM-MAP | DERIVED | Register + activity state | Regenerate |
| HOT-FILES | DERIVED | Activity state + register | Regenerate |
| PROJECT-TREE | DERIVED | Register + activity state | Regenerate |
| History views | DERIVED (cached) | Canonical records + events | Expensive reconstruct |
| MACHINE-TREE | AUTH (rels) + DERIVED (bands/sizes) | Itself (rels); activity + fs (bands/sizes) | Partial reconstruct |
| RETRIEVAL-INDEX | DERIVED | Register + activity + fs | Regenerate |
| ACTIVITY-STATE | AUTHORITATIVE | Itself (event_log is core) | Event log recomputes bands |

---

## LOSS-IMPACT SUMMARY

| If you lose... | Knowledge lost? | How to recover |
|----------------|----------------|----------------|
| Any DERIVED view | NO | Regenerate from sources |
| ACTIVITY_STATE event_log | Activity history lost; knowledge intact | Start fresh event log |
| MACHINE-TREE relationships | Relationship structure degraded | Partial from record refs; manual rebuild |
| A canonical record | YES for that record's content | From original evidence + project work |
| A provenance marker | Provenance chain for that source degraded | From SOURCE_INVENTORY or manual |
| Everything except canonical records + provenance | Navigability lost; all knowledge intact | Rebuild registers, trees, views |
