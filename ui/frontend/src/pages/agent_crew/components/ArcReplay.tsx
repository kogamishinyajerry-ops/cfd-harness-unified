// ArcReplay — shows the collaboration steps for a selected CrewArc
// and drives the topology graph via activeEdgeIds.
// V93 · Agent Crew Observatory

import { useState, useEffect, useRef } from "react";
import type { CrewArc } from "@/api/agentCrew";

// Verdict → color class (tailwind v4 tokens)
export function verdictColor(verdict: string): string {
  if (verdict === "APPROVE") return "bg-v4-healthy/20 text-v4-healthy border-v4-healthy/30";
  if (verdict === "APPROVE_WITH_COMMENTS")
    return "bg-yellow-500/10 text-yellow-400 border-yellow-500/30";
  if (verdict === "CHANGES_REQUIRED")
    return "bg-v4-active/20 text-v4-active border-v4-active/30";
  // UNPARSED / MISSING / anything else → gray
  return "bg-surface-700/40 text-surface-400 border-surface-700/30";
}

interface Step {
  id: string;
  label: string;
  edgeIds: string[];
  artifactKey?: string; // for inspector focus
}

function buildSteps(arc: CrewArc): Step[] {
  const steps: Step[] = [];
  if (arc.loop_auditor) {
    steps.push({
      id: "loop_auditor",
      label: "loop-auditor 设计审",
      edgeIds: ["e6"],
    });
  }
  steps.push({
    id: "chief_impl",
    label: "总师实现",
    edgeIds: ["e1", "e2", "e3"],
  });
  arc.codex_rounds.forEach((r, i) => {
    steps.push({
      id: `codex_r${r.round}`,
      label: `Codex R${r.round} · ${r.verdict}`,
      edgeIds: ["e4", "e5"],
      artifactKey: `codex_r${r.round}`,
    });
    // 步骤只从真实工件推导：仅当存在后续一轮审查时才插入「总师修复」——
    // 后续轮的存在就是修复发生过的证据；末轮之后从不虚构修复步
    //（Codex V93 R0 P2）。
    if (i < arc.codex_rounds.length - 1) {
      steps.push({
        id: `chief_fix_r${r.round}`,
        label: `总师修复 (after R${r.round})`,
        edgeIds: ["e1", "e2", "e3"],
      });
    }
  });
  // 末步诚实化：只有末轮 verdict 是放行类（APPROVE / APPROVE_WITH_COMMENTS /
  // RESOLVED）或没有任何 Codex 轮（如 spike/无审查 DEC）才显示「收口」；
  // 否则如实显示「未收口 · 最后一轮 <verdict>」。
  const last = arc.codex_rounds[arc.codex_rounds.length - 1];
  const closed =
    !last ||
    last.verdict === "APPROVE" ||
    last.verdict === "APPROVE_WITH_COMMENTS" ||
    last.verdict === "RESOLVED";
  steps.push(
    closed
      ? { id: "archive", label: "收口 / 归档", edgeIds: ["e8"] }
      : {
          id: "unresolved",
          label: `未收口 · 最后一轮 ${last.verdict}`,
          edgeIds: [],
        },
  );
  return steps;
}

interface ArcReplayProps {
  arc: CrewArc;
  onActiveEdgesChange: (edgeIds: string[]) => void;
  onStepClick?: (stepId: string) => void;
}

export function ArcReplay({
  arc,
  onActiveEdgesChange,
  onStepClick,
}: ArcReplayProps) {
  const steps = buildSteps(arc);
  const [currentStep, setCurrentStep] = useState<number>(-1);
  const [playing, setPlaying] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // When arc changes, reset
  useEffect(() => {
    setCurrentStep(-1);
    setPlaying(false);
    onActiveEdgesChange([]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [arc.decision_id]);

  // Propagate active edges upward
  useEffect(() => {
    if (currentStep < 0) {
      onActiveEdgesChange([]);
    } else {
      onActiveEdgesChange(steps[currentStep]?.edgeIds ?? []);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentStep]);

  // Auto-play
  useEffect(() => {
    if (playing) {
      timerRef.current = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev >= steps.length - 1) {
            setPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 1200);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, steps.length]);

  function handlePlay() {
    if (currentStep >= steps.length - 1) {
      // restart
      setCurrentStep(-1);
    }
    setPlaying(true);
  }

  function handlePause() {
    setPlaying(false);
  }

  function handleReset() {
    setPlaying(false);
    setCurrentStep(-1);
  }

  return (
    <div className="mt-3">
      <div className="mb-2 flex items-center gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-v4-textSecondary">
          协作回路回放
        </span>
        <button
          type="button"
          onClick={playing ? handlePause : handlePlay}
          className="rounded-sm border border-v4-border bg-v4-surfaceRaised px-2 py-0.5 text-[10px] text-v4-textSecondary hover:border-v4-borderActive hover:text-v4-textPrimary"
        >
          {playing ? "⏸ 暂停" : "▶ 回放"}
        </button>
        <button
          type="button"
          onClick={handleReset}
          className="rounded-sm border border-v4-border bg-v4-surfaceRaised px-2 py-0.5 text-[10px] text-v4-textSecondary hover:border-v4-borderActive hover:text-v4-textPrimary"
        >
          ↺ 重置
        </button>
      </div>

      <ol className="space-y-1">
        {steps.map((step, idx) => {
          const active = idx === currentStep;
          const done = idx < currentStep;
          return (
            <li
              key={step.id}
              onClick={() => {
                setCurrentStep(idx);
                if (step.artifactKey) onStepClick?.(step.artifactKey);
              }}
              className={[
                "flex cursor-pointer items-center gap-2 rounded-sm border px-2 py-1 text-[11px] transition-colors",
                active
                  ? "border-v4-active/50 bg-v4-active/10 text-v4-active"
                  : done
                    ? "border-v4-border bg-v4-surface text-v4-textSecondary"
                    : "border-transparent bg-transparent text-v4-textTertiary",
              ].join(" ")}
            >
              <span
                className={[
                  "inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[9px] font-bold",
                  active
                    ? "bg-v4-active text-black"
                    : done
                      ? "bg-v4-healthy/70 text-black"
                      : "bg-surface-700 text-surface-400",
                ].join(" ")}
              >
                {idx + 1}
              </span>
              <span className="truncate">{step.label}</span>
              {/* Show round verdict badges for codex steps */}
              {step.id.startsWith("codex_r") && (() => {
                const rn = parseInt(step.id.replace("codex_r", ""), 10);
                const round = arc.codex_rounds.find((r) => r.round === rn);
                if (!round) return null;
                return (
                  <span
                    className={[
                      "ml-auto shrink-0 rounded-sm border px-1 py-0.5 text-[9px]",
                      verdictColor(round.verdict),
                    ].join(" ")}
                    title={round.verdict}
                  >
                    {round.verdict}
                  </span>
                );
              })()}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
