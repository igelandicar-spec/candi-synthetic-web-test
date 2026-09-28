# ANDI New Preservation — controlled GOLDEN-copy authoring integration evidence

**Date:** 2026-09-26  
**Status:** integration candidate only — not commissioned, activated, installed or cut over

## Frozen inputs

- Accepted GOLDEN source archive: `andi-preservation-V3-new-preservation-repaired-successor-2026-09-25.tar.gz`; 91,449 bytes; SHA-256 `9584A7934D3D82481F8DDE55A4490121B8ED0FDAB6B46C62B3D9D1D26AEF1F57`.
- Accepted synthetic behavioral reference: `D1-REPAIRED-SYNTHETIC-CANDIDATE-NOT-COMMISSIONED-2026-09-26.tar.gz`; 37,153 bytes; SHA-256 `9F4271EC246ACAD11E960CF12449F879536422522B53291D385EE108C282BB2B`.
- Both identities were verified before extraction. The accepted archives were not modified.

## Baseline before integration

The accepted GOLDEN archive was safely extracted to a new disposable working directory. Its 119 files were hash-snapshotted. With Python 3.13.15 on Windows, the native whole-generation check was:

```powershell
python -B -X utf8 90-registers/preservation_engine.py rebuild . --as-of 2026-09-25T00:00:00+00:00
```

Result: exit 0; `{"changed": [], "status": "no_change"}`; all 119 files remained byte-identical; no sibling lock or transaction remained. The packaged static `INTEGRITY_REPORT.json` also records its pre-existing 21/21 PASS result.

## Bounded integration

- `preservation_engine.py` now exposes `add` / `add_record()` for one strict transient request.
- The request is translated into GOLDEN's own authoritative inputs: one canonical Markdown original, one canonical-register entry, one machine-tree node plus declared relationships, and one append-only meaningful activity event.
- The existing `rebuild()` transaction still owns the lock, whole-generation validation, derived/reference view generation, journal, uniquely declared publication/rollback temporary paths, exact generation readback, commit, rollback and recovery.
- The request must remain outside Preservation and is never persisted.
- New records start `UNRECONCILED`. Only `PROVISIONAL` or `ESTABLISHED` authority is accepted. `GOVERNING` is refused at this authoring boundary; existing legitimate governing records and general parsing were not changed.
- Existing source identities must resolve in `SOURCE_INVENTORY.json`; no provenance marker or source evidence is invented by authoring.
- Relationships remain authoritative only in `MACHINE-TREE.json`; every authored relationship must involve the new record and have valid endpoints.

## Focused tests

Run from `90-registers`:

```powershell
python -B -X utf8 -m unittest -v test_authoring
```

Final result: **12/12 PASS** (run as isolated test processes on Windows):

1. valid PROVISIONAL creation, source/relationship coordination, generated views, exact readback, preservation and idempotence;
2. valid ESTABLISHED creation;
3. isolated `GOVERNING` + independently valid `UNRECONCILED` refusal with the exact authority-boundary message;
4. duplicate stable identity, case-aliased path and repeated invocation refusal;
5. missing/unknown/malformed field values, path/prefix, sequential identity, status, body and future activity refusal;
6. provenance/source identity validation;
7. relationship endpoint, involvement, duplicate and supersession-boundary validation;
8. exact rollback on ordinary pre-publication and partial-publication failure;
9. CLI success, outside-root request rule and request non-persistence;
10. malformed JSON refusal without change;
11. interrupted uncommitted generation recovery by exact rollback;
12. interrupted verified generation recovery by retained commit and repeated no-change rebuild.

Development feedback found and repaired an exact-body-boundary defect before final testing. A test expectation that assumed `HOT` was corrected to GOLDEN's deterministic derived result, `WARM`; activity remains derived guidance and does not affect authority.

## Final integrated-copy regression and scope check

- Python syntax: PASS.
- Native GOLDEN whole-generation rebuild with the frozen explicit as-of: exit 0, `no_change`.
- No sibling maintenance lock or transaction residue.
- No pre-existing canonical record, provenance marker, relationship input, activity input, source inventory or derived/reference view was changed in the candidate working tree merely by adding the doorway.
- Functional candidate changes are confined to `90-registers/preservation_engine.py`, `90-registers/MAINTENANCE-CONTRACT.md`, focused `90-registers/test_authoring.py`, and this evidence ledger.

## Boundary

This artifact is a non-authoritative candidate for fresh independent review. OLD Preservation remains authoritative. Nothing here authorizes commissioning, activation, installation, cutover or authority transfer.