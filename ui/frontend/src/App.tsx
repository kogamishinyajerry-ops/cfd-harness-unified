import { Route, Routes } from "react-router-dom";

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

// Path B · Phase 0..5 MVP routes (Pro Workbench under /) + student-
// facing demo under /learn (LearnLayout). The /learn tree is a separate
// shell — softer typography, no sidebar, top-nav only — that speaks to
// CFD learners. Evidence-heavy features (audit, decisions, run monitor)
// stay under / and are reachable via "Pro Workbench →" link.
export default function App() {
  return (
    <Routes>
      {/* Student-facing learn shell */}
      <Route path="/learn" element={<LearnLayout />}>
        <Route index element={<LearnHomePage />} />
        <Route path="cases/:caseId" element={<LearnCaseDetailPage />} />
      </Route>

      {/* Pro Workbench (existing Phase 0..5 routes) */}
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="/cases" element={<CaseListPage />} />
        <Route path="/cases/:caseId/report" element={<ValidationReportPage />} />
        <Route path="/cases/:caseId/edit" element={<CaseEditorPage />} />
        <Route path="/decisions" element={<DecisionsQueuePage />} />
        <Route path="/runs" element={<RunMonitorPage />} />
        <Route path="/runs/:caseId" element={<RunMonitorPage />} />
        <Route path="/audit-package" element={<AuditPackagePage />} />
        <Route path="*" element={<DashboardPage />} />
      </Route>
    </Routes>
  );
}
