# ANDI PRESERVATION — BOUNDED HUMAN-HISTORY GROWTH METHOD
# Version: 3.0
# Status: INTERIM / REVERSIBLE / NON-CANDIDATE

## PROBLEM
MILESTONE-TIMELINE.md and HISTORICAL-NARRATIVE.md were generated on
21 September 2026 as complete-to-date snapshots. Without a forward-growth
method, they will either become stale or grow into the next giant
append-only master — reproducing the exact problem this archive solved.

## DESIGN PRINCIPLES
1. History is preserved in BOUNDED CHUNKS, not one ever-growing monolith.
2. A future Driver adds history INCREMENTALLY without rereading the whole corpus.
3. Human readability is preserved. Chris can browse naturally.
4. Do not fragment every paragraph into a separate file.
5. A sensible chunk contains a coherent body of information — split only
   when growth/retrieval cost justifies it.

## TIMELINE GROWTH
MILESTONE-TIMELINE.md is an APPEND-ONLY dated list.

Forward method:
- New milestones are APPENDED at the bottom with their date.
- No rewriting of earlier entries is needed.
- If the file exceeds a practical size threshold (suggest ~50KB / ~500 entries),
  split into dated chunks:
  - MILESTONE-TIMELINE-2026-SEP.md
  - MILESTONE-TIMELINE-2026-OCT.md
  - etc.
  Keep a small MILESTONE-TIMELINE-INDEX.md listing the chunks with date ranges.
- Each chunk is a standalone readable document for its period.
- The index is a DERIVED view regenerable from the chunk filenames/headers.

## NARRATIVE GROWTH
HISTORICAL-NARRATIVE.md is structured as dated CHAPTERS.

Forward method:
- New chapters are APPENDED at the bottom ("CHAPTER 10: ...").
- Earlier chapters are NOT rewritten merely because later knowledge exists.
  They reflect what was known/attempted/decided at that time.
- If the narrative exceeds a practical size threshold (suggest ~80KB /
  ~10 substantial chapters), split into era files:
  - HISTORICAL-NARRATIVE-01-ORIGIN.md (Chapters 1-2)
  - HISTORICAL-NARRATIVE-02-CONTINUITY.md (Chapters 3-5)
  - etc.
  Keep a small HISTORICAL-NARRATIVE-INDEX.md listing eras and chapter ranges.
- Each era file is a standalone readable human narrative for its period.
- The index is a DERIVED view.

## ADDING A SINGLE NEW EVENT TOMORROW
A Driver performing meaningful project work should:
1. Append a dated entry to MILESTONE-TIMELINE.md.
2. If the work constitutes a chapter-worthy development, append a new
   chapter section to HISTORICAL-NARRATIVE.md.
3. Log the corresponding activity event in ACTIVITY_STATE.json.
4. The Driver does NOT need to reread or regenerate the entire history
   corpus. It only needs to know the current end-of-file to append.

## SPLITTING PROCEDURE
When a history file reaches the threshold:
1. Create the new chunk file covering a defined date/era range.
2. Move the relevant section from the monolith into the chunk.
3. Replace the moved section in the monolith with a one-line pointer:
   "See HISTORICAL-NARRATIVE-02-CONTINUITY.md for Chapters 3-5."
4. Create/update the index file.
5. No stable IDs are broken because history files are human navigation
   views, not canonical records referenced by stable ID from elsewhere.
6. Log as clerical maintenance (does NOT generate an activity event).

## CURRENT STATE (21 September 2026)
- MILESTONE-TIMELINE.md: ~9.3KB, ~130 entries. Well within threshold.
- HISTORICAL-NARRATIVE.md: ~14.4KB, 9 chapters. Well within threshold.
- No splitting needed at current size. This method activates when growth
  approaches the thresholds.

## RELATIONSHIP TO CANONICAL RECORDS
History views are DERIVED from canonical records, activity events and
original evidence. They are valuable cached work but NOT the source
of truth. If a history view contradicts a canonical record, the
canonical record wins.

Loss of history views is recoverable (expensively) from canonical
records + activity event log + original evidence.
