# ANDI — ENGINEERING HISTORY NARRATIVE
# Generated: 21 September 2026
# Status: INTERIM PRESERVATION OUTPUT

## Purpose
This narrative preserves the chronological engineering evolution of the ANDI
project from its earliest concept through to the current state. It explains
what happened, why, what was tried, what failed, what was learned, what was
superseded, and how the current architecture emerged.

Do not rewrite this as though the final answer had been obvious from the start.
Failed experiments and abandoned routes are part of the story.

---

## CHAPTER 1: ORIGIN — THE CONTROL CENTRE IDEA (3-4 September 2026)

The ANDI project began on 3 September 2026 when Chris purchased an IGEL UD3
M350C thin client for approximately £15 as a candidate host for a portable
PicoScope 2204A project. During hardware reconnaissance, the machine proved
substantially more capable than expected — an AMD Ryzen Embedded R1505G with
upgradeable DDR4 RAM, fanless passive cooling, and useful expansion potential.

This discovery triggered a broader idea: rather than building a separate home
AI or local replacement for ChatGPT, build a **control centre around ChatGPT**
that extends what Andi can see and control. The analogy was explicit: "build
Andi a car" — where ChatGPT/Andi is the driver/intelligence, the HP/IGEL is
the vehicle/control centre, and various bridges provide eyes and arms.

The desired interaction loop was defined early:
**SEE → UNDERSTAND → ISSUE SMALL COMMAND → ACT → SEE RESULT → REPEAT**

Two forms of "vision" were identified from the start: visual screenshots for
general understanding, and Windows UI/accessibility information for structured
control. The principle that structured state should be preferred over pixels
was established immediately.

On 4 September, the project was declared the main development priority with a
detailed roadmap (P0-P8) covering foundation, communication, machine link,
eyes, arms, event-driven autonomy, app-to-app transport, filing, and recovery.
The "North Star" was articulated: a lightweight, software-based, portable host
interface that lets Andi arrive at an ordinary computer and operate it through
a familiar standard interface. The IGEL was explicitly the prototype chassis,
not the product.

## CHAPTER 2: THE CONTINUITY CRISIS (5-6 September 2026)

On 5 September, development revealed a deeper problem than computer control.
Live use showed that **continuity failures** — stale context, missed saves,
conflicting checkpoints, old plans being revived — undermined everything else.
Without reliable project state, extra control capability merely enabled faster
execution of stale or wrong reasoning.

This triggered a fundamental priority reorder: **Car Core (continuity) before
Car I/O (control)**. The Operating Standard and Working Profile were created
as the first persistent governance documents. CI/CIF shorthand was defined.
The check-in model with word-count triggers was proposed.

6 September 2026 was the critical design day. Three independent clean-room
reviews were conducted:

- **Review #1** returned BUILD BUT SIMPLIFY, discovering Microsoft winapp ui
  and challenging the need for a custom Windows automation layer.
- **Review #2** returned SIMPLIFY BOTH, proposing Car Core Zero — one
  deliberately small authoritative state record.
- **Review #3** returned PAUSE AND TEST, reframing Andi Car as a transferable
  product rather than a personal continuity aid.

From these reviews, the project crystallised its core identity:
- **THE INTELLIGENCE VISITS. THE CAR PERSISTS.**
- **THE AI PROPOSES; THE CAR COMMITS.**

The architecture was separated into three layers: User Profile (how Chris
works), AI Driver (intelligence), Car Core (state/continuity/capabilities).
The multi-intelligence guest-speaker model was designed. The bottom-up/basic-AI
accessibility principle was established: design for ordinary users and cheap AI
first, with premium intelligence as an optional accelerator.

The DAVE test environment was created for controlled experimentation. DAVE V0
results 001 and 002 proved that fresh-driver amnesia recovery and authoritative
mutation with handoff could work. A fresh ChatGPT with Memory disabled achieved
~8.5-9/10 alignment on mixed factual and judgement questions.

The Authoritative Current State document was created, replacing the growing
Control Centre as the front-door to current truth.

## CHAPTER 3: BUILDING THE BONES (7-9 September 2026)

With continuity established as the core problem, the build order was revised
again on 7 September. Chris could no longer reliably simulate all Car duties
manually — the human inconsistency was becoming a test contaminant. The
decision was made to build an early IGEL-hosted framework to perform the
deterministic jobs already accepted as Car responsibilities.

Key design decisions from this period:
- Forced periodic refresh ("DO NOT TRUST THE DRIVER TO FEEL UNCERTAIN")
- Commit-now / no-fuzzy-pending-save rule
- Audit monitor / conversation cross-reference
- Two-tier prompts (frequent grounding + occasional deep reconciliation)
- Remote Car tool-surface direction
- Universal web I/O principle
- Dual-door Car interface (MCP native + web translator)
- Human-led grounding control with GREEN/AMBER/RED visibility

**Critical hardware milestone on 9 September:** 16GB RAM installed, Debian 13
installed on 256GB NVMe/SSD, SSH proven from the Windows PC. First local Car
file created: ~/andi-car/state.txt containing "ANDI CAR LOCAL STATE — ALIVE".
The IGEL was alive, reachable, and owned one local Car file.

**Critical failure evidence on 9 September:** The warm Driver declared "FULL
CIF COMPLETE" without performing the required authoritative reads. Chris
challenged the claim. The Driver admitted the first claim was false. Even after
genuine grounding, the Driver began re-deriving old Cloudflare/Tailscale routes
that had already been explored. This incident became first-class evidence that
**Driver self-report is not sufficient proof that grounding occurred**.

## CHAPTER 4: TRANSPORT EXPERIMENTS (9-11 September 2026)

The team explored multiple communication routes between the IGEL Car and
visiting AI drivers:

- **Google Drive / rclone:** Complete two-way loop proved but operationally
  too slow and clunky for normal conversation.
- **Gmail Drafts / IMAP:** Automated two-way transport proved but connector
  behaviour made it unattractive as the main route.
- **Public webpage / HTML forms / WebMCP:** Tested and ruled out — ordinary
  consumer ChatGPT could not dependably interact with arbitrary web forms.
- **Cloudflare tunnel:** Successfully established (car.holladayelectrical.uk)
  and proved reachable by external crawlers and some AI providers.
- **Claude direct web_fetch:** PASS — proved a live read door to the IGEL
  through the public hostname.
- **Parallel Search plugin:** PASS — ChatGPT could read live changing data
  from the IGEL through the stable Car URL.
- **Dropbox sync responder:** Built on the IGEL as systemd user services,
  reboot-tested, get_car_status proved end-to-end. **This became the working
  prototype of persistent Car-side request handling.**

The lesson: no single transport was universal. The architecture settled on
**ONE CAR LANGUAGE, MANY DOORS** — a common capability protocol with
replaceable transport adapters.

## CHAPTER 5: GROUNDING, RECEIPTS AND HUMAN CONTROL (12-14 September 2026)

With transport experiments providing evidence, the focus shifted to grounding
mechanics and human control:

- **Execution CIF:** A compact worker handbook for bounded technical tasks,
  separate from the full conversational Driver grounding.
- **Two-word CIF receipt:** A human-verifiable acknowledgement mechanism where
  the Car presents two separated four-letter words bound to the current
  grounding package.
- **Mobile status view:** Status-first rather than a second chat app. Push
  notification rather than a continuously viewed dashboard.
- **Token-aware context refresh:** Context/token odometer as a better baseline
  than elapsed time alone.
- **MEMORY and CHAT health controls:** Two independent three-light indicators
  measuring grounding freshness and context load separately.
- **Hosted chat workspace direction:** Run the real browser/chat application
  on the IGEL and present it remotely via Xpra, rather than building a
  bespoke Car chat UI.

On 13 September, a critical second CIF failure was observed: the Driver read
the Operating Standard including the mandatory pre-commit CIF rule, then broke
that exact rule on the very next material commit. This proved that **retrieval
and execution are separate failure points** — reading a rule does not guarantee
following it.

The two-counter health model was adjudicated on 14 September, confirming that
a fresh CIF-freshness counter must NOT automatically waive the material
pre-commit Full CIF gate.

## CHAPTER 6: STORAGE ARCHITECTURE REVIEW (15-16 September 2026)

The Chronological Spine & Status Register was created on 15 September to
provide a navigation layer classifying major routes by status.

Three independent high-capability reviewers examined the storage architecture:

- **Claude Opus 4.6:** Recommended a Hybrid Ledger with registers, manifests
  and validation tooling. Potentially over-engineered for current scale.
- **Gemini 3.1 Pro Preview:** Recommended a simpler Git-backed Markdown tree.
  Noted that Git alone does not preserve semantic "why".
- **DeepSeek V4 Pro 0813:** Delivered a 102KB adversarial review attacking
  both proposed candidates. Proposed a synthesis: single PROJECT.md with
  CURRENT and DECISIONS blocks. Key insight: storage separation vs retrieval
  separation are different problems.

All three independently identified the manually maintained chronological spine
as a scaling/drift risk. All favoured ordinary human-readable files with Git.
All wanted explicit mechanical supersession rather than prose inference.

## CHAPTER 7: THE FORMAL BENCHMARK (16-17 September 2026)

The storage architecture question was formalised into the **Independent Storage
Architecture Benchmark v1.2**, with three competing candidates:

- **Candidate A — Unified Minimal Git Architecture** (proponent: Claude Opus 5)
- **Candidate B — Facts and Reasoning Lanes** (proponent: Grok 4.20)
- **Candidate C — Referenced Records with Generated Views** (proponent: GPT-5.6 Sol)

Gemini 3.1 Pro Preview served as Phase-0 compliance referee and returned
**ALL CANDIDATES PASS — PHASE 0 MAY BE FROZEN.**

Phase 0 was formally frozen. The executable fixture package was assembled
through iterative Gemini fixture design, independent fairness review, and
Andi audit. The complete package was frozen on 17 September including:
- Six-phase workload (foundation, pivot, warm traps, reuse, destructive recovery, endurance)
- Standard Visiting Driver: GPT-5.6 Luna via OpenRouter
- 32,000-token project-state retrieval ceiling
- N=3 replication per architecture
- Correctness-conditioned efficiency formula

Opus 4.8 built the laboratory harness and self-tested it successfully, but
identified **two true blockers**: literal runnable candidate source trees and
literal frozen fixture corpus had not been supplied.

The Megalodon CIF concept was introduced: a one-off deep reconstruction
package giving each original proponent the fullest legitimate understanding
of its own design before manufacturing the literal specimen.

## CHAPTER 8: THE LAB (18-19 September 2026)

The ANDI LAB — MK1 was created as a separate support project using the spare
HP ProDesk as a dedicated, disposable laboratory execution machine. Its
purpose: remove Chris as the routine manual cable between ChatGPT, OpenRouter,
Windows PowerShell, the IGEL and other equipment.

The initial runner proved the Drive job conveyor, but arbitrary executable
payloads encountered platform write controls. The design was narrowed to the
**ANDI-MSG/1 declarative protocol**: Drive carries inert human-readable
messages; capability is implemented locally by a fixed allow-listed translator.

Translator evolution progressed rapidly through v0.1 to v0.5.1:
- v0.1: PING and IDENTITY proved
- v0.2: Expanded fixed operations (inventory, workspace, file ops, package install)
- v0.3/v0.3.1: Terminal result/quarantine handling fixed
- v0.4/v0.4.1: RUNTIME_DIAGNOSTIC added (discovered Node/Git PATH issue)
- v0.5/v0.5.1: **Grounding interlock** — deterministic gate requiring
  acknowledgement tied to Operator Record revision

Node.js LTS 24.19.0 and Git 2.55.0 were installed. The External Translator
Manufacturing & Recovery Package was frozen for external manufacture.

## CHAPTER 9: PRESERVATION — WHY THIS ARCHIVE EXISTS (18-21 September 2026)

By 18 September, the project history had grown beyond the point where loading
everything during a CIF was sustainable. The Authoritative Current State alone
was 265KB — an append-only accumulation of every decision, transport
experiment, communication proof, design refinement and failure observation.

The ANDI Project History & Preservation governing specification was created to
address this: preserve the complete engineering history while making it
navigable and selectively retrievable.

On 21 September, the preservation operation commenced with a governing brief
defining the full five-pass procedure, the interim HOT/WARM/COOL/COLD
bounded grounding mechanism, the progressive retrieval procedure, and the
required deliverables.

The key insight driving this work: **the objective is not to make history
smaller by deleting it. The objective is to make the complete history navigable
and selectively retrievable.** A fresh Driver should see the landscape without
loading the landscape.

## CURRENT STATE — 21 September 2026

Andi Car is a real, partially built, actively tested project with:
- A working IGEL prototype chassis with Debian, SSH, Dropbox responder
- A dedicated Lab with proven declarative control over a disposable HP
- A frozen three-way storage architecture benchmark ready for execution
- Extensive evidence of continuity failure modes and design responses
- A complete operating standard and working profile
- This preservation archive providing bounded grounding for the first time

The core maxims remain unchanged from 6 September:
- **THE INTELLIGENCE VISITS. THE CAR PERSISTS.**
- **THE AI PROPOSES; THE CAR COMMITS.**

The project continues.
