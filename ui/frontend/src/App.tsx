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
import { RunMonitorPage } from "@/pages/RunMonitorPage";
import { ValidationReportPage } from "@/pages/ValidationReportPage";
import { NewCaseWizardPage } from "@/pages/workbench/NewCaseWizardPage";
import { WorkbenchRunPage } from "@/pages/workbench/WorkbenchRunPage";

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
        <Route path="/runs" element={<RunMonitorPage />} />
        <Route path="/runs/:caseId" element={<RunMonitorPage />} />
        <Route path="/audit-package" element={<AuditPackagePage />} />
        {/* Stage 8a · Onboarding Workbench — newcomer's first-case wizard */}
        <Route path="/workbench/new" element={<NewCaseWizardPage />} />
        <Route path="/workbench/run/:caseId" element={<WorkbenchRunPage />} />
        <Route path="*" element={<Navigate to="/learn" replace />} />
      </Route>
    </Routes>
  );
}
