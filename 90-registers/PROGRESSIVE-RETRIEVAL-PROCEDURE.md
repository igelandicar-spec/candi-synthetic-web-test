# ANDI — INTERIM BOUNDED ROUTINE GROUNDING / NAVIGATION / RETRIEVAL LAYER
# Status: INTERIM / REVERSIBLE / NON-CANDIDATE
# Remediated: 21 September 2026

## PURPOSE
Provide a bounded routine grounding and navigation mechanism that reduces
unnecessary context loading while keeping all deeper material reachable.

This layer operates ALONGSIDE the established CI/CIF system defined in the
Andi Operating Standard. It does NOT replace, redefine or supersede Full CIF.
When the Operating Standard requires a Full CIF, a Full CIF must be performed
regardless of what this retrieval layer has or has not preloaded.

This mechanism is TEMPORARY pending permanent memory/CIF architecture selection.
It is INTERIM, REVERSIBLE and NON-CANDIDATE.

## WHAT THIS LAYER DOES
- Reduces unnecessary routine loading when a full authoritative grounding
  is not required by the Operating Standard for the current operation.
- Provides progressive access to preserved knowledge through a structured
  navigation hierarchy: kernel → map → hot files → relevant branches → depth.
- Makes activity-concentration visible so a Driver knows where current
  work is happening without traversing the whole archive.

## WHAT THIS LAYER DOES NOT DO
- Does NOT redefine CI, CIF, Full CIF or any established grounding term.
- Does NOT replace the Operating Standard's grounding requirements.
- Does NOT determine when a Full CIF is required (the Operating Standard does).
- Does NOT decide the permanent memory/CIF architecture (Candidates A/B/C do).
- Does NOT grant authority based on activity band.

## NAVIGATION STAGES

### Stage 1 — KERNEL (always)
Load: 00-kernel/KERNEL.md
Provides: identity, purpose, core maxims, source hierarchy, operating essentials,
working relationship essentials, archive navigation, project landscape, priority pointers.

### Stage 2 — SHALLOW MAP (always)
Load: 00-kernel/SYSTEM-MAP.md
Provides: complete project/branch landscape at shallow depth, activity bands,
current-state pointers, dependency indicators.

### Stage 3 — HOT FILES INDEX
Load: 00-kernel/HOT-FILES.md (or HOT-FILES.json)
Provides: where meaningful work is currently concentrated. Hot branches and
hot records with direct pointers. Lets a Driver discover current activity
without scanning the whole tree.

### Stage 4 — DETERMINE RELEVANCE (reasoning only)
From the current task/conversation:
- Which project(s) are relevant?
- Which branches, dependencies, authority requirements?
- Does the Operating Standard require a Full CIF for this operation?

### Stage 5 — EXPAND RELEVANT BRANCHES
Load current-state records for relevant projects at depth appropriate to the task.
HOT records for active work may be loaded at full depth.
WARM/COOL/COLD records are loaded when the task requires them.

### Stage 6 — FOLLOW AUTHORITY AND EVIDENCE (conditional)
When the task requires governance rules, load full Operating Standard and/or
Working Profile via kernel pointers. When provenance or evidence is needed,
follow evidence pointers to specific records.

### Stage 7 — SUFFICIENCY CHECK (reasoning only)
- Do I know the current authoritative state for this task?
- Are relevant dependencies understood?
- Does the Operating Standard require broader grounding than I have loaded?
- Am I relying on inference where a source exists?

If insufficient → retrieve deeper or perform the required CI/CIF.

## TYPICAL COST PROFILES

| Scenario | Approximate size |
|----------|------------------|
| Kernel only (orientation) | ~4.3 KB |
| Kernel + map + hot files | ~14.3 KB |
| Above + one project compact current state | ~19.7 KB |
| Full governance add (OS + WP) | Reference to originals (~46KB + ~24KB) |

Note: Canonical pointer records in this archive are compact summaries/indexes
pointing to preserved original evidence. Full original content is available
via provenance markers in 80-original-evidence/.

## ACTIVITY BANDS AND RETRIEVAL
Activity bands (HOT/WARM/COOL/COLD) indicate WHERE meaningful work is
concentrated, not retrieval priority or authority level.

- A HOT record = someone is actively working there.
- A COLD authoritative record = still mandatory when governance requires it.
- A HOT experimental record = no authority until promoted.

See 90-registers/ACTIVITY_STATE.json for the authoritative activity state.
The HOT-FILES index, SYSTEM-MAP branch summaries and RETRIEVAL-INDEX all
derive from that single source.

## RELATIONSHIP TO ESTABLISHED CI/CIF
The Operating Standard defines when CI and Full CIF are required.
This retrieval layer provides navigation/access machinery.
They are complementary, not competing.

A Full CIF may use this archive's navigation to locate the required
authoritative records efficiently, but the scope and trigger of a Full CIF
remains governed by the Operating Standard, not by this retrieval layer.

## THIS IS TEMPORARY
When permanent memory/CIF architecture testing (Candidates A/B/C) is complete,
Chris/Andi will decide whether this mechanism should be adopted, adapted,
partially incorporated, retained as archive metadata, or retired.
Continued use alone must never silently make it permanent.
