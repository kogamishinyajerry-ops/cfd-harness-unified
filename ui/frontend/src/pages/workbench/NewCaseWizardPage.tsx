import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/api/client";
import type { TemplateSummary } from "@/types/wizard";

// Stage 8a — Onboarding Workbench wizard. Three-step pedagogical flow:
// (1) pick a starter template, (2) configure parameters via form, (3)
// preview YAML + create draft + jump to run timeline. Strict additive —
// new pages only, no foam_agent_adapter touching, mock execution lives
// inside ui/backend/routes/wizard.py.

type Step = 1 | 2 | 3;

export function NewCaseWizardPage() {
  const navigate = useNavigate();
  const templatesQuery = useQuery({
    queryKey: ["wizard-templates"],
    queryFn: api.listWizardTemplates,
  });

  const [step, setStep] = useState<Step>(1);
  const [selected, setSelected] = useState<TemplateSummary | null>(null);
  const [caseId, setCaseId] = useState<string>("");
  const [nameDisplay, setNameDisplay] = useState<string>("");
  const [params, setParams] = useState<Record<string, number>>({});

  const createMutation = useMutation({
    mutationFn: api.createWizardDraft,
    onSuccess: (res) => navigate(`/workbench/run/${encodeURIComponent(res.case_id)}`),
  });

  // Server-rendered byte-exact preview (Opus round-2 Q11 fix).
  // Client-side string-concat used to invent labels (e.g. `lid_velocity:`)
  // that did not match the server's emit (`top_wall_u:`) — a trust-killer
  // for the onboarding wizard. We now mirror exactly what /draft will
  // write by calling the same render_yaml service via /preview.
  const previewMutation = useMutation({ mutationFn: api.previewWizardYaml });
  const yamlPreview = previewMutation.data?.yaml_text ?? "";

  useEffect(() => {
    if (step !== 3 || !selected) return;
    const handle = setTimeout(() => {
      previewMutation.mutate({
        template_id: selected.template_id,
        case_id: caseId || "<your-case-id>",
        name_display: nameDisplay || null,
        params,
      });
    }, 150); // debounce: avoid flood while user types in step 2 then jumps
    return () => clearTimeout(handle);
    // previewMutation is stable from useMutation hook; intentionally
    // omitted from deps to keep the trigger purely value-driven.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, selected, caseId, nameDisplay, params]);

  const validId = /^[A-Za-z0-9_-]+$/.test(caseId);
  const canCreate =
    selected !== null && validId && caseId.length > 0 && !createMutation.isPending;

  if (templatesQuery.isLoading) {
    return <Section><p className="text-surface-300">Loading templates…</p></Section>;
  }
  if (templatesQuery.isError || !templatesQuery.data) {
    const msg =
      templatesQuery.error instanceof ApiError
        ? `${templatesQuery.error.status}: ${templatesQuery.error.message}`
        : String(templatesQuery.error);
    return (
      <Section>
        <p className="text-sm text-contract-fail">Failed to load templates: {msg}</p>
      </Section>
    );
  }

  return (
    <Section>
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-surface-100">
          新建案例 · Onboarding Workbench
        </h1>
        <p className="mt-1 text-sm text-surface-400">
          从三个起点模板挑一个 → 调几个数 → 看 YAML 预览 → 一键运行 5 阶段流程。
          新手从 0 到第一次跑通基线的最短路径。
        </p>
        <p className="mt-1 text-[11px] text-surface-500">
          Stage 8a · 模拟执行（mock solver）。Stage 8b 落地 line-B 真实 OpenFOAM 调度后，
          这里会切换到真实日志流，前端代码无需改动。
        </p>
      </header>

      <Stepper step={step} />

      {step === 1 && (
        <TemplateGrid
          templates={templatesQuery.data.templates}
          selected={selected}
          onSelect={(t) => {
            setSelected(t);
            // seed defaults
            const initial: Record<string, number> = {};
            for (const p of t.params) initial[p.key] = p.default;
            setParams(initial);
          }}
          onNext={() => selected && setStep(2)}
        />
      )}

      {step === 2 && selected && (
        <ConfigForm
          template={selected}
          caseId={caseId}
          setCaseId={setCaseId}
          nameDisplay={nameDisplay}
          setNameDisplay={setNameDisplay}
          params={params}
          setParams={setParams}
          validId={validId}
          onBack={() => setStep(1)}
          onNext={() => setStep(3)}
        />
      )}

      {step === 3 && selected && (
        <PreviewAndCreate
          yamlPreview={yamlPreview}
          previewLoading={previewMutation.isPending}
          previewError={
            previewMutation.isError ? previewMutation.error : null
          }
          canCreate={canCreate}
          isPending={createMutation.isPending}
          error={createMutation.isError ? createMutation.error : null}
          onBack={() => setStep(2)}
          onCreate={() =>
            createMutation.mutate({
              template_id: selected.template_id,
              case_id: caseId,
              name_display: nameDisplay || null,
              params,
            })
          }
        />
      )}
    </Section>
  );
}

function Section({ children }: { children: React.ReactNode }) {
  return <section className="mx-auto max-w-5xl px-8 py-8">{children}</section>;
}

function Stepper({ step }: { step: Step }) {
  const labels: Record<Step, string> = {
    1: "1 · 选模板",
    2: "2 · 配参数",
    3: "3 · 看预览 → 跑",
  };
  return (
    <nav className="mb-8 flex gap-1.5 text-[11px]">
      {([1, 2, 3] as Step[]).map((s) => (
        <span
          key={s}
          className={`mono rounded-sm px-2 py-1 ${
            s === step
              ? "bg-surface-100 text-surface-950"
              : s < step
                ? "bg-contract-pass/30 text-contract-pass"
                : "bg-surface-800 text-surface-500"
          }`}
        >
          {labels[s]}
        </span>
      ))}
    </nav>
  );
}

function TemplateGrid({
  templates,
  selected,
  onSelect,
  onNext,
}: {
  templates: TemplateSummary[];
  selected: TemplateSummary | null;
  onSelect: (t: TemplateSummary) => void;
  onNext: () => void;
}) {
  return (
    <>
      <div className="grid gap-3 md:grid-cols-3">
        {templates.map((t) => {
          const active = selected?.template_id === t.template_id;
          return (
            <button
              key={t.template_id}
              type="button"
              onClick={() => onSelect(t)}
              className={`group rounded-md border p-4 text-left transition ${
                active
                  ? "border-surface-300 bg-surface-100/5"
                  : "border-surface-800 bg-surface-900/40 hover:border-surface-600"
              }`}
            >
              <div className="mono mb-2 flex items-center justify-between text-[10px] uppercase tracking-wider">
                <span className="text-surface-500">{t.geometry_type}</span>
                <span className="text-surface-500">{t.solver}</span>
              </div>
              <h3 className="text-base font-semibold text-surface-100">{t.name_zh}</h3>
              <p className="mt-0.5 text-[11px] text-surface-500">{t.name_en}</p>
              <p className="mt-3 text-sm leading-relaxed text-surface-300">
                {t.description_zh}
              </p>
              {t.canonical_ref && (
                <p className="mt-3 text-[11px] text-surface-500">
                  ref · {t.canonical_ref}
                </p>
              )}
            </button>
          );
        })}
      </div>
      <div className="mt-6 flex justify-end">
        <button
          type="button"
          disabled={!selected}
          onClick={onNext}
          className="rounded-sm bg-surface-100 px-4 py-2 text-sm text-surface-950 disabled:bg-surface-800 disabled:text-surface-500"
        >
          下一步 · 配参数 →
        </button>
      </div>
    </>
  );
}

function ConfigForm({
  template,
  caseId,
  setCaseId,
  nameDisplay,
  setNameDisplay,
  params,
  setParams,
  validId,
  onBack,
  onNext,
}: {
  template: TemplateSummary;
  caseId: string;
  setCaseId: (v: string) => void;
  nameDisplay: string;
  setNameDisplay: (v: string) => void;
  params: Record<string, number>;
  setParams: (p: Record<string, number>) => void;
  validId: boolean;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      <div>
        <h3 className="mb-2 text-sm font-semibold text-surface-200">案例标识</h3>
        <label className="mb-3 block">
          <span className="mono mb-1 block text-[11px] uppercase tracking-wider text-surface-400">
            case_id
          </span>
          <input
            value={caseId}
            onChange={(e) => setCaseId(e.target.value)}
            placeholder="my_first_cavity"
            className="mono w-full rounded-sm border border-surface-800 bg-surface-900 px-3 py-2 text-sm text-surface-100 outline-none focus:border-surface-500"
          />
          <span className="mt-1 block text-[11px] text-surface-500">
            字母 / 数字 / 下划线 / 连字符。例：{" "}
            <span className="mono">my_first_cavity</span>
          </span>
          {!validId && caseId.length > 0 && (
            <span className="mt-1 block text-[11px] text-contract-fail">
              非法字符 — 只能含 A-Z a-z 0-9 _ -
            </span>
          )}
        </label>
        <label className="block">
          <span className="mono mb-1 block text-[11px] uppercase tracking-wider text-surface-400">
            name_display (optional)
          </span>
          <input
            value={nameDisplay}
            onChange={(e) => setNameDisplay(e.target.value)}
            placeholder={`${template.name_zh} · ${caseId || "<your-case-id>"}`}
            className="w-full rounded-sm border border-surface-800 bg-surface-900 px-3 py-2 text-sm text-surface-100 outline-none focus:border-surface-500"
          />
        </label>
      </div>
      <div>
        <h3 className="mb-2 text-sm font-semibold text-surface-200">物理参数</h3>
        <div className="space-y-3">
          {template.params.map((p) => (
            <label key={p.key} className="block">
              <div className="mb-1 flex items-baseline justify-between">
                <span className="text-sm text-surface-200">{p.label_zh}</span>
                <span className="mono text-[11px] text-surface-500">
                  {p.label_en}
                  {p.unit ? ` · ${p.unit}` : ""}
                </span>
              </div>
              <input
                type="number"
                step="any"
                min={p.min ?? undefined}
                max={p.max ?? undefined}
                value={params[p.key] ?? p.default}
                onChange={(e) =>
                  setParams({ ...params, [p.key]: Number(e.target.value) })
                }
                className="mono w-full rounded-sm border border-surface-800 bg-surface-900 px-3 py-2 text-sm text-surface-100 outline-none focus:border-surface-500"
              />
              {p.help_zh && (
                <span className="mt-1 block text-[11px] text-surface-500">
                  {p.help_zh}
                </span>
              )}
            </label>
          ))}
        </div>
      </div>
      <div className="md:col-span-2 mt-4 flex justify-between">
        <button
          type="button"
          onClick={onBack}
          className="rounded-sm border border-surface-800 px-4 py-2 text-sm text-surface-300 hover:border-surface-600"
        >
          ← 上一步
        </button>
        <button
          type="button"
          disabled={!validId || caseId.length === 0}
          onClick={onNext}
          className="rounded-sm bg-surface-100 px-4 py-2 text-sm text-surface-950 disabled:bg-surface-800 disabled:text-surface-500"
        >
          下一步 · 看 YAML →
        </button>
      </div>
    </div>
  );
}

function PreviewAndCreate({
  yamlPreview,
  previewLoading,
  previewError,
  canCreate,
  isPending,
  error,
  onBack,
  onCreate,
}: {
  yamlPreview: string;
  previewLoading: boolean;
  previewError: unknown;
  canCreate: boolean;
  isPending: boolean;
  error: unknown;
  onBack: () => void;
  onCreate: () => void;
}) {
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-surface-200">YAML 预览</h3>
        <span className="mono text-[10px] uppercase tracking-wider text-surface-500">
          {previewLoading
            ? "rendering..."
            : previewError
              ? "render error"
              : "server-rendered · byte-exact"}
        </span>
      </div>
      <pre className="mono overflow-x-auto rounded-sm border border-surface-800 bg-surface-950 p-4 text-[12px] leading-relaxed text-surface-200">
        {yamlPreview ||
          (previewLoading
            ? "正在生成 YAML..."
            : previewError
              ? `预览生成失败：${
                  previewError instanceof ApiError
                    ? `${previewError.status}: ${previewError.message}`
                    : previewError instanceof Error
                      ? previewError.message
                      : String(previewError)
                }`
              : "")}
      </pre>
      <p className="mt-3 text-[11px] text-surface-500">
        预览内容与点击「创建并跑」后真正落盘的 YAML{" "}
        <span className="text-surface-300">逐字节一致</span>（同一服务端
        render_yaml 调用）。落盘路径：
        <span className="mono">
          ui/backend/user_drafts/&lt;case_id&gt;.yaml
        </span>
        。
      </p>
      {error ? (
        <p className="mt-3 text-sm text-contract-fail">
          创建失败：
          {error instanceof ApiError
            ? `${error.status}: ${error.message}`
            : error instanceof Error
              ? error.message
              : String(error)}
        </p>
      ) : null}
      <div className="mt-6 flex justify-between">
        <button
          type="button"
          onClick={onBack}
          className="rounded-sm border border-surface-800 px-4 py-2 text-sm text-surface-300 hover:border-surface-600"
        >
          ← 上一步
        </button>
        <button
          type="button"
          disabled={!canCreate}
          onClick={onCreate}
          className="rounded-sm bg-contract-pass px-4 py-2 text-sm font-medium text-surface-950 disabled:bg-surface-800 disabled:text-surface-500"
        >
          {isPending ? "创建中..." : "创建并跑 ▶"}
        </button>
      </div>
    </div>
  );
}
