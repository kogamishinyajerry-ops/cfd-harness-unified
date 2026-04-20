import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { CaseListPage } from "@/pages/CaseListPage";
import { ValidationReportPage } from "@/pages/ValidationReportPage";

// Phase 0 routes only. Cases list + Screen 4 (Validation Report).
// Phases 1..5 land their routes on top of this skeleton without
// changing the shell — see docs/ui_roadmap.md.
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/cases" replace />} />
        <Route path="/cases" element={<CaseListPage />} />
        <Route
          path="/cases/:caseId/report"
          element={<ValidationReportPage />}
        />
        <Route path="*" element={<Navigate to="/cases" replace />} />
      </Route>
    </Routes>
  );
}
