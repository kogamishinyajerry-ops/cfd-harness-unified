# Editing Cutpoints Manifest — CapCut Assembly Guide for `advisor_moments_final.mp4`

> Target: a single ~5-minute video assembling the 3 raw advisor session recordings into a polished demo asset. Manual editing in CapCut (Chinese: 剪映) — Claude will not drive the GUI. Estimated assembly time: 25-35 minutes.

## Input clips (you record these · see `04_asset_paths.md`)

| File | Duration target | Content |
|---|---|---|
| `recordings/moment_1_raw.mov` | 90-150 s | Fresh Claude Code session · paste engineer block from `moment_1_prompt.md` "## Engineer's input" section · wait for reply · stop recording when reply ends |
| `recordings/moment_2_raw.mov` | 120-180 s | Same flow for Moment 2 |
| `recordings/moment_3_raw.mov` | 120-180 s | Same flow for Moment 3 |

## CapCut project setup

1. New project · 1920×1080 · 30 fps · stereo audio (silent — narration is overlaid live by you during demo)
2. Add `moment_1_raw.mov` to timeline at 0:00

## Per-moment editing recipe

### Moment 1 (target final duration 60-75 s)

| Cut action | Why |
|---|---|
| **Cut-in**: first frame where engineer input is fully visible | Avoid showing your unrelated tab-clicks |
| **Cut-out**: 0.5 s after the last `Advisory only` line of the reply | Avoid trailing dead space |
| **Speed up engineer typing/scrolling sections**: 2× speed on any pure-input segment > 4 s | Keep momentum |
| **Speed up Claude "thinking" indicator**: 3× speed | Audience doesn't need to watch thinking |
| **Add subtitle**: bottom-third overlay reading `Moment 1 · "max_skew 6.87 — can solver run?"` for first 3 s | Frame the segment |
| **Add subtitle**: when corpus-citation block appears, overlay `Cites V84 + V8 + S3 from project corpus` for 2 s | Highlight the load-bearing beat |

### Moment 2 (target final duration 90-110 s)

| Cut action | Why |
|---|---|
| **Cut-in**: first frame where engineer's energy-balance math is fully visible | Anchor the question |
| **Cut-out**: 0.5 s after `Advisory only` | Trim |
| **Speed up "Root cause decomposition" enumeration**: 1.5× if Claude writes slowly | Keep momentum |
| **Add subtitle**: `Moment 2 · "Why is bay 30 % under theoretical?"` for first 3 s | Frame |
| **Add subtitle**: when "What's still usable" section appears, overlay `Honest scope — what to ship vs what to redo` for 3 s | Reinforce honesty value |
| **Add subtitle**: when ETA/cost numbers appear, overlay `Each path quantified: ETA + ARM 4-core core-hours + expected gain` for 3 s | Highlight engineering specificity |

### Moment 3 (target final duration 90-110 s)

| Cut action | Why |
|---|---|
| **Cut-in**: first frame where engineer's budget constraints are visible | Anchor |
| **Cut-out**: 0.5 s after `Advisory only` | Trim |
| **Add subtitle**: `Moment 3 · "7-day ARM 4-core budget — which path first?"` for first 3 s | Frame |
| **Add subtitle**: when the Mon-Sun table renders, overlay `Concrete week plan with explicit Wed/Fri/Sun stop-points` for 3 s | Highlight decision-aid value |
| **Add subtitle**: when "What I'm explicitly Not Recommending" appears, overlay `Advisor names the path it deprioritized — auditable` for 3 s | Reinforce no-blackbox value |
| **Add subtitle**: when "One Question Back" appears, overlay `Advisor asks back — calibrates not assumes` for 3 s | Reinforce advisor-not-driver |

## Transitions between moments

- Between Moment 1 → Moment 2: 1-s black fade + 1-s title card reading `Moment 2 of 3 · Diagnosis`
- Between Moment 2 → Moment 3: 1-s black fade + 1-s title card reading `Moment 3 of 3 · Prioritization`
- No transition at start or end (assume narration handles framing)

## Overall constraints

- **Total final duration**: 4:00–5:00 (Segment 5 budget is 5 min including 30 s of your live narration)
- **Audio**: silent throughout (your live voice over)
- **Resolution**: 1920×1080 minimum (downsample to 1280×720 if file > 200 MB)
- **Codec**: H.264 MP4 (universal compatibility)
- **Subtitle font**: same as terminal in source clips (likely SF Mono or JetBrains Mono); size 32-40 pt; high-contrast color (white with black outline)
- **Export**: `recordings/advisor_moments_final.mp4`

## QA checklist before declaring done

- [ ] Total duration ≤ 5:00
- [ ] All 3 moments end with the `Advisory only` line visible
- [ ] All 6+ subtitle overlays are legible at 1080p (no clipping by terminal scroll)
- [ ] Title cards between moments are 1 s each, not longer
- [ ] No dead time > 2 s anywhere
- [ ] Played at 0.75× speed (test peer-comprehension margin), all engineer prompts + advisor verdicts still readable

## If CapCut export fails

Fall back to QuickTime trim + concatenate (Trim individual clips → File > Open All Three → Add Clip to End → Save As). Quality is lower (no subtitles) but the demo can still run — narrate the per-moment frames live from your cheat sheet (`03_speaking_cheatsheet.md` Segment 5 table).
