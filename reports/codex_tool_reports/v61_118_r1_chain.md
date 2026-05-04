# DEC-V61-118 · LLM provider foundation · Codex pre-merge chain

**Backend**: 86gs `gpt-5.4` xhigh (R1-R8) · CRS `gpt-5.4` high (R9 fallback after 86gs 522)
**Trigger**: RETRO-V61-001 multi-file backend + new operator endpoint + external-API integration + secrets handling
**Scope**: 9 files initial · grew to ~1700 LOC across `services/llm_provider/`, `routes/ai_chat.py`, `main.py`, tests, DEC
**Self-estimated pass rate**: 40% (predicted 4-6 rounds)
**Actual**: 9 rounds — meaningful overrun, cascade on eviction-cleanup design

---

## Round-by-round summary

| Round | Commit | Findings | Severity | Verdict | Backend |
|---|---|---|---|---|---|
| R1 | 667b120 | 3 | P1+P2+P3 | CHANGES_REQUIRED | 86gs xhigh |
| R2 | 129f973 | 2 | P1+P2 | CHANGES_REQUIRED | 86gs xhigh |
| R3 | 97bdc38 | 2 | P2×2 | CHANGES_REQUIRED | 86gs xhigh |
| R4 | db611a0 | 2 | P1+P2 | CHANGES_REQUIRED | 86gs xhigh |
| R5 | 5cbeb00 | 1 | P1 | CHANGES_REQUIRED | 86gs xhigh |
| R6 | 59111b8 | 1 | P2 | CHANGES_REQUIRED | 86gs xhigh |
| R7 | dc04f86 | 2 | P1×2 | CHANGES_REQUIRED | 86gs xhigh |
| R8 | 6b6765e | 1 | P2 | CHANGES_REQUIRED | 86gs xhigh |
| R9 | 583bc81 | 0 | — | **APPROVE clean** | CRS high (86gs 522 fallback) |

---

## Round 1 · CHANGES_REQUIRED · 1 P1 + 1 P2 + 1 P3

- **P1 · loopback-only contract**: `/api/ai-chat` is unauthenticated → an exposed deployment becomes an open relay for billable LLM traffic. Fixed in R2 with loopback guard + `AI_CHAT_ALLOW_NON_LOOPBACK` env override.
- **P2 · 4xx fallback retry**: 400/422 (e.g. context_length_exceeded) was retried against flash, masking actionable client errors. Fixed in R2 with new `LLMBadRequestError` that bypasses fallback, route maps to 400.
- **P3 · AsyncClient per call**: lazy-create-and-discard disabled connection pooling. Fixed in R2 with singleton provider + persistent client.

## Round 2 · CHANGES_REQUIRED · 1 P1 + 1 P2

- **P1 · same-host reverse proxy bypass**: nginx/Caddy on 127.0.0.1 makes `client.host=127.0.0.1` even for remote callers. Fixed in R3: also reject when X-Forwarded-For/X-Real-IP/Forwarded headers present (override unlocks).
- **P2 · same-length key fingerprint collision**: length-only fingerprint collided on uniform-length DeepSeek key rotations. Fixed in R3 with SHA-256 fingerprint.

## Round 3 · CHANGES_REQUIRED · 2 P2

- **P2-1 · audit log uses proxy peer**: when proxy-headers trip the guard, log recorded loopback proxy not real caller. Fixed in R4 by extracting forwarded IP.
- **P2-2 · evicted provider not closed**: same-length rotation rebuild path leaked old AsyncClient. Fixed in R4 with `_schedule_aclose` (this fix opened the cascade).

## Round 4 · CHANGES_REQUIRED · 1 P1 + 1 P2

- **P1 · XFF leftmost-hop is client-controlled**: trusting `xff.split(",")[0]` lets attacker spoof "the caller". Fixed in R5: log full chain verbatim.
- **P2 · close-eager races in-flight**: `_schedule_aclose(evicted)` could close while old singleton was still serving a request. Fixed in R5 with 90s delay.

## Round 5 · CHANGES_REQUIRED · 1 P1

- **P1 · 90s delay too short**: chat() can run primary (60s) + fallback (60s) = 120s. Fixed in R6 with `MAX_CHAT_DURATION_SECONDS = 2 × read_timeout = 120s`, +30s buffer.

## Round 6 · CHANGES_REQUIRED · 1 P2

- **P2 · pool/connect timeouts compound**: time-based delay still incorrect because pool waits aren't bounded. Fixed in R7 with drain-based aclose (refcount in-flight, aclose blocks until count=0).

## Round 7 · CHANGES_REQUIRED · 2 P1

- **P1-1 · drain refcount not thread-safe**: chat() drain check + inflight increment is atomic only within a single asyncio loop. Multi-thread scenarios could race.
- **P1-2 · sync `asyncio.run(aclose())` cross-loop wait unsafe**: drain signal can't reach across event loops.
- **Resolution in R8**: STEP BACK — drop the eviction-close machinery entirely. V1 deployment is single-loop, no in-process key rotation. Document as unsupported V1 scope; lifespan-shutdown is the only documented close path.

## Round 8 · CHANGES_REQUIRED · 1 P2

- **P2 · documented lifespan-shutdown but didn't wire it**: `main.py` had no lifespan hook so cached provider's AsyncClient was never closed in real deployments. Fixed in R9 with `@asynccontextmanager` lifespan + `close_cached_provider()` factory helper.

## Round 9 · APPROVE clean · 0 findings

**Backend**: CRS `gpt-5.4` high. 86gs hit Cloudflare 522 (twice in succession); fell back to CRS per `CLAUDE.md` relay protocol. CRS effort downgrade (xhigh → high) noted in DEC frontmatter `codex_review_relay` field.

**Codex finding (verbatim)**: "I did not find any discrete, actionable bugs in commit 583bc81. The new lifespan shutdown hook and cached-provider close path are consistent with the existing singleton design and the added tests cover the intended behavior."

---

## Methodology lessons

### L1 · Cleanup mechanism cascade is a real pattern

Findings R3 P2-2 → R4 P2 → R5 P1 → R6 P2 → R7 P1×2 form a single chain: each fix to the close-on-eviction logic introduced a new race surface that the next reviewer surfaced. Total 5 rounds spent on eviction-cleanup before the right answer (drop it; lifespan-only) emerged in R8.

**Pattern**: when a single architectural mechanism has multiple correctness axes (here: timing, concurrency, atomicity, cross-thread, cross-loop), and each axis is independent, iterative fixes ADD complexity rather than CONVERGE. The discipline: at the third or fourth iteration on a single mechanism, ask "is this mechanism necessary?" and consider removal/simplification.

V61-118 hit this at R7 → R8 (5 rounds in). V61-117 hit a different version at R3 → R4 (3 rounds in: walking back the auto-vs-manual origin tagging). Both arcs converged by **simplifying not adding**.

### L2 · Calibration anchor: external-API integration with cleanup contract

V61-118 prediction (40% / 4-6 rounds) underestimated significantly. Actual: 9 rounds. The miss was concentrated entirely in the eviction-cleanup mechanism — the LLM call path itself (R1 errors mapping, fallback chain, secrets handling) closed quickly.

Anchor refinement: "External-API integration with PERSISTENT-CLIENT cleanup contract" deserves its own anchor at ~25% / 7-9 rounds. The cleanup contract has multiple correctness axes (R3-R7) that compound; the API call path itself is well-trodden.

### L3 · Honest tradeoff disclosure unblocks closure

R7 → R8 transition was a deliberate scope-down. The DEC's risk register R6 was added explicitly disclosing in-process key rotation as unsupported. Codex R8 didn't object to the scope-down; it found the next logical issue (the documented hook wasn't wired). R9 closed cleanly because the disclosed scope was actually delivered.

**Discipline**: when a Codex finding pushes you toward a design that opens new races, write the trade-off into the DEC's risk register and step back. Reviewers prefer documented limits over fragile mechanisms.

### L4 · Multi-relay resilience matters

R9 hit 86gs 522 (twice). Per `CLAUDE.md` relay protocol, fell back to CRS with documented effort downgrade in DEC frontmatter. Total wall-clock impact: ~5 minutes vs. waiting for 86gs to recover. Without the documented fallback path, V61-118 would have stalled.

---

## Risk register impact (DEC §risk register R6 added)

V61-118 §risk register grew from 5 entries (R1-R5 written before R7) to 6 (R6 added at R7→R8 transition documenting in-process key rotation as out-of-V1-scope). This is the second instance in the V61-115..118 arc where a Codex chain forced a documented scope reduction (V61-117's R2/R3 also flagged a UX scope question that landed as a DEC trade-off note).

---

## Files comprising V61-118

```
.planning/decisions/2026-05-04_v61_118_llm_provider_integration.md
ui/backend/services/llm_provider/
  __init__.py
  base.py
  deepseek.py
  factory.py
ui/backend/routes/ai_chat.py
ui/backend/main.py (lifespan + router registration)
ui/backend/tests/test_llm_provider.py
ui/backend/tests/test_ai_chat_route.py
```

62 tests pass (test_llm_provider 41 + test_ai_chat_route 21). Backend baseline 1039 pass, 5 pre-existing unrelated failures.
