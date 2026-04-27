# Kogami Review · m5_kickoff_governance_clearance · 2026-04-27

**Verdict**: `APPROVE_WITH_COMMENTS`
**Recommended next**: `revise`
**Trigger**: phase_kickoff_strategic_clearance
**Artifact**: `.planning/strategic/m5_kickoff/brief_2026-04-27.md`
**Prompt SHA256**: `f1143020f8dfe93bf39d36e55dce3a3a27a4bce336d1ad98325820162be2a9e0`

## Summary

The brief is a well-scoped strategic clearance request that correctly halts implementation per DEC-V61-088 and surfaces three substantive contradictions for adjudication. The core asks (roadmap fit, governance tier, locked-decision coherence) are appropriately strategic-layer; the spec itself has internal inconsistencies (60-day vs 90-day window-tag mismatch, governance tier conflict with ROADMAP §post-pivot rule, and D3/D5 implicitly touching trust-core surfaces) that block clean APPROVE.

## Strategic Assessment

M5 is a coherent next step in the post-pivot user-as-first-customer arc — the pivot charter Addendum 1 explicitly anticipates 'import your own OpenFOAM case' at the 90-day horizon, and M1–M4 closed-loop being COMPLETE creates the operability substrate that makes STL import meaningful (edit→run→verdict→history). The decision arc from Pivot Charter → ROADMAP §90-day → M5 is sound IF the brief's three contradictions are resolved before code starts. The most strategically risky aspect is the conflation of routine-path UI/route work with trust-core touches (D3 TrustGate, D5 audit_package) under a single 'M5' umbrella; this is exactly the kind of governance-tier blurring that the post-pivot 2026-04-26 standing rule was written to prevent. Roadmap fit: YES, conditional on ROADMAP.md being updated to reflect M5–M8 framing (SSOT-in-repo posture). Governance tier: routine path for the bulk of M5 with explicit trust-core carve-outs for D3+D5, NOT a new 'trust-adjacent' tier (which would itself be a rule change requiring separate clearance). D1–D8 coherence: D1/D2/D6/D7/D8 are consistent with prior decisions and roadmap framing once the 60-day/90-day window tag is fixed; D3/D4/D5 need re-scoping per findings above.

## Findings

### [P1] D3 trust-gate hard-cap modification crosses trust-core boundary
**Position**: §Locked decisions D1–D8 · D3

**Problem**: D3 mandates a 1-line guard in TrustGate routing as part of M5 to hard-cap imported cases at PASS_WITH_DISCLAIMER. TrustGate logic lives in src/auto_verifier/ or trust_core paths (per ROADMAP §Governance posture trust-core list and prior DEC-V61-055/056 P1 arc which placed TrustGateReport on the Evaluation/Control trust-core boundary). Modifying TrustGate routing therefore touches a trust-core surface, contradicting the kickoff's framing of M5 as 'NOT trust-core but adjacent'. This is internal incoherence: the spec simultaneously claims trust-adjacent posture AND mandates a trust-core edit as part of M5 scope.

**Recommendation**: Either (a) split D3 into a separate trust-core micro-PR with full Codex 3-round + DEC + Kogami clearance, executed before or alongside M5 routine work, OR (b) defer the TrustGate hard-cap to M5.1 with an explicit interim guard at the manifest/audit_package layer (since D5 already routes imported cases through audit_package filtering). Make the boundary crossing explicit in the resolved kickoff spec rather than absorbing it into 'M5 routine'.

### [P1] D5 audit_package filter modification is trust-core per ROADMAP
**Position**: §Locked decisions D1–D8 · D5

**Problem**: D5 says M5 sets the manifest tag (source_origin='imported_user') and audit_package filtering is a '~30 LOC follow-up'. Per ROADMAP §Governance posture, src/audit_package/ is explicitly trust-core. Even the manifest-tag write in case_manifest.yaml may be acceptable as a manifest schema additive change, but any audit_package filter logic touching --include-imported is trust-core. Same incoherence as D3: spec routes a trust-core edit as routine.

**Recommendation**: Explicitly partition D5 into (i) M5-routine: add source_origin field to case_manifest.yaml schema (likely additive, low blast radius), and (ii) M5.1 trust-core: audit_package filter + --include-imported CLI flag, gated under trust-core path. Do not allow the '~30 LOC follow-up' framing to silently land trust-core changes.

### [P1] 60-day vs 90-day window-tag internal inconsistency
**Position**: §Pre-implementation surface scan · Contradiction 3 + Locked decisions D8

**Problem**: The kickoff's commit-trailer declares M5 as 60-day ('用户自带 case import (60-day)') while ROADMAP frames 'import your own OpenFOAM case' as the 90-day extension item. D8 then anchors a 'stranger dogfood' gate to the 60-day window end. This conflates two separate roadmap windows: 60-day's scope per ROADMAP is '3 anchor case 闭环 + run-comparison + project/workspace minimal', not import. Without resolving this, M5's success criteria and dogfood gate become ambiguous.

**Recommendation**: Pick one framing explicitly: either (a) update ROADMAP.md to add explicit M5–M8 framing that re-defines 60-day = import, OR (b) re-tag M5 as 90-day extension executing early and re-anchor D8's dogfood gate to the 90-day window. Treat ROADMAP.md as SSOT-in-repo per Pivot Charter; do not let Notion-side M5–M8 framing override repo ROADMAP without an explicit ROADMAP.md update DEC.

### [P2] D4 (gmsh pin for M6) is out-of-scope for an M5 kickoff brief
**Position**: §Locked decisions D1–D8 · D4

**Problem**: D4 pins gmsh>=4.11,<4.13 + CI smoke install matrix + macOS arm64 known-issue posture, all binding M6. Per kickoff hygiene, decisions binding a future milestone should land in that milestone's own kickoff brief where the surface scan and Codex review can validate the pin against the actual M6 implementation context. Pinning M6 dependencies inside an M5 brief creates a forward-binding decision without M6's pre-implementation scan.

**Recommendation**: Defer D4 to M6's own kickoff brief. If D4 is genuinely time-critical (e.g., gmsh wheel availability is a current procurement question), surface that rationale and lift it into a separate dependency-management DEC rather than burying it in M5's locked decisions.

### [P2] Governance tier ambiguity unresolved by author; needs Kogami picking among (a)/(b)/(c)
**Position**: §Pre-implementation surface scan · Contradiction 2

**Problem**: Per the brief's three reads (a) routine, (b) new trust-adjacent tier, (c) trust-core per-PR override: the strategically coherent answer per v6.2 + Pivot Charter Addendum 1 is (a) routine for the upload+frontend+route surface, with explicit carve-outs for the trust-core touches (D3 TrustGate + D5 audit_package filter) handled per their own tier. Reading (b) would constitute a governance rule change requiring its own Hard Boundary clearance, which the brief explicitly disclaims. Reading (c) creates a per-PR override precedent that erodes the post-pivot standing rule.

**Recommendation**: Adopt reading (a) + carve-outs: M5's upload route, scaffold service, frontend page, trimesh dependency, and case_manifest schema additions go routine path (direct commit to main, no DEC, single-pass review). Trust-core touches (D3 TrustGate hard-cap + D5 audit_package filter) get extracted into their own micro-PRs on trust-core path with DEC-V61-08X + Codex 3-round + Kogami clearance. The kickoff spec's blanket 'Codex 3-round + DEC + Kogami' demand should be revised to scope only the trust-core sub-PRs.

### [P2] ROADMAP.md SSOT lag vs Notion M5–M8 framing
**Position**: §Pre-implementation surface scan · Contradiction 1

**Problem**: The Notion-side 'Workbench Beginner-Full-Stack Roadmap (M5–M8)' is referenced as upstream but is not reflected in repo ROADMAP.md, which still shows 'Workbench Closed-Loop M1-M4' as main-line and import as a 90-day extension. Per Pivot Charter and §11.5 SSOT consistency rule, repo ROADMAP.md is SSOT-in-repo; allowing Notion to be the de facto roadmap source contradicts standing methodology.

**Recommendation**: Before M5 implementation begins, land a small ROADMAP.md update DEC (or amendment to DEC-V61-088 chain) that adds explicit M5–M8 framing to the 'Current main-line' / 'extensions' sections. This is a docs-only CLASS-1 change per Pivot Charter §4.7 and can be autonomous. Once landed, M5 surface scan can cite ROADMAP §M5 as the canonical scope anchor.

### [P3] Mechanical path drift in spec citations
**Position**: §Pre-implementation surface scan · Mechanical path drift

**Problem**: Spec cites case_editor.py at services/ (actual: routes/), and lid_driven_cavity.yaml under case_profiles/ (actual: workbench_basics/ + gold_standards/). These are scoping errors in the kickoff prompt, not strategic blockers, but they propagate into D-decision references if not corrected.

**Recommendation**: Patch the kickoff spec's path citations before code work begins. Surface scan already identified correct paths; a 5-minute spec-edit pass closes this.

