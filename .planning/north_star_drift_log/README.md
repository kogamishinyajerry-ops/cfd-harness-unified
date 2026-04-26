# North-Star Drift Log · §11.3 (DEC-V61-072 + RETRO-V61-005 · 2026-04-26)

> **Active provisional** pending CFDJerry sign-off. Active until further notice.

## Purpose

On the 1st of each month, the maintainer (CFDJerry) reviews the most recent 4
weeks of commits + DECs against the Pivot Charter v1.0-pivot North Star:

- **OpenFOAM 是唯一真相源** — surrogate is plugin-only, never produces canonical numerical artifacts.
- **surrogate 仅作 plugin / initializer / screener / ranker** — never participates in TrustGate verdicts.
- **Knowledge Protocol 先于功能发散** — no new `knowledge/**` schema fields before P4 KOM Active.
- **四层架构 import 方向不可反向** — Execution does not import Evaluation; Evaluation does not import Execution; cross-plane orchestration only via TaskRunner.

## Cadence

- **By 1st of each month**: spawn a fresh `<YYYY-MM>.md` file in this directory.
- **By 5th of each month**: at-least one entry filed.
- **By 12th of each month**: file is mandatory; CI step `north-star-drift-check` HARD-fails when missing for >12 days.

Skipping one month is recorded as `drift_check_skipped` in STATE.md. Two
consecutive skips trigger an Opus 4.7 Gate review of the Pivot Charter itself.

## Template

Each `<YYYY-MM>.md` file uses this template (see `_template.md`):

```yaml
---
month: 2026-MM
authored_at: <ISO-8601 date>
authored_by: <maintainer name>
window: 2026-MM-01 → 2026-MM-30
---

## Commits reviewed
<git log --since=...>

## DECs reviewed
<list of DEC-V61-XXX from .planning/decisions/ in window>

## North-star alignment

### OpenFOAM 是唯一真相源
- Verdict: ALIGNED / DRIFT_DETECTED
- Evidence: <commits/DECs that confirm or violate>

### surrogate 仅作 plugin / initializer / screener / ranker
- Verdict: ...
- Evidence: ...

### Knowledge Protocol 先于功能发散
- Verdict: ...
- Evidence: ...

### 四层架构 import 方向不可反向
- Verdict: ...
- Evidence: <ADR-001 import-linter results in window>

## Drift incidents (if any)

<For each: incident description · severity · remediation plan · DEC reference>

## Recommendations

<Forward-looking suggestions for next month>
```

## Authority

Methodology v2.0 §11.3 + Pivot Charter v1.0-pivot Risk-1 mitigation
(治理层叙事 drift). Active provisional pending CFDJerry sign-off in
Decisions DB.
