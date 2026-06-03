import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { AuditPackagePage } from "@/pages/AuditPackagePage";
import { DecisionsQueuePage } from "@/pages/DecisionsQueuePage";
import { ValidationReportPage } from "@/pages/ValidationReportPage";
import { WorkflowMonitorPage } from "@/pages/workflow_monitor/WorkflowMonitorPage";
import { ShortcutPalette } from "@/components/ShortcutPalette";
import { ThemeRoot } from "@/components/ThemeRoot";
import { WorkbenchShellV4 } from "@/pages/workbench/v4/WorkbenchShellV4";

// 2026-05-18 · Industrial-minimalist pivot · DIRECT CUT
// ----------------------------------------------------
// All V3-era workbench routes (case picker / wizards / 5-step shell /
// /learn teaching catalog / /pro dashboard / parallel /workbench/v3) were
// REMOVED from routing per user directive "直接砍掉，直奔新的蓝图图集UI".
//
// Source files preserved (not deleted) so the audit trail stays clean and
// any per-page logic can be referenced when wiring real data into V4
// during Phase B / D-real-3D. Catch-all redirect below means stale
// external deep-links land on /workbench (V4) instead of 404.
//
// Removed routes (each previously mounted a distinct page):
//   /learn · /learn/cases/:id      (teaching-case catalog · pivot violated)
//   /cases                          (case list · exposes teaching cases)
//   /pro                            (old dashboard · superseded by V4)
//   /workbench (old)                (WorkbenchIndexPage case picker)
//   /workbench/today                (cross-case runs feed)
//   /workbench/new                  (NewCaseWizardPage)
//   /workbench/tutorial             (TutorialPage)
//   /workbench/import               (ImportPage · STL upload — will rebuild as V4 mode)
//   /workbench/run/:caseId          (WorkbenchRunPage)
//   /workbench/case/:id             (StepPanelShell · V3 5-step)
//   /workbench/case/:id/edit        (EditCasePage)
//   /workbench/case/:id/mesh        (MeshWizardPage)
//   /workbench/case/:id/runs        (RunHistoryPage)
//   /workbench/case/:id/run/:rid    (RunDetailPage)
//   /workbench/case/:id/compare     (RunComparePage)
//   /workbench/v3 · /v3/case/:id    (WorkbenchShellV3 parallel)
//   /workbench/v4 · /v4/case/:id    (consolidated into /workbench root)
//   /workbench/dev/viewport-mode    (V68 dev harness)
//
// Kept (audit/evidence surfaces, NOT workbench shell):
//   /workbench · /workbench/case/:id   → WorkbenchShellV4 (the ONLY shell now)
//   /audit-package                      → AuditPackagePage
//   /decisions                          → DecisionsQueuePage
//   /cases/:id/report                   → ValidationReportPage (deep-link evidence)
//
// Tracked in .planning/transitions/2026-05-18_industrial_minimalist_pivot.md
// + 2026-05-18_blueprint_read.md (Phase E `cutover` step now done early).
export default function App() {
  return (
    <>
      <ThemeRoot />
      <ShortcutPalette />
      <Routes>
        <Route index element={<Navigate to="/workbench" replace />} />

        {/* V4 industrial-minimalist workbench · THE only workbench shell */}
        <Route path="/workbench" element={<WorkbenchShellV4 />} />
        <Route path="/workbench/case/:caseId" element={<WorkbenchShellV4 />} />

        {/* Evidence surfaces · kept inside Layout chrome. These are
            audit-trail destinations, not workbench shell views. */}
        <Route element={<Layout />}>
          {/* DEC-V61-226 · Workflow Monitor (in-house, mock-first design
              preview). Observation surface — NOT the frozen workbench shell. */}
          <Route path="/workflow-monitor" element={<WorkflowMonitorPage />} />
          <Route path="/audit-package" element={<AuditPackagePage />} />
          <Route path="/decisions" element={<DecisionsQueuePage />} />
          <Route
            path="/cases/:caseId/report"
            element={<ValidationReportPage />}
          />
        </Route>

        {/* Catch-all · stale deep-links land on V4 workbench, not 404. */}
        <Route path="*" element={<Navigate to="/workbench" replace />} />
      </Routes>
    </>
  );
}
