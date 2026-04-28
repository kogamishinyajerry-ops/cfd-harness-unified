import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { LearnLayout } from "@/components/learn/LearnLayout";
import { AuditPackagePage } from "@/pages/AuditPackagePage";
import { CaseEditorPage } from "@/pages/CaseEditorPage";
import { CaseListPage } from "@/pages/CaseListPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { DecisionsQueuePage } from "@/pages/DecisionsQueuePage";
import { LearnCaseDetailPage } from "@/pages/learn/LearnCaseDetailPage";
import { LearnHomePage } from "@/pages/learn/LearnHomePage";
import { ValidationReportPage } from "@/pages/ValidationReportPage";
import { EditCasePage } from "@/pages/workbench/EditCasePage";
import { ImportPage } from "@/pages/workbench/ImportPage";
import { MeshWizardPage } from "@/pages/workbench/MeshWizardPage";
import { NewCaseWizardPage } from "@/pages/workbench/NewCaseWizardPage";
import { RunComparePage } from "@/pages/workbench/RunComparePage";
import { RunDetailPage } from "@/pages/workbench/RunDetailPage";
import { RunHistoryPage } from "@/pages/workbench/RunHistoryPage";
import { StepPanelShell } from "@/pages/workbench/StepPanelShell";
import { WorkbenchIndexPage } from "@/pages/workbench/WorkbenchIndexPage";
import { WorkbenchRunPage } from "@/pages/workbench/WorkbenchRunPage";
import { WorkbenchTodayPage } from "@/pages/workbench/WorkbenchTodayPage";

// Demo-first routing (convergence round, 2026-04-22): the default landing is
// now the /learn shell — the student-facing catalog of 10 canonical cases.
// Pro Workbench (evidence-heavy validation / decisions / audit package) stays
// mounted under /pro and every /learn case has a "进入专业工作台 →" hook.
//
// Rationale: the workbench builds credibility but the demo story starts from
// "ten canonical flows, honest comparison against literature". Landing on the
// dashboard surfaced governance jargon (Phase 8 Sprint 1, attestor, gates,
// verdict split) before the user had any anchor case to tie them to. Flipping
// the default solves that without touching either shell internally.
export default function App() {
  return (
    <Routes>
      {/* Default: redirect / → /learn */}
      <Route index element={<Navigate to="/learn" replace />} />

      {/* Student-facing learn shell */}
      <Route path="/learn" element={<LearnLayout />}>
        <Route index element={<LearnHomePage />} />
        <Route path="cases/:caseId" element={<LearnCaseDetailPage />} />
      </Route>

      {/* Pro Workbench (Phase 0..5 evidence surface). Dashboard lives at /pro
          so the existing Dashboard "cards" layout still works for power users
          while it's one click further from the demo front door. Every
          evidence sub-route (decisions/runs/audit-package/cases) keeps its
          canonical top-level path so existing deep-links still resolve. */}
      <Route element={<Layout />}>
        <Route path="/pro" element={<DashboardPage />} />
        <Route path="/cases" element={<CaseListPage />} />
        <Route path="/cases/:caseId/report" element={<ValidationReportPage />} />
        <Route path="/cases/:caseId/edit" element={<CaseEditorPage />} />
        <Route path="/decisions" element={<DecisionsQueuePage />} />
        {/* /runs and /runs/:caseId removed 2026-04-26 (M1) — Phase-3 synthetic
            residual stream retired. Real solver SSE lives at
            /workbench/run/:caseId driven by RealSolverDriver. */}
        <Route path="/audit-package" element={<AuditPackagePage />} />
        {/* Workbench 60-day extension (2026-04-26) · landing index — case
            picker grid for the closed-loop entry point so users don't have
            to know case_ids by URL. */}
        <Route path="/workbench" element={<WorkbenchIndexPage />} />
        {/* Workbench 60-day extension #3 (2026-04-26) · cross-case "today's
            runs" feed grouped by local-tz date. */}
        <Route path="/workbench/today" element={<WorkbenchTodayPage />} />
        {/* Stage 8a · Onboarding Workbench — newcomer's first-case wizard */}
        <Route path="/workbench/new" element={<NewCaseWizardPage />} />
        {/* M5.0 (2026-04-27) · STL case import — workbench-side upload that
            ingests via trimesh + scaffolds an OpenFOAM case dir and routes
            to /workbench/case/:caseId/edit. Imported cases get
            source_origin=imported_user; M5.1 will hard-cap their verdicts
            at PASS_WITH_DISCLAIMER on the trust-core path. */}
        <Route path="/workbench/import" element={<ImportPage />} />
        <Route path="/workbench/run/:caseId" element={<WorkbenchRunPage />} />
        {/* M-PANELS (2026-04-28 · DEC-V61-096) · three-pane workbench
            shell · 5-step tree (Import / Mesh / Setup / Solve / Results)
            + [AI 处理] / [上一步] / [下一步] button contract per Pivot
            Charter Addendum 3 §3. Skeleton ships placeholder bodies for
            every step; step-by-step wireup lands in spec_v2 §E Steps 3-6. */}
        <Route path="/workbench/case/:caseId" element={<StepPanelShell />} />
        {/* M2 (2026-04-26) · Workbench Closed-Loop main-line — param-form
            editor for an existing whitelist case. Saves to user_drafts/ and
            navigates to /workbench/run/:caseId where RealSolverDriver picks
            up the override (CFD_HARNESS_WIZARD_SOLVER=real). */}
        <Route path="/workbench/case/:caseId/edit" element={<EditCasePage />} />
        {/* M6.0 (2026-04-27) · Mesh Wizard — gmsh-based unstructured mesh
            generation for imported cases. Writes constant/polyMesh/ via
            gmsh + gmshToFoam (cfd-openfoam container). M7 will fill in
            the M5.0 sHM stub on a separate path. */}
        <Route path="/workbench/case/:caseId/mesh" element={<MeshWizardPage />} />
        {/* M3 (2026-04-26) · Run history — newest-first table of past
            real-solver runs for a case, plus per-run detail page. SSE
            run_done in WorkbenchRunPage auto-jumps to the detail. */}
        <Route path="/workbench/case/:caseId/runs" element={<RunHistoryPage />} />
        <Route path="/workbench/case/:caseId/run/:runId" element={<RunDetailPage />} />
        {/* Workbench 60-day extension (2026-04-26) · two-up overlay of two
            runs of the same case. Reads run IDs from ?a=…&b=… so the URL is
            shareable. Reuses /run-history/{run_id} detail surface for data. */}
        <Route path="/workbench/case/:caseId/compare" element={<RunComparePage />} />
        <Route path="*" element={<Navigate to="/learn" replace />} />
      </Route>
    </Routes>
  );
}
