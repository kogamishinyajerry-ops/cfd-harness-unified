import { Route, Routes } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { CaseEditorPage } from "@/pages/CaseEditorPage";
import { CaseListPage } from "@/pages/CaseListPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { DecisionsQueuePage } from "@/pages/DecisionsQueuePage";
import { RunMonitorPage } from "@/pages/RunMonitorPage";
import { ValidationReportPage } from "@/pages/ValidationReportPage";

// Path B · Phase 0..4 MVP routes. Phase 5 (audit package) is still
// disabled in the left nav pending Q-1 / Q-2 external-Gate resolution.
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
        <Route path="*" element={<DashboardPage />} />
      </Route>
    </Routes>
  );
}
