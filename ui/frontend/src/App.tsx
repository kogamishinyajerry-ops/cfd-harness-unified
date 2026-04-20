import { Route, Routes } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { AuditPackagePage } from "@/pages/AuditPackagePage";
import { CaseEditorPage } from "@/pages/CaseEditorPage";
import { CaseListPage } from "@/pages/CaseListPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { DecisionsQueuePage } from "@/pages/DecisionsQueuePage";
import { RunMonitorPage } from "@/pages/RunMonitorPage";
import { ValidationReportPage } from "@/pages/ValidationReportPage";

// Path B · Phase 0..5 MVP routes. Phase 5 (Audit Package Builder)
// unblocked 2026-04-20 by DEC-V61-006 (Q-1 closed, Case 6 Path P-2)
// and DEC-V61-011 (Q-2 closed, duct_flow rename).
export default function App() {
  return (
    <Routes>
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
